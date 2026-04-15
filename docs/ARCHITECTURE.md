# Architecture

## Flow

```
User Question
     ↓
[memory_node] → Add to history, extract name
     ↓
[router_node] → LLM decides route
     ↓
┌────┴────┬──────────┐
↓         ↓          ↓
retrieve   tool    skip
     ↓     ↓         ↓
     └─────┴────────┘
            ↓
      [answer_node] → Generate response
            ↓
        [eval_node] → Check faithfulness
            ↓
     ┌────┴────┐
     ↓         ↓
   retry     save
     ↓
  [answer_node]
```

## Components

- **LangGraph**: Agent orchestration with 8 nodes
- **ChromaDB**: Vector store for RAG
- **SentenceTransformer**: Document embeddings
- **Groq LLM**: Language model
- **MemorySaver**: Conversation persistence
- **Streamlit**: Web UI