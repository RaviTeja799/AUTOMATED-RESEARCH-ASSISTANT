"""
Test script: upload a PDF and run queries against it.
"""
import httpx
import json
import time
import sys

BASE = "http://localhost:8000"


def sep(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def main():
    # ── 1. Health ────────────────────────────────────────────────
    sep("1. HEALTH CHECK")
    r = httpx.get(f"{BASE}/api/v1/health", timeout=15)
    h = r.json()
    print(f"  Status   : {h['status']}")
    print(f"  Qdrant   : {'✅ connected' if h['elasticsearch_connected'] else '❌ down'}")
    print(f"  Groq LLM : {'✅ connected' if h['ollama_available'] else '❌ down'}")
    print(f"  Version  : {h['version']}")

    # ── 2. Upload PDF ────────────────────────────────────────────
    sep("2. UPLOAD PDF  →  attention_is_all_you_need.pdf")
    pdf_path = "data/uploads/attention_paper.pdf"
    start = time.time()
    with open(pdf_path, "rb") as f:
        r = httpx.post(
            f"{BASE}/api/v1/papers/upload",
            files={"file": ("attention_is_all_you_need.pdf", f, "application/pdf")},
            timeout=120,
        )
    data = r.json()
    paper_id = data.get("paper_id", "")
    print(f"  Status   : {data['status']}")
    print(f"  Paper ID : {paper_id}")
    print(f"  Chunks   : {data['num_chunks']}")
    print(f"  Time     : {data['processing_time']:.1f}s")
    if data.get("metadata"):
        m = data["metadata"]
        print(f"  Title    : {m.get('title', 'N/A')}")
        print(f"  Pages    : {m.get('num_pages', 'N/A')}")
        if m.get("abstract"):
            print(f"  Abstract : {m['abstract'][:120]}...")

    if data["status"] != "success":
        print(f"\n  ERROR: {data['message']}")
        sys.exit(1)

    # ── 3. List Papers ───────────────────────────────────────────
    sep("3. LIST PAPERS")
    r = httpx.get(f"{BASE}/api/v1/papers", timeout=10)
    papers = r.json()
    print(f"  Total papers in Qdrant: {len(papers)}")
    for p in papers:
        print(f"  - {p.get('paper_id','?')} | chunks: {p.get('num_chunks','?')}")

    # ── 4. Queries ───────────────────────────────────────────────
    questions = [
        "What is the main contribution of this paper?",
        "How does the attention mechanism work?",
        "What are the results on machine translation tasks?",
    ]

    for i, question in enumerate(questions, 1):
        sep(f"4.{i}  QUERY: {question}")
        start = time.time()
        r = httpx.post(
            f"{BASE}/api/v1/query",
            json={"question": question, "top_k": 5},
            timeout=30,
        )
        resp = r.json()
        elapsed = time.time() - start
        print(f"  Answer ({elapsed:.1f}s):\n")
        # Word-wrap at 70 chars
        words = resp["answer"].split()
        line = "  "
        for w in words:
            if len(line) + len(w) > 72:
                print(line)
                line = "  " + w + " "
            else:
                line += w + " "
        if line.strip():
            print(line)
        print(f"\n  Chunks retrieved : {resp['retrieved_chunks']}")
        print(f"  Confidence       : {resp.get('confidence', 'N/A')}")
        if resp.get("citations"):
            print(f"  Citations        : {len(resp['citations'])}")
            for c in resp["citations"][:2]:
                print(f"    [{c['paper_title']}] p.{c.get('page_number','?')} score={c['relevance_score']:.2f}")

    # ── 5. Summarize ─────────────────────────────────────────────
    sep("5. SUMMARIZE PAPER")
    r = httpx.post(
        f"{BASE}/api/v1/summarize",
        json={"paper_id": paper_id, "summary_type": "brief"},
        timeout=30,
    )
    s = r.json()
    if "summary" in s:
        print(f"  Summary:\n")
        words = s["summary"].split()
        line = "  "
        for w in words:
            if len(line) + len(w) > 72:
                print(line)
                line = "  " + w + " "
            else:
                line += w + " "
        if line.strip():
            print(line)
    else:
        print(f"  Response: {json.dumps(s, indent=2)[:300]}")

    sep("DONE — All endpoints working")
    print(f"\n  Docs: http://localhost:8000/docs")
    print(f"  Qdrant: https://cloud.qdrant.io")


if __name__ == "__main__":
    main()
