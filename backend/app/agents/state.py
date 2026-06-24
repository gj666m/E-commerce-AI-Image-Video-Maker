# AgentState 定义 - LangGraph 状态
import operator
from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """对话式 Agent 的 LangGraph 状态

    messages 由 add_messages reducer 自动累加（HumanMessage/AIMessage/ToolMessage）
    generated_images / uploaded_images 用 operator.add reducer 跨轮累加
    （历史生成图与参考图引用在新轮中保留）
    qc_* 字段每轮显式覆写重置（每轮新生成独立计重试次数）
    """
    messages: Annotated[list, add_messages]
    user_id: int
    thread_id: str
    # 用户上传图引用 [{image_id, filename, mime}] — 跨轮累加
    uploaded_images: Annotated[list, operator.add]
    # 生成图引用 [{image_id, prompt_used, model_used, cost, currency}] — 跨轮累加
    generated_images: Annotated[list, operator.add]
    qc_retry_count: int
    qc_feedback: str
    # 内部瞬态标记：本轮 tool_executor 是否产出了图片（供 route_after_tools 决策是否触发质检）
    _produced_image_this_round: bool
