# Lumacorp API

FastAPI service exposing EVE Online market and wallet metrics, plus Prometheus instrumentation for dashboards.

## Quick Start
- **Local (Poetry)**: Install Python 3.11, run `poetry install`, then `poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`.
- **Docker Compose**: `docker-compose up --build` (binds `:8000`, mounts `./data` for persistence).

## Configuration
Provide a `.env` file (or environment variables):
- `EVE_CLIENT_ID`, `EVE_CLIENT_SECRET`, `EVE_CALLBACK_URL` (OAuth)
- `REFRESH_TOKEN_SECRET` (JWT refresh handling)
- Optional: `CHARACTER_ID`, `CORP_ID`, `REGION_ID`, `AVG_DAILY_VOLUME_WINDOW`, `MAX_PROFIT_INDEXES`, `MIN_PROFIT_THRESHOLD`, `DATABASE_URL`
- Caching: `REDIS_URL` (default `redis://localhost:6379/0`) for profitability snapshots, corp blueprint lookups, and wallet balance cache.
- Scheduling: `PROFIT_REFRESH_SECONDS` (default 86400), `WALLET_REFRESH_SECONDS` (default 300)

## Project Layout
- `app/main.py` – FastAPI app with background market refresher
- `app/routes/` – Endpoints (`auth`, `metrics`)
- `app/market.py`, `app/wallet.py` – Market profitability and wallet logic
- `app/db.py`, `app/models/`, `app/crud/` – Database setup and access
- `data/` – SQLite DB, SDE dumps, cached market data (gitignored)
- `prometheus/` – Metrics configs/artifacts

## Endpoints (summary)
- `GET /auth/login` – Redirect to EVE SSO
- `GET /auth/callback?code=...` – Exchange code for tokens
- `GET /metrics/` – Prometheus exposition (wallet + item profitability gauges)

## Development Notes
- Use 4-space indentation, type hints, and snake_case.
- Prefer `poetry run` for commands; quick sanity check: `poetry run python -m py_compile $(find app -name '*.py')`.
- Keep secrets out of git; ensure `data/` stays uncommitted.
