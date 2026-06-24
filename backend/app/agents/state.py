# AgentState 定义 - LangGraph 状态
from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """对话式 Agent 的 LangGraph 状态

    messages 由 add_messages reducer 自动累加（HumanMessage/AIMessage/ToolMessage）
    generated_images / uploaded_images 只存元信息引用（图片 bytes 在 ImageStore）
    qc_* 字段 Phase 2 质检循环使用，Phase 1 保留默认值
    """
    messages: Annotated[list, add_messages]
    user_id: int
    thread_id: str
    # 用户上传图引用 [{image_id, filename, mime}]
    uploaded_images: list[dict]
    # 生成图引用 [{image_id, prompt_used, model_used, cost, currency}]
    generated_images: list[dict]
    qc_retry_count: int
    qc_feedback: str
    # 内部瞬态标记：本轮 tool_executor 是否产出了图片（供 route_after_tools 决策是否触发质检）
    _produced_image_this_round: bool
