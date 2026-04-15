"""
NoteForge Node Functions
LangGraph node functions for the NoteForge agent.
"""

import re
from typing import Dict, Any
from langchain_groq import ChatGroq


FAITHFULNESS_THRESHOLD = 0.7
MAX_EVAL_RETRIES = 2


def create_memory_node(llm: ChatGroq):
    """Create memory node function."""

    def memory_node(state: Dict[str, Any]) -> Dict[str, Any]:
        question = state.get("question", "")
        messages = list(state.get("messages", []))

        user_name = state.get("user_name")
        if user_name is None and "my name is" in question.lower():
            match = re.search(r"my name is\s+(\w+)", question.lower())
            if match:
                user_name = match.group(1)

        messages.append(f"User: {question}")

        if len(messages) > 12:
            messages = messages[-12:]

        return {"messages": messages, "user_name": user_name}

    return memory_node


def create_router_node(llm: ChatGroq):
    """Create router node function that decides the route."""

    router_prompt = """You are a router for NoteForge, an AI learning assistant. 
Given the user's question, decide which route to take:

1. "retrieve" - Use this when the question requires information from the knowledge base about NoteForge features, capabilities, tools, or learning techniques.
2. "tool" - Use this when the question requires local text analysis like: generating an outline, creating a quiz, calculating text statistics, or analyzing a provided text.
3. "memory_only" - Use this for casual conversation, greetings, or questions that don't need knowledge base or tools.

Respond with ONLY one word: retrieve, tool, or memory_only.

Question: {question}"""

    def router_node(state: Dict[str, Any]) -> Dict[str, Any]:
        question = state.get("question", "")

        response = llm.invoke(router_prompt.format(question=question))
        route = response.content.strip().lower()

        if route not in ["retrieve", "tool", "memory_only"]:
            route = "memory_only"

        return {"route": route}

    return router_node


def create_retrieval_node(embedder, collection):
    """Create retrieval node function."""

    def retrieval_node(state: Dict[str, Any]) -> Dict[str, Any]:
        question = state.get("question", "")

        query_embedding = embedder.encode([question]).tolist()

        results = collection.query(query_embeddings=query_embedding, n_results=3)

        retrieved = ""
        sources = []

        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                topic = results["metadatas"][0][i].get("topic", "Unknown")
                retrieved += f"[{topic}]\n{doc}\n\n"
                sources.append(topic)

        return {"retrieved": retrieved, "sources": sources}

    return retrieval_node


def create_skip_retrieval_node():
    """Create skip retrieval node for memory_only routes."""

    def skip_retrieval_node(state: Dict[str, Any]) -> Dict[str, Any]:
        return {"retrieved": "", "sources": []}

    return skip_retrieval_node


def create_tool_node(llm):
    """Create tool node for local text analysis."""

    def tool_node(state: Dict[str, Any]) -> Dict[str, Any]:
        question = state.get("question", "")

        tool_prompt = f"""You are a local text analysis tool for NoteForge. 
Analyze the user's request and provide the appropriate output.

Available tools:
1. Outline Generation: Create structured outlines from topics
2. Quiz Generation: Generate practice questions from content
3. Text Statistics: Calculate word count, reading time, complexity
4. Study Plan: Create personalized study schedules

User request: {question}

Provide a helpful response based on the appropriate tool. 
If the user is asking about NoteForge features or capabilities, 
respond that you're a learning assistant and ask how you can help with their study needs."""

        try:
            response = llm.invoke(tool_prompt)
            tool_result = response.content
        except Exception as e:
            tool_result = f"Error: {str(e)}"

        return {"tool_result": tool_result}

    return tool_node


def create_answer_node(llm):
    """Create answer node that generates the final response."""

    def answer_node(state: Dict[str, Any]) -> Dict[str, Any]:
        question = state.get("question", "")
        retrieved = state.get("retrieved", "")
        tool_result = state.get("tool_result", "")
        messages = state.get("messages", [])
        user_name = state.get("user_name")
        eval_retries = state.get("eval_retries", 0)

        name_part = f" {user_name}" if user_name else ""

        context_parts = []
        if retrieved:
            context_parts.append(f"KNOWLEDGE BASE CONTEXT:\n{retrieved}")
        if tool_result:
            context_parts.append(f"LOCAL TOOL RESULTS:\n{tool_result}")

        context = (
            "\n\n".join(context_parts)
            if context_parts
            else "No specific context available."
        )

        history = "\n".join(messages[-6:]) if messages else "No previous messages."

        escalation = ""
        if eval_retries > 0:
            escalation = f"\n\nIMPORTANT: This is attempt {eval_retries + 1}. Previous answer had low faithfulness. Focus on ONLY using information from the provided context. Do NOT add information from your general knowledge."

        system_prompt = f"""You are NoteForge, an AI learning assistant for students and researchers.

Your goal is to help users transform learning materials into structured notes, summaries, revision sheets, concept maps, and study plans.

IMPORTANT RULES:
1. Answer ONLY from the provided context - never use your general knowledge
2. If the context doesn't contain the answer, explicitly state "I don't have this information in the provided material"
3. Be helpful, concise, and educational
4. Never hallucinate information{escalation}

Context:
{context}

Conversation History:
{history}

User{name_part}: {question}

Provide a helpful, accurate response based ONLY on the context provided."""

        response = llm.invoke(system_prompt)
        answer = response.content

        return {"answer": answer}

    return answer_node


def create_eval_node(llm):
    """Create evaluation node that scores faithfulness."""

    def eval_node(state: Dict[str, Any]) -> Dict[str, Any]:
        question = state.get("question", "")
        answer = state.get("answer", "")
        retrieved = state.get("retrieved", "")
        eval_retries = state.get("eval_retries", 0)

        if not retrieved:
            return {"faithfulness": 1.0, "eval_retries": eval_retries}

        eval_prompt = f"""Evaluate the faithfulness of the answer to the retrieved context.

Retrieved Context:
{retrieved}

Question: {question}

Answer: {answer}

Rate faithfulness from 0.0 to 1.0, where:
- 1.0 = Answer uses ONLY information from the context
- 0.5 = Answer mixes context with some outside information
- 0.0 = Answer is completely unrelated to context

Respond with ONLY a number between 0.0 and 1.0."""

        try:
            response = llm.invoke(eval_prompt)
            score_text = response.content.strip()
            faithfulness = float(score_text)
            faithfulness = max(0.0, min(1.0, faithfulness))
        except:
            faithfulness = 0.5

        return {"faithfulness": faithfulness, "eval_retries": eval_retries}

    return eval_node


def create_save_node():
    """Create save node that stores the answer in message history."""

    def save_node(state: Dict[str, Any]) -> Dict[str, Any]:
        answer = state.get("answer", "")
        messages = state.get("messages", [])

        messages.append(f"NoteForge: {answer}")

        return {"messages": messages}

    return save_node
