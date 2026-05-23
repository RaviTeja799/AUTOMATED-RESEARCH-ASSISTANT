"""
demo.py — Quick demo that queries the already-uploaded papers.

Usage:
    python scripts/demo.py

Requires the server to be running at http://localhost:8000
"""
import httpx

BASE = "http://localhost:8000"


def wrap(text, width=65, indent="  "):
    words = text.split()
    lines, line = [], indent
    for w in words:
        if len(line) + len(w) + 1 > width:
            lines.append(line)
            line = indent + w
        else:
            line += (" " if line != indent else "") + w
    if line.strip():
        lines.append(line)
    return "\n".join(lines)


def section(title):
    print(f"\n{'─'*60}\n  {title}\n{'─'*60}")


def main():
    # ── Health ────────────────────────────────────────────────────
    section("HEALTH")
    h = httpx.get(f"{BASE}/api/v1/health", timeout=15).json()
    print(f"  Status       : {h['status'].upper()}")
    print(f"  Qdrant Cloud : {'✅' if h['qdrant_connected'] else '❌'}")
    print(f"  Groq LLM     : {'✅' if h['groq_available'] else '❌'}")

    # ── Papers ────────────────────────────────────────────────────
    section("INDEXED PAPERS")
    papers = httpx.get(f"{BASE}/api/v1/papers", timeout=10).json()
    print(f"  Total: {len(papers)} paper(s) in Qdrant Cloud")
    for p in papers:
        print(f"\n  Paper ID : {p['paper_id']}")
        print(f"  Chunks   : {p['num_chunks']}")
        print(f"  Sections : {', '.join(p.get('sections', [])) or 'N/A'}")

    if not papers:
        print("\n  No papers indexed. Upload one first via the web UI or API.")
        return

    # ── Queries ───────────────────────────────────────────────────
    questions = [
        ("How does the attention mechanism work?", "Core concept"),
        ("What are the BLEU scores on WMT 2014 English-to-German?", "Specific results"),
        ("What are the limitations of this approach?", "Critical analysis"),
    ]

    for question, label in questions:
        section(f"QUERY [{label}]")
        print(f"  Q: {question}\n")
        r = httpx.post(f"{BASE}/api/v1/query", json={"question": question, "top_k": 5}, timeout=60)
        if r.status_code != 200:
            print(f"  ERROR {r.status_code}: {r.text[:200]}")
            continue
        resp = r.json()
        print(wrap(resp["answer"]))
        print(f"\n  Chunks: {resp['retrieved_chunks']}  Confidence: {resp.get('confidence','N/A')}  Time: {resp['processing_time']:.1f}s")

    # ── Summarize ─────────────────────────────────────────────────
    section("SUMMARIZE PAPER")
    r = httpx.post(f"{BASE}/api/v1/summarize",
                   json={"paper_id": papers[0]["paper_id"], "summary_type": "brief"}, timeout=60)
    if r.status_code == 200:
        s = r.json()
        print(wrap(s.get("summary", "No summary returned")))
        for kf in s.get("key_findings", [])[:3]:
            print(f"  • {kf}")

    section("DONE")
    print(f"  Web UI   : {BASE}")
    print(f"  API Docs : {BASE}/docs")
    print(f"  Live     : https://vamsi-op-automated-research-assistant.hf.space")


if __name__ == "__main__":
    main()

# ── Papers ────────────────────────────────────────────────────
section("INDEXED PAPERS")
papers = httpx.get(f"{BASE}/api/v1/papers", timeout=10).json()
print(f"  Total: {len(papers)} paper(s) in Qdrant Cloud")
for p in papers:
    meta = p.get("metadata", {})
    print(f"\n  Paper ID : {p['paper_id']}")
    print(f"  Chunks   : {p['num_chunks']}")
    print(f"  Sections : {', '.join(p.get('sections', [])) or 'N/A'}")

# ── Queries ───────────────────────────────────────────────────
questions = [
    ("How does the attention mechanism work?",
     "Core concept question"),
    ("What are the BLEU scores on WMT 2014 English-to-German?",
     "Specific results question"),
    ("What are the limitations of this approach?",
     "Critical analysis question"),
]

for question, label in questions:
    section(f"QUERY  [{label}]")
    print(f"  Q: {question}\n")
    r = httpx.post(
        f"{BASE}/api/v1/query",
        json={"question": question, "top_k": 5},
        timeout=60,
    )
    if r.status_code != 200:
        print(f"  ERROR {r.status_code}: {r.text[:200]}")
        continue
    resp = r.json()
    print(wrap(resp["answer"]))
    print(f"\n  Chunks used : {resp['retrieved_chunks']}")
    print(f"  Confidence  : {resp.get('confidence', 'N/A')}")
    print(f"  Time        : {resp['processing_time']:.1f}s")
    if resp.get("citations"):
        print(f"  Citations   : {len(resp['citations'])}")

# ── Summarize ─────────────────────────────────────────────────
section("SUMMARIZE PAPER")
paper_id = papers[0]["paper_id"] if papers else None
if paper_id:
    r = httpx.post(
        f"{BASE}/api/v1/summarize",
        json={"paper_id": paper_id, "summary_type": "brief"},
        timeout=60,
    )
    if r.status_code == 200:
        s = r.json()
        print(wrap(s.get("summary", "No summary returned")))
        if s.get("key_findings"):
            print("\n  Key Findings:")
            for kf in s["key_findings"][:3]:
                print(f"    • {kf}")
    else:
        print(f"  {r.status_code}: {r.text[:200]}")

section("DONE")
print(f"  API Docs : http://localhost:8000/docs")
print(f"  GitHub   : https://github.com/vamsi-op/AUTOMATED-RESEARCH-ASSISTANT")
print()
