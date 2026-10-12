"""Low-concurrency spot check for the two external-API endpoints that were
deliberately excluded from stress_test.py's 10/100/1000 tiers:

  - POST /api/geocode            -> calls OpenStreetMap Nominatim (1 req/s policy)
  - POST /generate_travel_plans/random -> calls the paid DeepSeek LLM

Geocode calls are sent sequentially, spaced >=1.1s apart, to respect
Nominatim's usage policy. Trip planning is run at a small, real concurrency
(3) since each call has a real (small) cost. See ../stress_test_report.md
section 2b for the results this produced.

Usage: same account setup as stress_test.py; fill in EMAIL/USERNAME/PASSWORD
below, then `python stress_test_external.py`. Delete the test account after.
"""
import asyncio
import statistics
import time
from datetime import date, timedelta

import httpx

BASE_URL = "http://localhost"
USERNAME = "stresstest2"
PASSWORD = "TestPassw0rd!1"
EMAIL = "stresstest2@example.com"

CITIES = ["Vienna", "Prague", "Berlin", "Warsaw", "Rome"]


def summarize(label, results, wall_time):
    oks = [r for r in results if r["ok"]]
    fails = [r for r in results if not r["ok"]]
    latencies = [r["elapsed"] for r in results]
    print(f"\n--- {label} (n={len(results)}) ---")
    print(f"  wall clock: {wall_time:.2f}s")
    print(f"  success:    {len(oks)}/{len(results)}")
    if fails:
        for f in fails:
            print(f"    FAIL: status={f.get('status')} error={f.get('error')}")
    for i, r in enumerate(results):
        print(f"  [{i}] ok={r['ok']} status={r.get('status')} elapsed={r['elapsed']*1000:.0f}ms")
    if latencies:
        print(f"  mean: {statistics.mean(latencies)*1000:.0f}ms  min: {min(latencies)*1000:.0f}ms  max: {max(latencies)*1000:.0f}ms")


async def one_geocode(client, token, place):
    start = time.perf_counter()
    try:
        resp = await client.post(
            "/api/geocode",
            json={"places": [place], "language": "en"},
            headers={"Authorization": f"Bearer {token}"},
        )
        elapsed = time.perf_counter() - start
        return {"ok": resp.status_code == 200, "status": resp.status_code, "elapsed": elapsed, "body": resp.text[:200]}
    except Exception as e:
        elapsed = time.perf_counter() - start
        return {"ok": False, "error": str(e)[:150], "elapsed": elapsed}


async def one_plan(client, token, start_date, end_date):
    start = time.perf_counter()
    try:
        resp = await client.post(
            "/generate_travel_plans/random",
            json={
                "startingPoint": "Budapest, Hungary",
                "startDate": start_date,
                "endDate": end_date,
                "people": 1,
                "preferredTransport": "allModes",
                "preferences": [],
                "likedPlaces": [],
                "dislikedPlaces": [],
                "language": "en",
            },
            headers={"Authorization": f"Bearer {token}"},
            timeout=180.0,
        )
        elapsed = time.perf_counter() - start
        return {"ok": resp.status_code == 200, "status": resp.status_code, "elapsed": elapsed, "body": resp.text[:200]}
    except Exception as e:
        elapsed = time.perf_counter() - start
        return {"ok": False, "error": str(e)[:150], "elapsed": elapsed}


async def main():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        resp = await client.post(
            "/api/login", json={"username": USERNAME, "email": EMAIL, "password": PASSWORD}
        )
        resp.raise_for_status()
        token = resp.json()["access_token"]

    # --- Geocode: sequential, spaced >=1.1s apart to respect Nominatim's 1 req/s policy ---
    print("\n" + "=" * 60 + "\nGEOCODE (sequential, 1.1s spacing - Nominatim policy)\n" + "=" * 60)
    results = []
    start_all = time.perf_counter()
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        for city in CITIES:
            r = await one_geocode(client, token, city)
            results.append(r)
            await asyncio.sleep(1.1)
    wall = time.perf_counter() - start_all
    summarize(f"GEOCODE x{len(CITIES)}", results, wall)

    # --- Trip planning: 3 concurrent real DeepSeek-backed generations ---
    print("\n" + "=" * 60 + "\nTRIP PLANNING (3 concurrent, random strategy)\n" + "=" * 60)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=180.0) as client:
        start_date = (date.today() + timedelta(days=7)).isoformat()
        end_date = (date.today() + timedelta(days=12)).isoformat()
        tasks = [one_plan(client, token, start_date, end_date) for _ in range(3)]
        start = time.perf_counter()
        results = await asyncio.gather(*tasks)
        wall = time.perf_counter() - start
    summarize("TRIP PLANNING x3", results, wall)


if __name__ == "__main__":
    asyncio.run(main())
