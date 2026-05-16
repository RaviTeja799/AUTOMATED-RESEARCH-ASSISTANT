"""Benchmark script — measures optimization improvements."""
import httpx
import time

BASE = "http://localhost:8000/api/v1"


def test(label, fn):
    t = time.time()
    r = fn()
    elapsed = time.time() - t
    print(f"  {label:<30} HTTP {r.status_code}  {elapsed:.2f}s")
    return r, elapsed


def main():
    print()
    print("=" * 55)
    print("  OPTIMIZATION BENCHMARK")
    print("=" * 55)

    # Health
    r, _ = test("Health check", lambda: httpx.get(f"{BASE}/health", timeout=15))
    h = r.json()
    print(f"    Qdrant={h['qdrant_connected']}  Groq={h['groq_available']}  Status={h['status']}")

    # Query cold
    print()
    print("  QUERY:")
    q = {"question": "How does the attention mechanism work?", "top_k": 5}
    r, t1 = test("  Cold (no cache)", lambda: httpx.post(f"{BASE}/query", json=q, timeout=30))
    if r.status_code == 200:
        d = r.json()
        print(f"    chunks={d['retrieved_chunks']}  confidence={d.get('confidence', 0):.0%}")

    # Query cached
    r, t2 = test("  Cached (same Q)", lambda: httpx.post(f"{BASE}/query", json=q, timeout=30))
    if t2 > 0:
        print(f"    Cache speedup: {t1:.2f}s → {t2:.3f}s  ({t1/t2:.0f}x faster)")

    # Papers list
    print()
    r, _ = test("List papers", lambda: httpx.get(f"{BASE}/papers", timeout=10))
    papers = r.json() if r.status_code == 200 else []
    print(f"    {len(papers)} papers indexed")

    # Summarize
    if papers:
        pid = papers[0]["paper_id"]
        print()
        print("  SUMMARIZE:")
        req = {"paper_id": pid, "summary_type": "brief"}
        r, ts1 = test("  Cold", lambda: httpx.post(f"{BASE}/summarize", json=req, timeout=60))
        r, ts2 = test("  Cached", lambda: httpx.post(f"{BASE}/summarize", json=req, timeout=60))
        if ts2 > 0:
            print(f"    Cache speedup: {ts1:.2f}s → {ts2:.3f}s  ({ts1/ts2:.0f}x faster)")

    print()
    print("=" * 55)


if __name__ == "__main__":
    main()
