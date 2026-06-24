# Runner - 桥接 LangGraph 执行 → SSE 事件流
import json
import logging
import uuid
from typing import AsyncGenerator

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from app.agents.graph import build_graph
from app.agents.qc_bus import get_bus, reset_bus
from app.config import settings

logger = logging.getLogger(__name__)


def _sse(event: dict) -> str:
    """把 dict 编码为 SSE data 帧"""
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


async def run_agent(
    user_message: str,
    user_id: int,
    thread_id: str,
    uploaded_refs: list[dict] | None = None,
) -> AsyncGenerator[str, None]:
    """异步生成器：消费 LangGraph astream_events，yield SSE 字符串

    事件类型：
      {type: "token", content}                 — Claude 流式 token
      {type: "tool_start", tool, args}         — 工具开始
      {type: "tool_end", tool, result}         — 工具结束
      {type: "image", image_id, data_url, ...} — 生成图（工具产出后聚合推送）
      {type: "done"}                           — 结束
      {type: "error", message}                 — 错误
    """
    graph = build_graph()
    run_id = str(uuid.uuid4())
    reset_bus(run_id)  # 清空本次质检状态

    config: RunnableConfig = {
        "configurable": {
            "user_id": user_id,
            "thread_id": thread_id,
            "uploaded_refs": uploaded_refs or [],
            "_generated_images": [],
            "run_id": run_id,
        },
        "recursion_limit": settings.agent_recursion_limit,
        "run_id": run_id,
    }

    initial_state = {
        "messages": [HumanMessage(content=user_message)],
        "user_id": user_id,
        "thread_id": thread_id,
        "uploaded_images": uploaded_refs or [],
        "generated_images": [],
        "qc_retry_count": 0,
        "qc_feedback": "",
    }

    # 已推送过 image 事件的 image_id 集合，避免重复
    pushed_images: set[str] = set()
    final_generated: list[dict] = []
    qc_pushed_count = 0  # 已推送的质检状态条数

    def _flush_qc_events():
        """把 quality_check 节点写入 qc_bus 的新条目转 SSE"""
        nonlocal qc_pushed_count
        bag = get_bus(run_id)
        out = []
        while qc_pushed_count < len(bag):
            entry = bag[qc_pushed_count]
            qc_pushed_count += 1
            phase = entry.get("phase")
            if phase == "checking":
                out.append(_sse({
                    "type": "qc_checking",
                    "image_id": entry.get("image_id"),
                    "retry": entry.get("retry", 0),
                }))
            elif phase == "passed":
                out.append(_sse({
                    "type": "qc_passed",
                    "score": entry.get("score"),
                    "retry": entry.get("retry", 0),
                }))
            elif phase == "retry":
                out.append(_sse({
                    "type": "qc_retry",
                    "score": entry.get("score"),
                    "issues": entry.get("issues", []),
                    "suggestions": entry.get("suggestions", ""),
                    "retry": entry.get("retry", 0),
                }))
            elif phase == "error":
                out.append(_sse({"type": "qc_error", "message": entry.get("message", "")}))
        return out

    try:
        async for ev in graph.astream_events(initial_state, config=config, version="v2"):
            etype = ev.get("event")
            name = ev.get("name", "")
            data = ev.get("data", {})

            # 1. Claude 流式 token
            if etype == "on_chat_model_stream":
                chunk = data.get("chunk")
                if chunk is None:
                    continue
                content = getattr(chunk, "content", "")
                # bind_tools 下 tool_calls 走 chunk.tool_call_chunks，content 可能是空 str/列表
                if isinstance(content, list):
                    # 多模态 content，提取 text 块
                    text_parts = []
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                    content = "".join(text_parts)
                if content:
                    yield _sse({"type": "token", "content": content})

            # 2. 工具开始
            elif etype == "on_tool_start":
                tool_input = data.get("input", {})
                # input 可能是 dict 或 str
                args_summary = tool_input if isinstance(tool_input, dict) else {}
                yield _sse({"type": "tool_start", "tool": name, "args": args_summary})

            # 3. 工具结束
            elif etype == "on_tool_end":
                output = data.get("output")
                # output 是 ToolMessage 或字符串
                result_text = ""
                if hasattr(output, "content"):
                    result_text = str(getattr(output, "content", ""))
                else:
                    result_text = str(output)
                yield _sse({"type": "tool_end", "tool": name, "result": result_text[:800]})

            # 4. 节点结束 - 聚合生成图（从 configurable bag 拿，实时推送）
            elif etype == "on_chain_end" and name == "tools":
                bag = config["configurable"].get("_generated_images", [])
                for meta in bag:
                    iid = meta.get("image_id")
                    if iid and iid not in pushed_images:
                        pushed_images.add(iid)
                        yield _sse({
                            "type": "image",
                            "image_id": iid,
                            "data_url": meta.get("data_url", ""),
                            "prompt_used": meta.get("prompt_used", ""),
                            "model_used": meta.get("model_used", ""),
                            "cost": meta.get("cost", 0.0),
                            "currency": meta.get("currency", "$"),
                            "aspect_ratio": meta.get("aspect_ratio", "1:1"),
                        })

            # 5. 整个图执行结束 - 兜底补推未推送的图
            elif etype == "on_chain_end" and name == "LangGraph":
                final_state = data.get("output", {})
                final_generated = final_state.get("generated_images", []) if isinstance(final_state, dict) else []

            # 6. 每个事件后都尝试刷出质检状态（_flush_qc_events 有计数器，幂等安全；
            #    LangGraph 节点事件的 name 不稳定，按节点名匹配易漏，改无条件刷）
            for sse_evt in _flush_qc_events():
                yield sse_evt

        # 兜底：图结束后若还有未推送的生成图（理论上 4 已推过），补推
        for meta in final_generated:
            iid = meta.get("image_id")
            if iid and iid not in pushed_images:
                pushed_images.add(iid)
                yield _sse({
                    "type": "image",
                    "image_id": iid,
                    "data_url": meta.get("data_url", ""),
                    "prompt_used": meta.get("prompt_used", ""),
                    "model_used": meta.get("model_used", ""),
                    "cost": meta.get("cost", 0.0),
                    "currency": meta.get("currency", "$"),
                    "aspect_ratio": meta.get("aspect_ratio", "1:1"),
                })

        yield _sse({"type": "done"})
    except Exception as e:
        logger.error(f"[agent] run_agent 异常: {e}", exc_info=True)
        yield _sse({"type": "error", "message": str(e)})
