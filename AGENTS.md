# Repository Guidelines

## Project Structure & Module Organization
- API entrypoint at `app/main.py` (FastAPI with background market loader); routes live in `app/routes/` (`auth.py`, `metrics.py`), shared logic in `app/market.py`, `app/wallet.py`, and DB models in `app/models/`.
- Settings come from `app/config.py` (.env-backed `pydantic-settings`), database setup in `app/db.py`, reusable helpers in `app/utils/`.
- Persistent data (SQLite `data/lumacorp.db`, SDE dumps, cached market files) stay under `data/` and are volume-mounted in Docker. Avoid committing new binaries here.
- Prometheus artifacts/configs sit in `prometheus/`; adjust exporters here when adding metrics.

## Build, Test, and Development Commands
- Install deps: `poetry install` (preferred) or `pip install -r app/requirements.txt` inside a Python 3.11 venv.
- Run API locally: `poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` (loads background data fetcher).
- Dockerized run: `docker-compose up --build` (binds :8000, mounts `./data` for persistence).
- Lint/type-check: `poetry run python -m py_compile $(find app -name '*.py')` for a quick sanity check if no linter is configured.

## Coding Style & Naming Conventions
- Use 4-space indentation, type hints throughout, and snake_case for functions/variables; keep path operations async-friendly in FastAPI endpoints.
- Pydantic models and settings should define explicit field types/defaults; validate external data at boundaries (routes, ESI client responses).
- Keep modules cohesive (routes for I/O, `crud/` for DB access, helpers in `utils/`); prefer small, composable functions.

## Testing Guidelines
- No automated tests exist yet; add `pytest`-style tests under a new `tests/` directory with files named `test_*.py`.
- Favor unit tests around market calculations (`app/market.py`) and wallet logic (`app/wallet.py`); use fixtures to isolate DB interactions (in-memory SQLite is acceptable).
- Run with `poetry run pytest` once added; target deterministic inputs and avoid hitting live ESI endpoints.

## Commit & Pull Request Guidelines
- Recent history favors short, lowercase summaries (e.g., `fix average volume calculation`); continue using concise, present-tense messages with a single focus.
- Keep branches small and PRs scoped; include a brief description, linked issue (if any), config changes (.env keys), and screenshots of new metrics when relevant.
- Note any data migrations or background-task impacts; call out changes that alter exported Prometheus metric names/labels.

## Security & Configuration Tips
- Never commit `.env`, tokens, or refreshed SDE/market dumps. Ensure `data/` stays gitignored.
- Update `app/config.py` defaults cautiously; prefer new env vars over hardcoded secrets. When adding scopes, document them near `settings.scopes`.
