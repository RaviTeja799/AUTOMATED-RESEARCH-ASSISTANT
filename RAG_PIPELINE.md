# RAG Pipeline

## Flow

```
Question
  → Embed query (sentence-transformers, 384-dim)
  → Search Qdrant Cloud (cosine similarity, top-k)
  → Build citation-aware prompt
  → Generate answer (Groq, temperature=0.3)
  → Extract citations (match answer text to source chunks)
  → Assess confidence (citation count + uncertainty phrases + avg score)
  → Return answer + citations + confidence
```

## Hallucination Prevention

- **Citation enforcement** — every claim must be cited `[Title, Authors, Year]`
- **Grounding instructions** — system prompt forbids external knowledge
- **Uncertainty phrases** — model says "based on provided sources" when partial
- **Missing info handling** — explicit "not in the indexed papers" response
- **Low temperature** — 0.3 for factual accuracy
- **Confidence scoring** — flags low-confidence answers

## Confidence Score

```
confidence = (citations/5 × 0.4) + (1 - uncertainty_count×0.2) × 0.3 + (avg_score/10 × 0.3)
```

- **0.7–1.0** — well-supported, multiple citations
- **0.4–0.7** — partially supported
- **0.0–0.4** — insufficient information

## Caching

Identical `(question, top_k, filters)` tuples are cached for 120 seconds. Cache is in-process (resets on restart).

## Configuration

```env
DEFAULT_TOP_K=5
HYBRID_SEARCH_WEIGHT=0.5
MIN_SIMILARITY_SCORE=0.3
GROQ_MAX_TOKENS=2048
```
