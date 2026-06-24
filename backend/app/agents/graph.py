# LangGraph 图构建 - StateGraph 编排（Phase 2：orchestrator + tool_executor + quality_check）
from langgraph.graph import StateGraph, END

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

    Phase 2 结构：
        START → orchestrator ──(tool_calls)──→ tool_executor ──┐
                      │                                        │
                      └──(纯文本)──→ END                       ├──(产图 & retry<max)──→ quality_check ──→ orchestrator
                                                               └──(否则)──→ orchestrator

    quality_check 执行后恒回 orchestrator（Claude 读 qc_feedback：
      - PASSED → 给用户最终回复
      - FAIL & retry<max → 调工具重生（反馈指导修正）
      - FAIL & retry>=max → 放弃重生，告知用户）
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
    builder.add_edge("quality_check", "orchestrator")  # 质检完回 orchestrator 决策

    # Phase 1/2 无 checkpointer（Phase 3 加 AsyncSqliteSaver 做多轮持久化）
    return builder.compile()

