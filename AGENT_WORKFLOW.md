# Agent Workflow Documentation

## Overview

Complete LangChain-based agent system with intent determination, tool orchestration, and conversation memory.

---

## Architecture

```
User Query
     ↓
Intent Classification
     ↓
Agent (ReAct)
     ↓
Tool Selection
     ↓
┌─────────────────────────────────────────┐
│ Available Tools:                        │
│ 1. search_papers                        │
│ 2. answer_question                      │
│ 3. summarize_paper                      │
│ 4. compare_papers                       │
│ 5. generate_literature_review           │
└─────────────────────────────────────────┘
     ↓
Tool Execution (with Memory)
     ↓
Response Synthesis
     ↓
Final Answer
```

---

## Components

### 1. **Tools** (`app/agents/tools.py`)

#### SearchPapersTool
- **Purpose**: Find relevant papers
- **Input**: Search query
- **Output**: List of papers with metadata

#### AnswerQuestionTool
- **Purpose**: Answer questions with RAG
- **Input**: Question
- **Output**: Answer with citations

#### SummarizePaperTool
- **Purpose**: Summarize specific paper
- **Input**: Paper ID
- **Output**: Comprehensive summary

#### ComparePapersTool
- **Purpose**: Compare papers/approaches
- **Input**: Comparison query
- **Output**: Structured comparison

#### GenerateLiteratureReviewTool
- **Purpose**: Generate literature review
- **Input**: Topic
- **Output**: Comprehensive review

### 2. **Research Agent** (`app/agents/research_agent.py`)

**Features:**
- ReAct (Reasoning + Acting) pattern
- Conversation memory
- Multi-step reasoning
- Tool orchestration

**Components:**
- LLM (Ollama)
- Tools (5 research tools)
- Memory (ConversationBufferMemory)
- Agent Executor

### 3. **Intent Classifier** (`app/agents/research_agent.py`)

**Intents:**
- **SEARCH**: Find papers
- **QUESTION**: Answer questions
- **SUMMARIZE**: Summarize papers
- **COMPARE**: Compare papers
- **LITERATURE_REVIEW**: Generate reviews

### 4. **Agent Orchestrator** (`app/agents/research_agent.py`)

**Responsibilities:**
- Intent classification
- Query enhancement
- Agent execution
- Memory management

### 5. **Agent Service** (`app/services/agent_service.py`)

**Responsibilities:**
- Service initialization
- Query processing
- Response formatting
- Session management

---

## Agent Workflow

### Step 1: Intent Classification

```python
query = "What are transformers?"
intent = IntentClassifier.classify(query)
# Returns: "QUESTION"
```

**Intent Keywords:**
- SEARCH: "find", "search", "papers on"
- QUESTION: "what", "how", "why", "explain"
- SUMMARIZE: "summarize", "summary"
- COMPARE: "compare", "versus", "difference"
- LITERATURE_REVIEW: "literature review", "survey"

### Step 2: Agent Reasoning (ReAct)

```
Thought: The user wants to know about transformers
Action: answer_question
Action Input: "What are transformers?"
Observation: [Tool result with answer and citations]
Thought: I now have the answer
Final Answer: [Synthesized response]
```

### Step 3: Tool Execution

Agent selects and executes appropriate tool(s):

```python
# Example: answer_question tool
result = await answer_question_tool.run(
    "What are transformers?"
)
```

### Step 4: Memory Update

Conversation stored in memory:

```python
memory.save_context(
    {"input": "What are transformers?"},
    {"output": "Transformers are..."}
)
```

### Step 5: Response

```json
{
  "answer": "Transformers are neural networks...",
  "intent": "QUESTION",
  "steps": [
    {
      "tool": "answer_question",
      "input": "What are transformers?",
      "output": "Transformers are..."
    }
  ],
  "processing_time": 2.34
}
```

---

## Usage Examples

### Example 1: Search Papers

**Request:**
```json
{
  "query": "Find papers about BERT",
  "use_intent_routing": true
}
```

**Agent Flow:**
1. Intent: SEARCH
2. Tool: search_papers
3. Output: List of BERT papers

### Example 2: Answer Question

**Request:**
```json
{
  "query": "How does attention mechanism work?",
  "use_intent_routing": true
}
```

**Agent Flow:**
1. Intent: QUESTION
2. Tool: answer_question
3. Output: Answer with citations

### Example 3: Compare Papers

**Request:**
```json
{
  "query": "Compare BERT and GPT",
  "use_intent_routing": true
}
```

**Agent Flow:**
1. Intent: COMPARE
2. Tool: compare_papers
3. Output: Structured comparison

### Example 4: Literature Review

**Request:**
```json
{
  "query": "Generate literature review on transformers",
  "use_intent_routing": true
}
```

**Agent Flow:**
1. Intent: LITERATURE_REVIEW
2. Tool: generate_literature_review
3. Output: Comprehensive review

### Example 5: Multi-Step Query

**Request:**
```json
{
  "query": "Find papers about transformers and summarize the most relevant one",
  "use_intent_routing": true
}
```

**Agent Flow:**
1. Intent: SEARCH (primary)
2. Tool 1: search_papers
3. Tool 2: summarize_paper (for top result)
4. Output: Papers + Summary

---

## Memory Management

### Conversation Memory

```python
# Agent remembers context
User: "What are transformers?"
Agent: "Transformers are neural networks..."

User: "How do they differ from RNNs?"
Agent: "Unlike RNNs which we just discussed..."
```

### Clear Memory

```python
# Clear for new conversation
agent_service.clear_memory(session_id="user-123")
```

### Get History

```python
# Retrieve conversation
history = agent_service.get_conversation_history(
    session_id="user-123"
)
```

---

## API Endpoints

### POST /api/v1/agent

Query the agent:

```bash
curl -X POST "http://localhost:8000/api/v1/agent" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are transformers?",
    "use_intent_routing": true,
    "session_id": "user-123"
  }'
```

### POST /api/v1/agent/clear-memory

Clear conversation memory:

```bash
curl -X POST "http://localhost:8000/api/v1/agent/clear-memory" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "user-123"
  }'
```

### GET /api/v1/agent/conversation-history

Get conversation history:

```bash
curl "http://localhost:8000/api/v1/agent/conversation-history?session_id=user-123"
```

---

## Configuration

```python
# In app/core/config.py
AGENT_MAX_ITERATIONS = 5      # Max reasoning steps
AGENT_VERBOSE = True           # Show agent reasoning
OLLAMA_MODEL = "llama3"        # LLM model
OLLAMA_TEMPERATURE = 0.7       # Higher for reasoning
```

---

## Tool Selection Logic

Agent automatically selects tools based on:

1. **Intent classification**
2. **Query analysis**
3. **Previous context** (from memory)
4. **Tool descriptions**

**Selection Examples:**

| Query | Intent | Tool(s) |
|-------|--------|---------|
| "Find papers on X" | SEARCH | search_papers |
| "What is X?" | QUESTION | answer_question |
| "Summarize paper Y" | SUMMARIZE | search_papers → summarize_paper |
| "Compare X and Y" | COMPARE | compare_papers |
| "Literature review on X" | LITERATURE_REVIEW | generate_literature_review |

---

## Advanced Features

### Multi-Step Reasoning

Agent can chain multiple tools:

```
Query: "Find papers about BERT and explain the key innovation"

Step 1: search_papers("BERT")
Step 2: answer_question("What is the key innovation in BERT?")
Step 3: Synthesize results
```

### Context Awareness

Agent uses memory for context:

```
User: "What are transformers?"
Agent: [Explains transformers]

User: "What are their limitations?"
Agent: [Knows "their" refers to transformers from context]
```

### Error Handling

Agent handles errors gracefully:

```python
try:
    result = tool.run(input)
except Exception as e:
    return "I encountered an error. Let me try a different approach..."
```

---

## Testing

### Test Intent Classification

```python
assert IntentClassifier.classify("Find papers") == "SEARCH"
assert IntentClassifier.classify("What is X?") == "QUESTION"
assert IntentClassifier.classify("Compare X and Y") == "COMPARE"
```

### Test Agent

```python
response = await agent_service.process_query(
    query="What are transformers?",
    use_intent_routing=True
)

assert response['answer']
assert response['intent'] == "QUESTION"
assert len(response['steps']) > 0
```

### Test Tools

```python
# Test search tool
result = await search_tool.run("transformers")
assert "Found" in result

# Test answer tool
result = await answer_tool.run("What are transformers?")
assert len(result) > 0
```

---

## Performance

Typical agent query:

```
Intent classification: 0.05s
Tool execution:        1.50s
Response synthesis:    0.30s
Total:                 1.85s
```

---

## Best Practices

1. **Use intent routing** - Improves tool selection
2. **Provide context** - Use session IDs for conversations
3. **Clear memory** - Start fresh when changing topics
4. **Monitor steps** - Check intermediate steps for debugging
5. **Handle errors** - Agent will retry with different approaches

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Wrong tool selected | Check intent classification, adjust keywords |
| Agent loops | Reduce max_iterations, improve tool descriptions |
| Memory issues | Clear memory between sessions |
| Slow responses | Reduce max_iterations, optimize tools |
| No results | Check if papers are indexed |

---

## Files Created

```
app/
├── agents/
│   ├── __init__.py              ✅ Package init
│   ├── tools.py                 ✅ 5 LangChain tools
│   ├── research_agent.py        ✅ Agent + Orchestrator
│   └── callbacks.py             (future)
├── prompts/
│   └── agent_prompts.py         ✅ Agent prompts
├── services/
│   └── agent_service.py         ✅ Agent service
└── api/v1/
    ├── agent.py                 ✅ Agent endpoints
    └── router.py                ✅ Updated router
```

---

## Integration

Agent integrates with:
- ✅ Query Service (RAG)
- ✅ Summarization Service
- ✅ Literature Service
- ✅ Hybrid Retriever
- ✅ Elasticsearch
- ✅ Ollama LLM

---

## Next Steps

Optional enhancements:
- [ ] Custom callbacks for monitoring
- [ ] Streaming responses
- [ ] Multi-agent collaboration
- [ ] Tool result caching
- [ ] Advanced memory (vector store)
- [ ] User feedback loop
