# LangGraph 节点：orchestrator（Claude 决策）+ tool_executor（执行工具）+ quality_check（Gemini 质检）
import json
import logging
import time
import uuid

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig

from app.agents.image_store import image_store
from app.agents.llm import get_llm
from app.agents.prompts import (
    build_system_prompt,
    build_quality_check_user_prompt,
    QUALITY_CHECK_SYSTEM_PROMPT,
)
from app.agents.state import AgentState
from app.agents.tools import ALL_TOOLS
from app.config import settings

logger = logging.getLogger(__name__)

# 工具名 → 工具对象 索引
_TOOL_MAP = {t.name: t for t in ALL_TOOLS}

# 会产出图片的工具集合（这些工具执行后需触发质检）
_IMAGE_PRODUCTION_TOOLS = {"generate_quick_image"}


async def orchestrator_node(state: AgentState, config: RunnableConfig) -> dict:
    """Claude 决策节点：读消息历史，决定调工具还是直接回复"""
    t0 = time.perf_counter()
    llm = get_llm()
    bound = llm.bind_tools(ALL_TOOLS)

    # 构建消息：system + 历史
    configurable = (config or {}).get("configurable", {})
    uploaded_refs = configurable.get("uploaded_refs", [])
    system_text = build_system_prompt(uploaded_refs)
    messages = [SystemMessage(content=system_text)] + list(state["messages"])

    # 质检反馈注入：
    # - PASSED：质检已通过，注入终止信号，Claude 转为向用户汇报，不再调生图工具
    # - 非空且非 PASSED：FAIL 反馈，提示 Claude 改 prompt 重生
    # - 空：首次或纯文本对话，不注入
    qc_feedback = state.get("qc_feedback", "")
    if qc_feedback == "PASSED":
        messages = [SystemMessage(content=system_text), SystemMessage(
            content=(
                "【质检结果】上一轮生成的图片已通过视觉质检，无明显 AI 缺陷。"
                "请直接向用户汇报生成结果（简要描述图片特点、使用的模型、比例、费用），"
                "**不要再调用 generate_quick_image 或任何生图工具**，也不要重复生成。"
                "如果用户未明确要求多张，默认一张即可。"
            )
        )] + list(state["messages"])
    elif qc_feedback:
        messages = [SystemMessage(content=system_text), SystemMessage(
            content=f"【质检反馈】上一轮生成的图片未通过质检：{qc_feedback}。请根据反馈调整 prompt 或参数后重新生成，不要原样重试。"
        )] + list(state["messages"])

    ai_msg: AIMessage = await bound.ainvoke(messages)
    logger.info(f"[agent] orchestrator: tool_calls={len(ai_msg.tool_calls or [])} decision_cost={time.perf_counter() - t0:.2f}s")
    return {"messages": [ai_msg]}


async def tool_executor_node(state: AgentState, config: RunnableConfig) -> dict:
    """执行 Claude 要求的工具，返回 ToolMessage + 聚合生成图元信息"""
    last_msg: AIMessage = state["messages"][-1]
    tool_calls = last_msg.tool_calls or []

    new_messages = []
    new_generated = list(state.get("generated_images", []))

    # 准备 config configurable 容器（工具往里塞生成图 meta）
    configurable = (config or {}).setdefault("configurable", {})
    gen_bag = configurable.setdefault("_generated_images", [])

    for call in tool_calls:
        tool_name = call.get("name")
        tool_args = call.get("args", {}) or {}
        tool_call_id = call.get("id", "")
        tool = _TOOL_MAP.get(tool_name)
        if tool is None:
            new_messages.append(ToolMessage(
                content=f"未知工具：{tool_name}",
                tool_call_id=tool_call_id,
                name=tool_name,
            ))
            continue

        try:
            # 注入运行时参数
            result = await tool.ainvoke(tool_args, config=config)
        except Exception as e:
            logger.error(f"[agent] 工具 {tool_name} 执行异常: {e}", exc_info=True)
            result = f"❌ 工具执行异常：{e}"

        new_messages.append(ToolMessage(
            content=str(result),
            tool_call_id=tool_call_id,
            name=tool_name,
        ))

    # 把工具侧 stash 的生成图 meta 合并进 state
    produced_image = bool(gen_bag)
    if gen_bag:
        new_generated.extend(gen_bag)

    # 记录本轮是否产出图片（供 route_after_tools 决策是否触发质检）
    return {
        "messages": new_messages,
        "generated_images": new_generated,
        "_produced_image_this_round": produced_image,
    }


async def quality_check_node(state: AgentState, config: RunnableConfig) -> dict:
    """质检节点：取最新生成图，调 Gemini Flash 视觉质检，PASS/FAIL 反馈注入 state

    qc_feedback：
      - PASSED（通过）
      - 或 FAIL 反馈文本（含 issues + suggestions，供 orchestrator 据此改进重生）
    qc_retry_count：+1
    """
    from app.providers.gemini_provider import GeminiProvider

    t0 = time.perf_counter()
    generated = state.get("generated_images", [])
    if not generated:
        return {"qc_feedback": "PASSED"}  # 无图可检，跳过

    last_img_meta = generated[-1]
    image_id = last_img_meta.get("image_id")
    gen_prompt = last_img_meta.get("prompt_used", "")
    # 用户原始需求：取最早的 HumanMessage
    request_desc = ""
    for m in state["messages"]:
        if m.__class__.__name__ == "HumanMessage":
            request_desc = getattr(m, "content", "")
            if isinstance(request_desc, list):
                request_desc = str(request_desc)
            break

    # 把质检状态写进 qc_bus（模块级注册表，按 run_id 隔离），让 runner 能推 qc_* 事件
    from app.agents.qc_bus import get_bus

    run_id = ((config or {}).get("configurable", {})).get("run_id", "") or str((config or {}).get("run_id", ""))
    qc_status_bag = get_bus(run_id)
    qc_status_bag.append({"phase": "checking", "image_id": image_id, "retry": state.get("qc_retry_count", 0)})

    img_bytes = await image_store.get(image_id)
    if img_bytes is None:
        logger.warning(f"[agent] 质检取图失败 image_id={image_id}（可能已过期）")
        return {"qc_feedback": "PASSED", "qc_retry_count": state.get("qc_retry_count", 0) + 1}

    user_prompt = build_quality_check_user_prompt(request_desc, gen_prompt)
    try:
        gemini = GeminiProvider()
        raw = await gemini.free_text_query(
            img_bytes,
            user_prompt,
            mime_type="image/jpeg",
            system_prompt=QUALITY_CHECK_SYSTEM_PROMPT,
        )
    except Exception as e:
        logger.error(f"[agent] 质检 Gemini 调用失败：{e}", exc_info=True)
        # 质检服务异常不应阻塞主流程，判通过
        qc_status_bag.append({"phase": "error", "message": str(e)})
        return {"qc_feedback": "PASSED", "qc_retry_count": state.get("qc_retry_count", 0) + 1}

    passed, issues, suggestions, score = _parse_qc_result(raw)
    retry_count = state.get("qc_retry_count", 0) + 1

    if passed:
        qc_status_bag.append({"phase": "passed", "score": score, "retry": retry_count})
        logger.info(f"[agent] 质检通过 score={score} retry={retry_count} cost={time.perf_counter() - t0:.2f}s")
        return {"qc_feedback": "PASSED", "qc_retry_count": retry_count}

    # FAIL：把 issues + suggestions 拼成反馈，供 orchestrator 据此重生
    feedback_parts = []
    if issues:
        feedback_parts.append("问题：" + "；".join(issues))
    if suggestions:
        feedback_parts.append(f"修正方向：{suggestions}")
    feedback = "；".join(feedback_parts) if feedback_parts else "图片质量不达标，请调整后重新生成"
    qc_status_bag.append({
        "phase": "retry",
        "score": score,
        "issues": issues,
        "suggestions": suggestions,
        "retry": retry_count,
    })
    logger.info(f"[agent] 质检未通过 score={score} retry={retry_count} cost={time.perf_counter() - t0:.2f}s，反馈：{feedback}")
    return {"qc_feedback": feedback, "qc_retry_count": retry_count}


def _parse_qc_result(raw: str) -> tuple[bool, list[str], str, int]:
    """解析 Gemini 质检 JSON 输出，返回 (passed, issues, suggestions, score)

    容错：JSON 解析失败时尝试兜底关键词判定。
    """
    text = raw.strip()
    # 去除可能的 markdown 代码块包裹
    if text.startswith("```"):
        text = text.split("\n", 1)[-1] if "\n" in text else text.lstrip("`")
        if text.endswith("```"):
            text = text[:-3].strip()
    try:
        data = json.loads(text)
        return (
            bool(data.get("pass", True)),
            list(data.get("issues", []) or []),
            str(data.get("suggestions", "") or ""),
            int(data.get("score", 0) or 0),
        )
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"[agent] 质检结果 JSON 解析失败：{e}，原文：{raw[:200]}")
        # 兜底：含 "pass": true / 通过 → 判通过；否则判通过（质检不可靠时不阻塞）
        lowered = raw.lower()
        if '"pass": true' in lowered or '"pass":true' in lowered or "通过" in raw:
            return True, [], "", 0
        return True, [], "", 0  # 解析失败默认通过，避免误判死循环


def route_after_orchestrator(state: AgentState) -> str:
    """orchestrator 后的路由：有 tool_calls → tools；否则 END"""
    last_msg = state["messages"][-1]
    if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
        return "tools"
    return "end"


def route_after_tools(state: AgentState) -> str:
    """tool_executor 后的路由：
    - 本轮产出了图片 且 质检次数未达上限 且 之前未通过 → quality_check
    - 否则 → orchestrator（让 Claude 看到工具结果后继续/收尾）

    防御：若上一轮已 PASSED（qc_feedback 仍为 "PASSED"），即使 Claude 忽略
    终止信号再次调生图工具，也不再触发质检（避免无限循环直到 retry 上限）。
    """
    produced = state.get("_produced_image_this_round", False)
    retry = state.get("qc_retry_count", 0)
    qc_passed = state.get("qc_feedback", "") == "PASSED"
    if produced and retry < settings.agent_max_qc_retries and not qc_passed:
        return "quality_check"
    return "orchestrator"
