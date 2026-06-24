# 历史对话恢复 - 从 LangGraph checkpoint 还原前端可渲染的消息列表
import logging

from langchain_core.runnables import RunnableConfig

from app.agents.graph import build_graph
from app.agents.image_store import image_store

logger = logging.getLogger(__name__)


async def reconstruct_history(thread_id: str, user_id: int) -> dict | None:
    """从 checkpoint 还原对话历史，返回前端可渲染结构

    Returns:
        {"thread_id": str, "messages": [chat_msg_dict, ...], "image_expired_count": int}
        若该 thread 无 checkpoint 返回 None
    """
    config: RunnableConfig = {
        "configurable": {"thread_id": thread_id, "user_id": user_id},
    }
    graph = build_graph()
    try:
        snapshot = await graph.aget_state(config)
    except Exception as e:
        logger.error(f"[agent] aget_state 失败 thread={thread_id}: {e}", exc_info=True)
        return None

    if snapshot is None or snapshot.values is None or not snapshot.values.get("messages"):
        return None

    values = snapshot.values
    state_messages = values.get("messages", [])
    generated_images = values.get("generated_images", [])

    # 预取所有生成图的 data_url（仍存在于 ImageStore 的才有）
    images_with_url: list[dict] = []
    expired_count = 0
    for meta in generated_images:
        iid = meta.get("image_id")
        data_url = ""
        if iid:
            img_bytes = await image_store.get(iid)
            if img_bytes is not None:
                # 构造 data_url
                import base64
                b64 = base64.b64encode(img_bytes).decode()
                data_url = f"data:image/jpeg;base64,{b64}"
            else:
                expired_count += 1
        images_with_url.append({
            "image_id": iid or "",
            "data_url": data_url,
            "expired": data_url == "",
            "prompt_used": meta.get("prompt_used", ""),
            "model_used": meta.get("model_used", ""),
            "cost": meta.get("cost", 0.0),
            "currency": meta.get("currency", "$"),
            "aspect_ratio": meta.get("aspect_ratio", "1:1"),
        })

    chat_msgs = _state_messages_to_chat(state_messages, images_with_url)
    return {
        "thread_id": thread_id,
        "messages": chat_msgs,
        "image_expired_count": expired_count,
    }


def _state_messages_to_chat(state_messages: list, images: list[dict]) -> list[dict]:
    """把 LangChain 消息序列还原为前端 ChatMessage 列表

    规则：
    - HumanMessage → 新 user 消息（文本）
    - AIMessage → 追加到当前 assistant 消息（文本 + tool_calls 转 ToolStep）
    - ToolMessage → 完成对应的 running ToolStep（写 result）
    - SystemMessage → 跳过（不展示）
    - 生成图：按 image_id 在 assistant 消息出现顺序中分配（最简：全部挂到最后一条 assistant）
    """
    result: list[dict] = []
    current_assistant: dict | None = None

    def flush_assistant():
        nonlocal current_assistant
        if current_assistant is not None:
            result.append(current_assistant)
            current_assistant = None

    for msg in state_messages:
        cls = msg.__class__.__name__
        if cls == "HumanMessage":
            flush_assistant()
            content = getattr(msg, "content", "")
            if isinstance(content, list):
                # 多模态 content，提取 text
                content = "".join(
                    b.get("text", "") for b in content
                    if isinstance(b, dict) and b.get("type") == "text"
                )
            result.append({
                "id": f"u_{id(msg)}",
                "role": "user",
                "content": str(content),
                "images": [],
                "toolSteps": [],
            })
        elif cls == "AIMessage":
            if current_assistant is None:
                current_assistant = {
                    "id": f"a_{id(msg)}",
                    "role": "assistant",
                    "content": "",
                    "images": [],
                    "toolSteps": [],
                }
            # 提取文本
            content = getattr(msg, "content", "")
            if isinstance(content, str):
                current_assistant["content"] += content
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        current_assistant["content"] += block.get("text", "")
            # tool_calls → running ToolStep
            for tc in (getattr(msg, "tool_calls", None) or []):
                current_assistant["toolSteps"].append({
                    "id": tc.get("id", "") or f"t_{id(tc)}",
                    "tool": tc.get("name", ""),
                    "args": tc.get("args", {}) or {},
                    "status": "running",
                })
        elif cls == "ToolMessage":
            if current_assistant is None:
                current_assistant = {
                    "id": f"a_{id(msg)}",
                    "role": "assistant",
                    "content": "",
                    "images": [],
                    "toolSteps": [],
                }
            tool_name = getattr(msg, "name", "") or ""
            content_str = str(getattr(msg, "content", ""))
            # 找到最后一个同名 running step 完成它
            for step in reversed(current_assistant["toolSteps"]):
                if step["tool"] == tool_name and step["status"] == "running":
                    step["status"] = "done"
                    step["result"] = content_str[:800]
                    break
        # SystemMessage / 其他：跳过

    flush_assistant()

    # 把生成图挂到「最后一条 assistant 消息」（多轮多 assistant 的精确分配需更复杂追踪，
    # MVP 不做：多轮场景里用户主要看最新一组图，全挂最后一条可接受）
    if images:
        for msg in reversed(result):
            if msg["role"] == "assistant":
                msg["images"] = images
                break

    return result


async def get_image_bytes(image_id: str) -> tuple[bytes | None, str]:
    """从 ImageStore 取图片 bytes，返回 (bytes, mime)；不存在返回 (None, '')"""
    meta = await image_store.get_meta(image_id)
    mime = meta.get("mime", "image/jpeg") if meta else "image/jpeg"
    b = await image_store.get(image_id)
    return b, mime
