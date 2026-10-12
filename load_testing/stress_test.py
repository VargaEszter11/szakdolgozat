"""Ad-hoc load test: 10/100/1000 concurrent users against LOGIN and READ.

Fires fully concurrent bursts (asyncio.gather, no ramp-up) at three tiers
against the full Docker Compose stack (nginx -> backend -> PostgreSQL).
See ../stress_test_report.md for methodology and the results this produced.

Usage:
    1. Register and email-verify a test account, e.g.:
         curl -X POST http://localhost/api/register -H "Content-Type: application/json" \
           -d '{"username":"stresstest1","email":"stresstest1@example.com","password":"TestPassw0rd!1"}'
         docker exec <db-container> psql -U postgres -d <db> -c \
           "UPDATE users SET email_verified = true WHERE email = 'stresstest1@example.com';"
    2. Fill in EMAIL/USERNAME/PASSWORD below to match.
    3. python stress_test.py
    4. Delete the test account afterwards.
"""
import asyncio
import statistics
import time

import httpx

BASE_URL = "http://localhost"
EMAIL = "stresstest1@example.com"
USERNAME = "stresstest1"
PASSWORD = "TestPassw0rd!1"

TIERS = [10, 100, 1000]


def summarize(label, results, wall_time):
    oks = [r for r in results if r["ok"]]
    fails = [r for r in results if not r["ok"]]
    latencies = sorted(r["elapsed"] for r in results)
    n = len(latencies)

    def pct(p):
        if not latencies:
            return float("nan")
        idx = min(n - 1, int(round(p / 100 * (n - 1))))
        return latencies[idx]

    print(f"\n--- {label} (n={len(results)}) ---")
    print(f"  wall clock:     {wall_time:.2f}s")
    print(f"  throughput:     {len(results) / wall_time:.1f} req/s")
    print(f"  success:        {len(oks)}/{len(results)} ({100 * len(oks) / len(results):.1f}%)")
    if fails:
        status_counts = {}
        for f in fails:
            key = f.get("status") or f.get("error") or "unknown"
            status_counts[key] = status_counts.get(key, 0) + 1
        print(f"  failures:       {status_counts}")
    if latencies:
        print(f"  latency min:    {min(latencies) * 1000:.0f}ms")
        print(f"  latency p50:    {pct(50) * 1000:.0f}ms")
        print(f"  latency p95:    {pct(95) * 1000:.0f}ms")
        print(f"  latency p99:    {pct(99) * 1000:.0f}ms")
        print(f"  latency max:    {max(latencies) * 1000:.0f}ms")
        print(f"  latency mean:   {statistics.mean(latencies) * 1000:.0f}ms")


async def one_login(client: httpx.AsyncClient):
    start = time.perf_counter()
    try:
        resp = await client.post(
            "/api/login",
            json={"username": USERNAME, "email": EMAIL, "password": PASSWORD},
        )
        elapsed = time.perf_counter() - start
        return {"ok": resp.status_code == 200, "status": resp.status_code, "elapsed": elapsed}
    except Exception as e:
        elapsed = time.perf_counter() - start
        return {"ok": False, "error": str(e)[:80], "elapsed": elapsed}


async def one_read(client: httpx.AsyncClient, token: str, path: str):
    start = time.perf_counter()
    try:
        resp = await client.get(path, headers={"Authorization": f"Bearer {token}"})
        elapsed = time.perf_counter() - start
        return {"ok": resp.status_code == 200, "status": resp.status_code, "elapsed": elapsed}
    except Exception as e:
        elapsed = time.perf_counter() - start
        return {"ok": False, "error": str(e)[:80], "elapsed": elapsed}


async def run_tier(n: int, token: str):
    limits = httpx.Limits(max_connections=n + 50, max_keepalive_connections=n + 50)
    timeout = httpx.Timeout(60.0)

    # Phase 1: N concurrent logins (same account - exercises bcrypt + user lookup under load)
    async with httpx.AsyncClient(base_url=BASE_URL, limits=limits, timeout=timeout) as client:
        start = time.perf_counter()
        results = await asyncio.gather(*[one_login(client) for _ in range(n)])
        wall = time.perf_counter() - start
    summarize(f"LOGIN x{n}", results, wall)

    # Phase 2: N concurrent authenticated reads, split across two list endpoints
    async with httpx.AsyncClient(base_url=BASE_URL, limits=limits, timeout=timeout) as client:
        tasks = []
        for i in range(n):
            path = "/api/visited-places" if i % 2 == 0 else "/api/planned-trips"
            tasks.append(one_read(client, token, path))
        start = time.perf_counter()
        results = await asyncio.gather(*tasks)
        wall = time.perf_counter() - start
    summarize(f"READ  x{n}", results, wall)


async def main():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        resp = await client.post(
            "/api/login", json={"username": USERNAME, "email": EMAIL, "password": PASSWORD}
        )
        resp.raise_for_status()
        token = resp.json()["access_token"]

    for n in TIERS:
        print(f"\n{'=' * 60}\nTIER: {n} concurrent users\n{'=' * 60}")
        await run_tier(n, token)


if __name__ == "__main__":
    asyncio.run(main())
