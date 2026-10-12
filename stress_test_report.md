# API Stress Test Report — Planventure Backend

**Date:** 2026-10-04, re-run and updated 2026-10-12.
**Target:** `http://localhost` (nginx reverse proxy → FastAPI backend → PostgreSQL), full local Docker Compose stack (`frontend`, `backend`, `db` containers), as run in production topology.

## 1. Methodology

A Python `asyncio` + `httpx.AsyncClient` script fired bursts of fully concurrent requests (`asyncio.gather`, no ramp-up) at three concurrency tiers: **10, 100, and 1000 simulated users**. Each tier ran two phases:

1. **LOGIN phase** — N concurrent `POST /api/login` requests against a single pre-verified test account. This exercises the full authentication path: user lookup (`crud.get_user_by_username`), bcrypt password verification, JWT issuance, and — critically — a DB connection checkout for every request.
2. **READ phase** — N concurrent authenticated `GET` requests, split evenly between `GET /api/visited-places` and `GET /api/planned-trips`, using a single valid JWT obtained beforehand. This exercises typical authenticated read traffic (DB query + response serialization), without the bcrypt cost of login.

Two endpoints that call real external, paid/rate-limited third-party APIs were **deliberately excluded from the 10/100/1000 concurrency tiers**: `/generate_travel_plans/*` (calls the paid DeepSeek LLM) and `POST /api/geocode` (calls OpenStreetMap's Nominatim, whose free-tier usage policy caps requests at 1/second). Firing hundreds or thousands of simultaneous real calls at either would cost real money, risk a provider-side ban, and would mostly measure the *external* service's capacity rather than this app's own. Both were instead spot-checked separately at a small, policy-respecting scale — see §2b.

Each request's wall-clock latency was recorded individually; HTTP timeout was set generously (60s client-side) so that slow responses would be captured rather than aborted early, to reveal true backend behavior under load rather than client impatience.

## 2. Results

Two full runs were made, 8 days apart, with the same methodology; both show the same pattern (comfortable at 10, badly degraded at 100, non-functional at 1000), with the exact figures varying somewhat run-to-run as expected under this kind of saturation test. The 2026-10-12 re-run's figures are shown below (2026-10-04 original figures in parentheses where notably different).

| Tier | Phase | Success rate | Throughput | p50 latency | p95 latency | Max latency |
|---|---|---|---|---|---|---|
| **10**   | LOGIN | 10/10 (100%)  | 19.1 req/s | 511 ms (255 ms)  | 517 ms   | 517 ms   |
| **10**   | READ  | 10/10 (100%)  | 28.5 req/s | 340 ms (55 ms)   | 350 ms   | 350 ms   |
| **100**  | LOGIN | 74/100 (74%, was 88%)  | 3.1 req/s  | 31,067 ms | 31,661 ms | 31,740 ms |
| **100**  | READ  | 100/100 (100%) | 122.8 req/s | 606 ms (329 ms)  | 709 ms   | 727 ms   |
| **1000** | LOGIN | 33/1000 (3.3%, was 6.2%) | 13.2 req/s | 67,531 ms | 75,292 ms | 75,920 ms |
| **1000** | READ  | 0/1000 (0%)   | 13.0 req/s | 70,666 ms | 76,160 ms | 76,310 ms |

### Failure breakdown (2026-10-12 run)

| Tier | Phase | Failures |
|---|---|---|
| 100  | LOGIN | 26× HTTP 500 (DB pool checkout timeout) |
| 1000 | LOGIN | 35× HTTP 500, 114× client-side error (connection reset/timeout), 818× HTTP 504 (nginx gateway timeout) |
| 1000 | READ  | 849× HTTP 504, 151× client-side error |

## 2b. External API endpoints (geocode, trip planning) — low-concurrency spot check

Run separately from the tiers above, against a fresh test account, to respect external provider limits while still gathering real latency data. Figures below are from the 2026-10-12 re-run (2026-10-04 original in parentheses where notably different).

**Geocode** — 5 sequential `POST /api/geocode` calls (different city names), spaced 1.1s apart to stay within Nominatim's 1 req/s policy:

| # | Status | Latency |
|---|---|---|
| 1 | 200 | 359 ms |
| 2 | 200 | 90 ms |
| 3 | 200 | 106 ms |
| 4 | 200 | 92 ms |
| 5 | 200 | 81 ms |

5/5 succeeded, mean 145ms (was 226ms), max 359ms. No issues at this scale.

**Trip planning** — 3 concurrent `POST /generate_travel_plans/random` calls (real DeepSeek-backed generation, 5-day Budapest-origin trip):

| # | Status | Latency |
|---|---|---|
| 1 | 200 | 12,338 ms |
| 2 | 200 | 15,222 ms |
| 3 | 200 | 16,332 ms |

3/3 succeeded, mean 14.6s (was 6.37s — DeepSeek's own response time varies run to run), wall clock 16.3s (the three ran essentially in parallel with no contention between them). At this small scale, neither the DB pool nor the DeepSeek API showed any sign of strain — consistent with §3's finding that the bottleneck is connection-pool capacity, which 3 concurrent long-running requests don't come close to exhausting. This result should **not** be extrapolated to higher concurrency: a real 100-or-1000-user burst against this endpoint would hit the same 30-connection DB pool ceiling as the LOGIN/READ tests (each plan generation holds a connection for several seconds, far longer than a login or read), likely *before* DeepSeek's own capacity became the limiting factor — but was not measured directly, for the cost/rate-limit reasons above.

## 3. Root cause (confirmed from backend logs, not inferred)

The backend container's own logs captured the exact failure during the test window:

```
sqlalchemy.exc.TimeoutError: QueuePool limit of size 10 overflow 20 reached,
connection timed out, timeout 30.00
(Background on this error at: https://sqlalche.me/e/21/3o7r)
```

`backend/database/database.py` configures the SQLAlchemy engine with:

```python
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=False,
)
```

This caps the application at **30 concurrent database connections** (`pool_size` + `max_overflow`), independent of how many HTTP requests arrive simultaneously. Every request — including a simple `GET /api/visited-places` — needs to check out one connection from this pool for the duration of its query.

- At **10 concurrent users**, demand (≤10 connections) stays well under the 30-connection ceiling → full success, low latency.
- At **100 concurrent users**, the login burst alone demands up to 100 connections at once. The ~70 requests beyond the pool's capacity queue for a free connection; those that wait longer than SQLAlchemy's 30-second pool-checkout timeout fail outright with HTTP 500 (12-26 across the two runs — see the failure breakdown table). The ones that succeed are delayed by the queue, producing the ~31s latencies seen even for *successful* logins.
- At **1000 concurrent users**, the queue never meaningfully drains. Most login requests exceed nginx's default `proxy_read_timeout` (60s) before the backend can even respond, surfacing to the client as HTTP 504 (699-818 of 1000 across the two runs). The subsequent READ phase then starts with the connection pool still saturated by in-flight/queued work from the login storm — pool exhaustion has no "cooldown," it only clears as fast as queued requests finish or time out — so **every** read in that phase also stalled past the timeout window (0% success).

### Secondary bottleneck

`login()` in `backend/routers/auth.py` is declared as a **synchronous** route (`def login(...)`, not `async def`). FastAPI/Starlette runs sync routes in a thread pool (default size 40). Each call performs a CPU-bound bcrypt hash comparison, measured at **~200-250ms per call** even under the unloaded 10-user baseline. This is a second, independent concurrency ceiling (40 worker threads) layered on top of the 30-connection DB pool ceiling — both had to be exhausted before requests could proceed at the higher tiers, compounding the slowdown.

## 4. Interpretation

The application's request-handling *logic* is fast — the 10-user baseline shows login in roughly a quarter to half a second and reads in well under half a second (see §2), both reasonable. The collapse at 100 and 1000 concurrent users is **not** a symptom of inefficient queries or slow code; it is a direct, measured consequence of a connection pool sized for light/single-developer use (30 total connections) being asked to serve far more simultaneous requests than it can hold open at once. The system degrades predictably: comfortable at ~10 concurrent users, significantly degraded with partial failures around 100, and non-functional at 1000 under the current configuration.

## 5. Possible remediations (not applied — reported for reference only)

- Raise `pool_size`/`max_overflow` in `backend/database/database.py` to match realistic expected concurrency, and tune PostgreSQL's own `max_connections` accordingly.
- Convert `login()` (and other hot sync routes) to `async def` with a non-blocking bcrypt call (e.g. run bcrypt in `asyncio.to_thread` explicitly, or use an async-friendly password library), so authentication doesn't compete with database I/O for the same limited Starlette thread pool.
- Consider a connection pooler (e.g. PgBouncer) in front of PostgreSQL if horizontal scaling of backend instances is ever introduced, so pool limits are centrally managed rather than per-process.
- Add explicit timeout/backpressure handling (e.g. return HTTP 503 with a `Retry-After` header once the pool is saturated) instead of letting requests queue silently until nginx's generic 504.

## 6. Test artifacts

- Scripts: `load_testing/stress_test.py` (10/100/1000 LOGIN/READ tiers) and `load_testing/stress_test_external.py` (low-concurrency geocode/trip-planning spot check), both committed to the repository.
- Environment: local Docker Compose stack, single backend replica, default resource limits (no explicit CPU/memory caps set on the `backend` container).
- Test accounts created and deleted for each run; no persistent data changes.
- Maps: not a separate backend endpoint — the map view renders visited-place markers (already covered by the READ test, `GET /api/visited-places`) on a client-side Leaflet map against static GeoJSON, so there was nothing distinct left to test there.
