# Test Instructions

This project provides automated and manual checks to verify the Web Navigator AI Agent end to end.

## 1. Environment Preparation

1. Install Python 3.10+ and Node.js 18+ (LTS).
2. Ensure Playwright browsers are installed once via `playwright install`.
3. (Optional) Install Ollama and pull a local model (e.g., `ollama pull llama3`).

## 2. Backend Unit / Integration Tests

```cmd
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install
pytest -k test_executor --maxfail=1
```

This runs the integration test that executes `test_plan.json` with Playwright headless Chromium. Ensure outbound network access is available for `https://example.com`.

## 3. Manual End-to-End Test

1. Start the backend API:
   ```cmd
   cd backend
   .venv\Scripts\activate
   uvicorn app.main:app --reload
   ```
2. In a new terminal, start the frontend:
   ```cmd
   cd frontend\nextjs-app
   npm install
   npm run dev
   ```
3. Open `http://localhost:3000` in a browser.
4. Issue the sample command `Search laptops under 50000 and list top 5 links and short descriptions.`
5. Confirm:
   - Response panel shows `success: true` and populated results.
   - Logs list the executed plan actions.
   - Task history updates with the new task.
   - Export buttons download CSV/JSON snapshots.

## 4. Planner LLM Smoke Test (Optional)

With Ollama running locally:

```cmd
set LLM_BACKEND=ollama
set LLM_MODEL=llama3
curl -X POST http://localhost:8000/api/command ^
  -H "Content-Type: application/json" ^
  -d "{\"command\":\"search laptops under 50000 and return top 5\"}"
```

Verify the response includes a valid plan and execution result. Logs will contain the raw LLM output for troubleshooting.

## 5. Storage & Export Check

1. After running at least one command, call the task list endpoint:
   ```cmd
   curl http://localhost:8000/api/tasks
   ```
2. Note a task `id` and download JSON export:
   ```cmd
   curl http://localhost:8000/api/export/<task_id>?format=json -o task.json
   ```
3. Repeat for CSV and open the file to ensure it contains stored results.

Following the steps above validates planner generation, executor reliability, persistence, and frontend interactions.
