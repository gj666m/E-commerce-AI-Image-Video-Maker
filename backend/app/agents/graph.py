# LangGraph 图构建 - StateGraph 编排（Phase 3：接 AsyncSqliteSaver checkpointer）
from langgraph.graph import StateGraph, END

from app.agents.checkpoint import get_checkpointer
from app.agents.nodes import (
    orchestrator_node,
    tool_executor_node,
    quality_check_node,
    route_after_orchestrator,
    route_after_tools,
)
from app.agents.state import AgentState


def build_graph():
    """构建并编译 Agent 图

    Phase 3 起：若 checkpointer 已初始化（lifespan startup 阶段完成），编译时挂载
    AsyncSqliteSaver，配合 config.configurable.thread_id 实现多轮持久化（刷新/重连
    可用 aget_state 恢复历史）。未初始化时降级为无持久化（保持 Phase 1/2 行为）。

    结构：
        START → orchestrator ──(tool_calls)──→ tool_executor ──┐
                      │                                        │
                      └──(纯文本)──→ END                       ├──(产图 & retry<max)──→ quality_check ──→ orchestrator
                                                               └──(否则)──→ orchestrator
    """
    builder = StateGraph(AgentState)
    builder.add_node("orchestrator", orchestrator_node)
    builder.add_node("tools", tool_executor_node)
    builder.add_node("quality_check", quality_check_node)

    builder.set_entry_point("orchestrator")
    builder.add_conditional_edges(
        "orchestrator",
        route_after_orchestrator,
        {"tools": "tools", "end": END},
    )
    builder.add_conditional_edges(
        "tools",
        route_after_tools,
        {"quality_check": "quality_check", "orchestrator": "orchestrator"},
    )
    builder.add_edge("quality_check", "orchestrator")

    checkpointer = get_checkpointer()
    return builder.compile(checkpointer=checkpointer) if checkpointer else builder.compile()
