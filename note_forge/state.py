"""
NoteForge State Definition
Defines the state structure for the LangGraph agent.
"""

from typing import TypedDict, List, Optional


class NoteForgeState(TypedDict):
    """State structure for NoteForge agent."""

    question: str
    messages: List[str]
    route: str
    retrieved: str
    sources: List[str]
    tool_result: str
    answer: str
    faithfulness: float
    eval_retries: int
    user_name: Optional[str]
