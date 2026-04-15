"""
NoteForge Test Script
Test the agent with 10 questions including red-team tests.
"""

import os
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import chromadb
from langgraph.checkpoint.memory import MemorySaver
from langchain_groq import ChatGroq

from note_forge.knowledge_base import KNOWLEDGE_BASE
from note_forge.state import NoteForgeState
from note_forge.nodes import (
    create_memory_node,
    create_router_node,
    create_retrieval_node,
    create_skip_retrieval_node,
    create_tool_node,
    create_answer_node,
    create_eval_node,
    create_save_node,
)
from note_forge.graph import build_graph

load_dotenv()


def initialize_components():
    """Initialize all components."""

    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.3,
    )

    embedder = SentenceTransformer("all-MiniLM-L6-v2")

    chroma_client = chromadb.Client()
    collection = chroma_client.create_collection("noteforge_kb")

    documents = [doc["text"] for doc in KNOWLEDGE_BASE]
    ids = [doc["id"] for doc in KNOWLEDGE_BASE]
    metadatas = [{"topic": doc["topic"]} for doc in KNOWLEDGE_BASE]
    embeddings = embedder.encode(documents).tolist()

    collection.add(
        documents=documents, ids=ids, metadatas=metadatas, embeddings=embeddings
    )

    memory_node = create_memory_node(llm)
    router_node = create_router_node(llm)
    retrieval_node = create_retrieval_node(embedder, collection)
    skip_retrieval_node = create_skip_retrieval_node()
    tool_node = create_tool_node(llm)
    answer_node = create_answer_node(llm)
    eval_node = create_eval_node(llm)
    save_node = create_save_node()

    app = build_graph(
        memory_node,
        router_node,
        retrieval_node,
        skip_retrieval_node,
        tool_node,
        answer_node,
        eval_node,
        save_node,
    )

    return app


def ask(app, question, thread_id):
    """Ask a question and get the response."""

    config = {"configurable": {"thread_id": thread_id}}

    existing_state = None
    try:
        existing_state = app.get_state(config)
    except:
        pass

    if existing_state:
        current_messages = list(existing_state.values.get("messages", []))
        current_user_name = existing_state.values.get("user_name")
    else:
        current_messages = []
        current_user_name = None

    initial_state: NoteForgeState = {
        "question": question,
        "messages": current_messages,
        "route": "",
        "retrieved": "",
        "sources": [],
        "tool_result": "",
        "answer": "",
        "faithfulness": 0.0,
        "eval_retries": 0,
        "user_name": current_user_name,
    }

    result = app.invoke(initial_state, config)

    return result


def test_questions():
    """Run test questions."""

    app = initialize_components()

    test_questions = [
        ("What is NoteForge?", "test_1"),
        ("How does NoteForge generate structured notes?", "test_2"),
        ("What are the summarization techniques used?", "test_3"),
        ("How does NoteForge create revision sheets?", "test_4"),
        ("What is concept mapping in NoteForge?", "test_5"),
        ("How does NoteForge generate study plans?", "test_6"),
        ("Can NoteForge create quizzes?", "test_7"),
        ("How does NoteForge handle multi-turn conversations?", "test_8"),
        ("What is faithfulness evaluation?", "test_9"),
        ("Out of scope: What is the weather today?", "red_team_1"),
    ]

    print("\n" + "=" * 60)
    print("NOTEFORGE TEST RESULTS")
    print("=" * 60)

    for question, test_id in test_questions:
        print(f"\n--- Test: {test_id} ---")
        print(f"Question: {question}")

        try:
            result = ask(app, question, test_id)

            print(f"Route: {result.get('route', 'N/A')}")
            print(f"Faithfulness: {result.get('faithfulness', 0.0):.2f}")
            print(f"Sources: {result.get('sources', [])}")
            print(f"Answer: {result.get('answer', 'No answer')[:200]}...")

            if test_id.startswith("red_team"):
                print(
                    f"RED TEAM TEST - PASS"
                    if "don't know" in result.get("answer", "").lower()
                    or "not have" in result.get("answer", "").lower()
                    else f"RED TEAM TEST - FAIL"
                )

        except Exception as e:
            print(f"ERROR: {str(e)}")

    print("\n" + "=" * 60)
    print("MEMORY TEST")
    print("=" * 60)

    thread_id = "memory_test"

    result1 = ask(app, "My name is John", thread_id)
    print(f"\nQ1: My name is John")
    print(f"A1: {result1.get('answer', '')[:100]}...")

    result2 = ask(app, "What is my name?", thread_id)
    print(f"\nQ2: What is my name?")
    print(f"A2: {result2.get('answer', '')[:100]}...")

    result3 = ask(app, "Create a study plan for me", thread_id)
    print(f"\nQ3: Create a study plan for me")
    print(f"A3: {result3.get('answer', '')[:200]}...")
    print(f"Memory test - Should remember 'John' in Q3")


if __name__ == "__main__":
    test_questions()
