"""
NoteForge Graph Assembly
LangGraph graph configuration for the NoteForge agent.
"""

from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from note_forge.state import NoteForgeState


MAX_EVAL_RETRIES = 2
FAITHFULNESS_THRESHOLD = 0.7


def create_route_decision(state: NoteForgeState) -> str:
    """Determine route based on router decision."""
    route = state.get("route", "")
    if route == "retrieve":
        return "retrieve"
    elif route == "tool":
        return "tool"
    else:
        return "skip"


def create_eval_decision(state: NoteForgeState) -> str:
    """Determine whether to retry or save based on faithfulness."""
    faithfulness = state.get("faithfulness", 0.0)
    eval_retries = state.get("eval_retries", 0)

    if faithfulness >= 0.7:
        return "save"
    elif eval_retries >= MAX_EVAL_RETRIES:
        return "save"
    else:
        return "answer"


MAX_EVAL_RETRIES = 2
FAITHFULNESS_THRESHOLD = 0.7


def build_graph(
    memory_node,
    router_node,
    retrieval_node,
    skip_retrieval_node,
    tool_node,
    answer_node,
    eval_node,
    save_node,
):
    """Build and compile the LangGraph."""

    graph = StateGraph(NoteForgeState)

    graph.add_node("memory", memory_node)
    graph.add_node("router", router_node)
    graph.add_node("retrieve", retrieval_node)
    graph.add_node("skip", skip_retrieval_node)
    graph.add_node("tool", tool_node)
    graph.add_node("answer", answer_node)
    graph.add_node("eval", eval_node)
    graph.add_node("save", save_node)

    graph.set_entry_point("memory")

    graph.add_edge("memory", "router")

    graph.add_conditional_edges(
        "router",
        create_route_decision,
        {"retrieve": "retrieve", "tool": "tool", "skip": "skip"},
    )

    graph.add_edge("retrieve", "answer")
    graph.add_edge("skip", "answer")
    graph.add_edge("tool", "answer")

    graph.add_edge("answer", "eval")

    graph.add_conditional_edges(
        "eval", create_eval_decision, {"answer": "answer", "save": "save"}
    )

    graph.add_edge("save", END)

    app = graph.compile(checkpointer=MemorySaver())

    return app
