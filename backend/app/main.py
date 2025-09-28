from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .executor import execute_plan
from .models import PlanModel
from .planner import generate_plan
from .storage import export_task, get_task, list_tasks, save_task
from .config import get_settings

LOGGER = logging.getLogger("api")
LOGGER.setLevel(logging.INFO)

SETTINGS = get_settings()


async def _require_token(x_api_token: Optional[str] = Header(default=None, alias="X-API-Token")) -> None:
    if SETTINGS.api_token and x_api_token != SETTINGS.api_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API token")

app = FastAPI(title="Web Navigator AI Agent", version="0.1.0", dependencies=[Depends(_require_token)])

app.add_middleware(
    CORSMiddleware,
    allow_origins=SETTINGS.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=(
        ["Authorization", "Content-Type", "X-API-Token"]
        if SETTINGS.api_token
        else ["*"]
    ),
)


class CommandRequest(BaseModel):
    command: str = Field(min_length=3)
    headless: bool = True
    record_screenshots: bool = False


class CommandResponse(BaseModel):
    success: bool
    task_id: Optional[str]
    plan: Dict[str, Any]
    results: Dict[str, Any]
    logs: list[str]
    errors: list[str]


@app.post("/api/command", response_model=CommandResponse)
async def handle_command(payload: CommandRequest) -> CommandResponse:
    LOGGER.info("Received command: %s", payload.command)
    plan_model: PlanModel = await run_in_threadpool(generate_plan, payload.command)
    execution_result = await run_in_threadpool(
        execute_plan,
        plan_model,
        headless=payload.headless,
        record_screenshots=payload.record_screenshots,
    )

    task_payload = {
        "command": payload.command,
        "plan": plan_model.dict(),
        "result": execution_result,
    }

    task_id = await run_in_threadpool(save_task, payload.command, task_payload["plan"], execution_result)

    return CommandResponse(
        success=execution_result.get("success", False),
        task_id=task_id,
        plan=plan_model.dict(),
        results=execution_result.get("results", {}),
        logs=execution_result.get("logs", []),
        errors=execution_result.get("errors", []),
    )


@app.get("/api/tasks")
async def handle_list_tasks() -> Dict[str, Any]:
    tasks = await run_in_threadpool(list_tasks)
    return {"tasks": tasks}


@app.get("/api/task/{task_id}")
async def handle_get_task(task_id: str) -> Dict[str, Any]:
    task = await run_in_threadpool(get_task, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@app.get("/api/export/{task_id}")
async def handle_export_task(
    task_id: str,
    format: str = Query(default="json", pattern="^(json|csv)$"),
) -> FileResponse:
    path = await run_in_threadpool(export_task, task_id, format)
    media_type = "application/json" if format == "json" else "text/csv"
    filename = path.name
    return FileResponse(path, media_type=media_type, filename=filename)


@app.get("/")
async def root() -> Dict[str, str]:
    return {"status": "ok", "message": "Web Navigator AI Agent backend"}
