"""
upload_test.py — Upload a PDF and run end-to-end tests against it.

Usage:
    python scripts/upload_test.py path/to/paper.pdf

Requires the server to be running at http://localhost:8000
"""
import httpx
import json
import sys
import time
from pathlib import Path

BASE = "http://localhost:8000"


def sep(title):
    print(f"\n{'='*60}\n  {title}\n{'='*60}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/upload_test.py path/to/paper.pdf")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)

    # ── 1. Health ────────────────────────────────────────────────
    sep("1. HEALTH CHECK")
    r = httpx.get(f"{BASE}/api/v1/health", timeout=15)
    h = r.json()
    print(f"  Status   : {h['status']}")
    print(f"  Qdrant   : {'✅ connected' if h['qdrant_connected'] else '❌ down'}")
    print(f"  Groq LLM : {'✅ connected' if h['groq_available'] else '❌ down'}")
    print(f"  Version  : {h['version']}")

    # ── 2. Upload PDF ────────────────────────────────────────────
    sep(f"2. UPLOAD PDF → {pdf_path.name}")
    with open(pdf_path, "rb") as f:
        r = httpx.post(
            f"{BASE}/api/v1/papers/upload",
            files={"file": (pdf_path.name, f, "application/pdf")},
            timeout=120,
        )

    if r.status_code == 409:
        data = r.json()
        print(f"  ⚠️  Duplicate — already uploaded as {data.get('existing_paper_id')}")
        paper_id = data.get("existing_paper_id")
    else:
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
        if data["status"] != "success":
            print(f"\n  ERROR: {data['message']}")
            sys.exit(1)

    # ── 3. List Papers ───────────────────────────────────────────
    sep("3. LIST PAPERS")
    papers = httpx.get(f"{BASE}/api/v1/papers", timeout=10).json()
    print(f"  Total papers in Qdrant: {len(papers)}")
    for p in papers:
        print(f"  - {p.get('paper_id','?')[:8]}… | chunks: {p.get('num_chunks','?')}")

    # ── 4. Queries ───────────────────────────────────────────────
    questions = [
        "What is the main contribution of this paper?",
        "How does the methodology work?",
        "What are the key results?",
    ]

    for i, question in enumerate(questions, 1):
        sep(f"4.{i} QUERY: {question}")
        r = httpx.post(f"{BASE}/api/v1/query", json={"question": question, "top_k": 5}, timeout=30)
        resp = r.json()
        answer = resp.get("answer", "")
        print(f"  Answer: {answer[:300]}{'...' if len(answer) > 300 else ''}")
        print(f"  Chunks: {resp['retrieved_chunks']}  Confidence: {resp.get('confidence','N/A')}  Time: {resp['processing_time']:.1f}s")

    # ── 5. Summarize ─────────────────────────────────────────────
    sep("5. SUMMARIZE PAPER")
    r = httpx.post(f"{BASE}/api/v1/summarize",
                   json={"paper_id": paper_id, "summary_type": "brief"}, timeout=60)
    s = r.json()
    if "summary" in s:
        print(f"  {s['summary'][:300]}...")
        for kf in s.get("key_findings", [])[:3]:
            print(f"  • {kf}")
    else:
        print(f"  {json.dumps(s)[:300]}")

    sep("DONE")
    print(f"  Docs: {BASE}/docs")


if __name__ == "__main__":
    main()
