# Agent Workflow

The agent uses LangChain's ReAct pattern with Groq as the LLM backbone.

## Flow

```
POST /api/v1/agent  {"query": "..."}
        │
        ▼
IntentClassifier.classify()
  SEARCH | QUESTION | SUMMARIZE | COMPARE | LITERATURE_REVIEW
        │
        ▼
ResearchAgent.process_query()
  → AgentExecutor.invoke() [thread pool — LangChain is sync]
        │
        ▼
ReAct loop (max 5 iterations):
  Thought → Action → Observation → Thought → Final Answer
        │
        ▼
Response: {answer, intent, steps, processing_time}
```

## Tools

| Tool | Input | When used |
|------|-------|-----------|
| `search_papers` | query string | Finding relevant papers |
| `answer_question` | question | Direct RAG Q&A with citations |
| `summarize_paper` | paper_id | Summarizing a specific paper |
| `compare_papers` | comparison query | Comparing approaches |
| `generate_literature_review` | topic | Broad topic overview |

## Intent Keywords

| Intent | Trigger words |
|--------|--------------|
| SEARCH | find, search, look for, papers on |
| QUESTION | what, how, why, when, explain, describe |
| SUMMARIZE | summarize, summary, overview of paper |
| COMPARE | compare, difference, versus, vs, contrast |
| LITERATURE_REVIEW | literature review, state of the art, survey |

## Memory

`ConversationBufferMemory` — stores the full conversation history per agent instance. Clear it between unrelated sessions:

```bash
POST /api/v1/agent/clear-memory
GET  /api/v1/agent/conversation-history
```

## Configuration

```env
AGENT_MAX_ITERATIONS=5   # Max ReAct steps
AGENT_VERBOSE=False      # Set True to log reasoning steps
GROQ_MODEL=llama-3.1-8b-instant
```
