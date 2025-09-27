# Backend (FastAPI + Playwright)

This backend exposes REST APIs that translate natural language commands into browser automation plans and executes them with Playwright.

## Setup

```cmd
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install
```

## Running the API

```cmd
.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000/docs for the interactive API explorer.

## Environment Variables

| Variable | Description |
| --- | --- |
| `LLM_BACKEND` | Set to `ollama` to enable the local LLM planner adapter. Leave unset to use rule-based fallback. |
| `LLM_MODEL` | Ollama model name (default `llama3`). |
| `API_TOKEN` | Optional. If set, clients must pass the same value in the `X-API-Token` header. |
| `TASK_DB_PATH` | Optional custom path for the SQLite task store. |
| `CORS_ALLOW_ORIGINS` | Comma-separated list of origins allowed for CORS (default enables localhost ports). |

Create a `.env` file in the `backend/` directory to set these values without touching your shell profile. The backend loads it automatically on startup:

```env
# backend/.env
LLM_BACKEND=fallback
LLM_MODEL=llama3
API_TOKEN=change-me
TASK_DB_PATH=storage/tasks.db
CORS_ALLOW_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

Only keep the settings you need; any line can be removed to fall back to the documented defaults.

## Key Components

- `app/models.py` – Pydantic validation for plans and actions.
- `app/planner.py` – Rule-based planner with optional Ollama LLM integration.
- `app/executor.py` – Playwright action dispatcher with retries, scraping, and artifact capture.
- `app/storage.py` – SQLite-based task history and export helpers.
- `app/main.py` – FastAPI routes combining planner, executor, and storage.

## Testing

```cmd
pytest -k test_executor
```

The test executes `backend/test_plan.json` and asserts that scraping results are returned.
