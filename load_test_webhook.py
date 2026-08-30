#!/usr/bin/env python3
"""Burst-test /telegram/webhook and report p50/p95/p99 latency."""
from __future__ import annotations
import argparse, asyncio, json, time
import httpx

def percentile(values: list[float], p: float) -> float:
    if not values: return 0.0
    values = sorted(values)
    index = min(len(values)-1, max(0, int(round((p/100)*(len(values)-1)))))
    return values[index]

async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--secret", required=True)
    parser.add_argument("--requests", type=int, default=500)
    parser.add_argument("--concurrency", type=int, default=500)
    args = parser.parse_args()
    semaphore = asyncio.Semaphore(args.concurrency)
    latencies, statuses = [], []
    async with httpx.AsyncClient(timeout=15.0) as client:
        async def one(i: int) -> None:
            async with semaphore:
                payload = {"update_id": 900000000+i, "message": {"message_id": i, "date": int(time.time()), "chat": {"id": 900000000+i, "type": "private"}, "from": {"id": 900000000+i, "is_bot": False, "first_name": "LoadTest"}, "text": "/start"}}
                started = time.perf_counter()
                response = await client.post(args.url, headers={"X-Telegram-Bot-Api-Secret-Token": args.secret, "content-type": "application/json"}, content=json.dumps(payload))
                latencies.append((time.perf_counter()-started)*1000)
                statuses.append(response.status_code)
        await asyncio.gather(*(one(i) for i in range(args.requests)))
    p95 = percentile(latencies, 95)
    print(f"requests={len(latencies)} concurrency={args.concurrency}")
    print(f"status_2xx={sum(200<=s<300 for s in statuses)} status_5xx={sum(s>=500 for s in statuses)}")
    print(f"p50_ms={percentile(latencies,50):.1f} p95_ms={p95:.1f} p99_ms={percentile(latencies,99):.1f}")
    ok = p95 < 1500 and all(s < 500 for s in statuses)
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
