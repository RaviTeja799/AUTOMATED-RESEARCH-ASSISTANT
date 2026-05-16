# RAG Implementation Summary

## What's implemented

| Feature | Status | Notes |
|---------|--------|-------|
| PDF ingestion pipeline | ✅ | PyMuPDF → pdfplumber → pypdf fallback |
| Section detection | ✅ | Abstract, Intro, Methods, Results, Conclusion |
| Semantic chunking | ✅ | Sentence-aware, 512 chars, 50 overlap |
| Qdrant Cloud indexing | ✅ | 384-dim cosine, payload indexes on paper_id/section |
| Semantic search | ✅ | `query_points` API |
| RAG Q&A | ✅ | Citation-aware, hallucination prevention |
| Query TTL cache | ✅ | 120s in-process cache |
| Paper summarization | ✅ | JSON-structured output from Groq |
| Literature review | ✅ | Themes, gaps, future directions |
| LangChain agent | ✅ | ReAct + 5 tools + conversation memory |
| Web UI | ✅ | Single-page, 5 tabs, Tailwind CSS |
| Health endpoint | ✅ | Checks Qdrant + Groq connectivity |

## Known limitations / planned improvements

- `embed_query()` is synchronous — blocks event loop during inference. Wrap in `run_in_executor` for production.
- `list_papers()` does N+1 Qdrant scrolls. Cache paper metadata at index time.
- `get_paper_ids()` scrolls entire collection. Maintain a separate ID set.
- Agent re-instantiated per request. Make it a singleton with per-request memory.
- No persistent query cache (resets on restart). Add Redis for production.
