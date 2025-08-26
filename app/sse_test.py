# sse_test.py
import requests

SID = "LIVE_DEMO"
url = f"http://127.0.0.1:8000/chat-events/events?sid={SID}"

print(f"Connecting to {url} ...")
with requests.get(url, stream=True, timeout=30) as r:
    r.raise_for_status()
    print("Connected. Waiting for events (Ctrl+C to quit)...")
    for raw in r.iter_lines(decode_unicode=True):
        if raw is None:
            continue
        line = raw.strip()
        if not line:
            # blank line separates SSE events
            print("-" * 40)
            continue
        print(line)
