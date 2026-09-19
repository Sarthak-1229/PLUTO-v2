import time, json, pathlib, sys
import requests

API_URL = "http://127.0.0.1:8000/process"

TEST_CASES = [
    ("Smalltalk greeting", "hi"),
    ("Simple math", "what is 15% of 340"),
    ("Research CEO Nvidia", "who is the current CEO of Nvidia"),
    ("Repeat research", "who is the current CEO of Nvidia"),
    ("Ambiguous binary search", "explain how binary search works"),
    ("Vague ML question", "tell me about machine learning"),
]

def send_query(query):
    start = time.perf_counter()
    try:
        resp = requests.post(API_URL, json={"text": query}, timeout=30)
        total = time.perf_counter() - start
        if resp.status_code != 200:
            return {"error": f"HTTP {resp.status_code}", "total": total}
        data = resp.json()
        return {
            "query": query,
            "answer": data.get("answer", ""),
            "audio_uri": data.get("audio_uri", ""),
            "total": total,
        }
    except Exception as e:
        return {"error": str(e), "total": time.perf_counter() - start}

def audit_ui():
    # Very lightweight UI audit: fetch the served index.html and look for obvious markers.
    ui_path = pathlib.Path("ui/index.html")
    if not ui_path.exists():
        return {"error": "ui/index.html not found"}
    content = ui_path.read_text(encoding="utf-8", errors="ignore")
    # Simple heuristics: check for known control strings.
    controls = {
        "voice": "voice" in content.lower(),
        "knowledge": "knowledge" in content.lower(),
        "reports": "report" in content.lower(),
        "settings": "settings" in content.lower(),
    }
    return controls

def main():
    results = []
    for desc, q in TEST_CASES:
        res = send_query(q)
        res["description"] = desc
        results.append(res)
    ui_audit = audit_ui()
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "test_results": results,
        "ui_audit": ui_audit,
    }
    out_path = pathlib.Path("audit_report.md")
    with out_path.open("w", encoding="utf-8") as f:
        f.write("# Audit Report\n\n")
        f.write(f"Generated on {report['timestamp']}\n\n")
        f.write("## Test Cases\n\n")
        for r in results:
            f.write(f"### {r.get('description')}\n")
            f.write(f"- Query: `{r.get('query')}`\n")
            if r.get('error'):
                f.write(f"- Error: {r['error']}\n")
                f.write(f"- Total time: {r['total']:.3f}s\n\n")
                continue
            f.write(f"- Answer: {r.get('answer')[:200]}\n")
            f.write(f"- Total latency: {r['total']:.3f}s\n\n")
        f.write("## UI Audit\n\n")
        if isinstance(ui_audit, dict):
            for k, v in ui_audit.items():
                f.write(f"- {k.capitalize()} control present: {v}\n")
        else:
            f.write(f"- Error: {ui_audit}\n")
    print("Audit report written to", out_path)

if __name__ == "__main__":
    main()
