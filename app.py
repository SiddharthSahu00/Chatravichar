"""
NoteForge Streamlit UI
Streamlit deployment for the NoteForge agent.
"""

__version__ = "0.1.0"

import streamlit as st
from sentence_transformers import SentenceTransformer
import chromadb
from langgraph.checkpoint.memory import MemorySaver
from langchain_groq import ChatGroq
import os
from dotenv import load_dotenv

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


@st.cache_resource
def initialize_components():
    """Initialize LLM, embedder, ChromaDB, and compiled graph."""

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

    return app, collection, embedder


def main():
    st.set_page_config(
        page_title="NoteForge - AI Learning Assistant", page_icon="📝", layout="wide"
    )

    st.title("📝 NoteForge")
    st.markdown("*Transform your learning materials into structured notes*")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "thread_id" not in st.session_state:
        st.session_state.thread_id = "default"

    with st.sidebar:
        st.header("About NoteForge")
        st.markdown("""
        **NoteForge** is an AI assistant that helps you:
        
        - 📚 Generate structured notes
        - 📝 Create revision sheets
        - 🗺️ Build concept maps
        - 📋 Generate study plans
        - ❓ Create quizzes
        
        **Topics covered:**
        - Note generation techniques
        - Summarization methods
        - Study planning
        - Self-assessment
        - Faithfulness evaluation
        """)

        if st.button("New Conversation"):
            st.session_state.messages = []
            st.session_state.thread_id = (
                f"thread_{hash(str(st.session_state.messages))}"
            )
            st.rerun()

    app, _, _ = initialize_components()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input(
        "Ask about note-taking, study techniques, or any topic from the knowledge base..."
    ):
        with st.chat_message("user"):
            st.markdown(prompt)

        st.session_state.messages.append({"role": "user", "content": prompt})

try:
            st.session_state.messages.append({"role": "user", "content": prompt})

            initial_state: NoteForgeState = {
                "question": prompt,
                "messages": list(st.session_state.get("app_messages", [])),
                "route": "",
                "retrieved": "",
                "sources": [],
                "tool_result": "",
                "answer": "",
                "faithfulness": 0.0,
                "eval_retries": 0,
                "user_name": st.session_state.get("user_name", None),
            }

            config = {"configurable": {"thread_id": st.session_state.thread_id}}

            with st.spinner("Thinking..."):
                result = app.invoke(initial_state, config)

            answer = result.get("answer", "I couldn't generate a response.")
            faithfulness = result.get("faithfulness", 0.0)
            
            st.session_state["app_messages"] = list(result.get("messages", []))
            st.session_state["user_name"] = result.get("user_name")

            answer = result.get("answer", "I couldn't generate a response.")
            faithfulness = result.get("faithfulness", 0.0)

            with st.chat_message("assistant"):
                st.markdown(answer)
                st.caption(f"Faithfulness score: {faithfulness:.2f}")

            st.session_state.messages.append({"role": "assistant", "content": answer})

        except Exception as e:
            st.error(f"Error: {str(e)}")


if __name__ == "__main__":
    main()
