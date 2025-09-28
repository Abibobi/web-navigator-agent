# Web Navigator AI Agent

> Build an AI agent that takes natural language instructions and autonomously drives the web on a local computer. Must be fully functional offline/local (no cloud). It should:
> - Use a locally running LLM for understanding and planning ( LLaMA / Ollama local models).
> - Use browser automation (Playwright) to control a browser (headless or headful).
> - Turn user commands into a strict JSON "plan" (list of actions).
> - Execute the JSON plan reliably and return structured outputs (JSON/CSV).
> - Include optional features: multi-step reasoning & task chaining, task memory, retries/error handling, a simple Next.js GUI, export results, and voice input (client-side Web Speech API).
>
> **Constraints:**
> 1. All integrations must be local and no-cost.
> 2. Use Playwright for browser control.
> 3. Backend in Python (FastAPI) + LangChain optional for orchestration if used locally only.
> 4. Frontend in Next.js (React) — local dev only.
> 5. Provide robust error handling & logging.
> 6. Provide an example plan (`test_plan.json`) and at least one end-to-end test scenario.

## Repository Layout

```
backend/
  app/
    main.py
    planner.py
    executor.py
    models.py
    storage.py
    adapters/
      llm_ollama.py
  test_plan.json
  requirements.txt
  README-backend.md
frontend/
  nextjs-app/
    pages/
      _app.jsx
      index.jsx
    components/
      ChatBox.jsx
      TaskList.jsx
    utils/
      voice.js
    styles/
      globals.css
    package.json
  README-frontend.md
docs/
  MASTER_PROMPT.md
  PlanSchema.md
README.md
_demo_commands.txt_
_test_instructions.md_
```

## Quick Start

### Backend

```cmd
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install
uvicorn app.main:app --reload --port 8000
```

### Frontend

```cmd
cd frontend\nextjs-app
npm install
npm run dev
```

Open http://localhost:3000 to access the UI.

## Environment Variables

| Variable | Component | Description |
| --- | --- | --- |
| `LLM_BACKEND` | Backend | Set to `ollama` to use local Ollama adapter. Leave unset to enable rule-based fallback planner. |
| `LLM_MODEL` | Backend | Ollama model identifier (default `llama3`). |
| `API_TOKEN` | Backend | Optional. Require clients to send matching `X-API-Token`. |
| `TASK_DB_PATH` | Backend | Override SQLite storage location. |
| `CORS_ALLOW_ORIGINS` | Backend | Comma-separated list of origins for CORS (default: localhost ports). |
| `NEXT_PUBLIC_AGENT_API_URL` | Frontend | Base URL for backend API (default `http://localhost:8000`). |
| `NEXT_PUBLIC_API_TOKEN` | Frontend | Optional token forwarded in `X-API-Token`. |

## Planner & LLM Integration

- `docs/MASTER_PROMPT.md` contains the exact system prompt used by `planner.py`.
- The planner loads the prompt, concatenates the user command, and attempts to call the configured LLM backend.
- When `LLM_BACKEND` is not set to `ollama` or the LLM fails, the rule-based fallback covers common search/wikipedia tasks.

### Ollama Adapter

1. Install [Ollama](https://ollama.ai) locally and download a model:
   ```cmd
   ollama pull llama3
   ```
2. Run Ollama server (usually starts automatically).
3. Set environment variables before launching the backend:
   ```cmd
   set LLM_BACKEND=ollama
   set LLM_MODEL=llama3
   ```

## Executor

- Uses Playwright Chromium to execute plans.
- Supports retries, waits, scraping, evaluation, downloads, cookies, navigation.
- Stores action outputs keyed by `store_as`, returned in the `results` payload.

## Storage & Exports

- Results persist in SQLite (`storage/tasks.db`).
- `/api/tasks` returns history, `/api/task/{id}` returns detail, `/api/export/{id}` downloads JSON or CSV snapshots.

## Frontend UI

- React/Next.js client with command input, toggles, voice input, result viewer, and task list.
- Fetches backend API directly; configure proxy via `.env.local` if needed.

## Demo Commands

See `demo_commands.txt` for 10 ready-to-run natural language instructions covering search, e-commerce, news, finance, etc.

## Tests

Read `test_instructions.md` for detailed steps. Key command:

```cmd
cd backend
pytest -k test_executor --maxfail=1
```

This uses `backend/test_plan.json` to exercise the executor in headless mode.

## Troubleshooting

- **Playwright not installed**: run `playwright install` once inside the backend virtual environment.
- **Ollama connection errors**: ensure Ollama service is running locally and the model is pulled. Logs in `planner.py` emit raw responses.
- **Voice input missing**: Available only in browsers that implement the Web Speech API (Chrome). Provide manual input otherwise.

## Roadmap & Optional Enhancements

- Multi-step chaining and confirmation flows.
- Richer memory replay and task resume.
- Local text-to-speech for results (browser speechSynthesis or backend `pyttsx3`).
- Authentication via API token (already supported) and role-based UI.
