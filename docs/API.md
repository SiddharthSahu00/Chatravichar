# API Documentation

## State Structure

```python
class NoteForgeState(TypedDict):
    question: str           # User's question
    messages: List[str]    # Conversation history
    route: str             # retrieve, tool, or memory_only
    retrieved: str         # Retrieved context from ChromaDB
    sources: List[str]     # Source document topics
    tool_result: str       # Result from local tools
    answer: str            # Final generated answer
    faithfulness: float    # Faithfulness score (0.0-1.0)
    eval_retries: int      # Number of retry attempts
    user_name: Optional[str]  # User's name if provided
```

## Node Functions

### memory_node
- Appends user question to messages
- Extracts user name if mentioned
- Applies sliding window (keeps last 12 messages)

### router_node
- Decides route: retrieve, tool, or memory_only
- Uses LLM to determine appropriate route

### retrieval_node
- Embeds question using SentenceTransformer
- Queries ChromaDB for top 3 relevant documents
- Returns formatted context with topic labels

### tool_node
- Handles local text analysis requests
- Tools: outline generation, quiz generation, text statistics

### answer_node
- Generates final answer using LLM
- Includes context from retrieval or tools
- Handles retry escalation for low faithfulness

### eval_node
- Scores answer faithfulness (0.0-1.0)
- Triggers retry if below 0.7 threshold
- Max 2 retries before accepting

### save_node
- Appends answer to message history
- Prepares state for next turn