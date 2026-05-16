"""Quick demo - queries the already-uploaded paper."""
import httpx, json

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
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print('─'*60)

# ── Health ────────────────────────────────────────────────────
section("HEALTH")
h = httpx.get(f"{BASE}/api/v1/health", timeout=15).json()
print(f"  Status       : {h['status'].upper()}")
print(f"  Qdrant Cloud : {'✅' if h['elasticsearch_connected'] else '❌'}")
print(f"  Groq LLM     : {'✅' if h['ollama_available'] else '❌'}")

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
