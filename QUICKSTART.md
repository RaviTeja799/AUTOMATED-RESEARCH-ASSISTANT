# Quick Start

## Prerequisites

- Python 3.11+
- Free [Groq API key](https://console.groq.com) — sign up, create key
- Free [Qdrant Cloud cluster](https://cloud.qdrant.io) — sign up, create cluster, copy URL + API key

---

## Setup

```bash
# 1. Clone
git clone https://github.com/vamsi-op/AUTOMATED-RESEARCH-ASSISTANT.git
cd AUTOMATED-RESEARCH-ASSISTANT

# 2. Install
pip install -r requirements.txt

# 3. Configure
cp .env.example .env
```

Edit `.env`:
```env
GROQ_API_KEY=gsk_your_key_here
QDRANT_URL=https://your-cluster.europe-west3-0.gcp.cloud.qdrant.io
QDRANT_API_KEY=eyJhbGci...
```

```bash
# 4. Run
python main.py
```

Open **http://localhost:8000** — the web UI loads automatically.

---

## Using the UI

1. **Upload tab** — drag and drop a PDF. Processing takes ~10s for a typical paper.
2. **Chat tab** — ask questions. Answers include citations and confidence scores.
3. **Papers tab** — see all indexed papers, delete them.
4. **Summarize tab** — pick a paper, choose summary type.
5. **Lit Review tab** — enter a topic, get themes/gaps/future directions.

---

## API Examples

```bash
# Upload a paper
curl -X POST http://localhost:8000/api/v1/papers/upload -F "file=@paper.pdf"

# Ask a question
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the main contribution?", "top_k": 5}'

# Summarize
curl -X POST http://localhost:8000/api/v1/summarize \
  -H "Content-Type: application/json" \
  -d '{"paper_id": "your-paper-id", "summary_type": "comprehensive"}'

# Health check
curl http://localhost:8000/api/v1/health
```

Expected health response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "qdrant_connected": true,
  "groq_available": true
}
```

---

## Docker

```bash
cp .env.example .env   # fill in your keys
docker-compose up
```

---

## Troubleshooting

**Qdrant connection failed**
- Check `QDRANT_URL` and `QDRANT_API_KEY` in `.env`
- Verify cluster is running at https://cloud.qdrant.io

**Groq not available**
- Check `GROQ_API_KEY` in `.env`
- Verify key at https://console.groq.com

**PDF processing fails**
- Ensure PDF is not password-protected
- Max size: 50MB (configurable via `MAX_UPLOAD_SIZE_MB`)
- Check logs: `logs/app.log`

**Out of memory during embedding**
```env
EMBEDDING_BATCH_SIZE=8
CHUNK_SIZE=256
```

**Port in use**
```bash
uvicorn app.main:app --port 8001
```
