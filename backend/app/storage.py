from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .config import get_settings

SETTINGS = get_settings()
BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = SETTINGS.task_db_path
if not DB_PATH.is_absolute():
    DB_PATH = (BASE_DIR / DB_PATH).resolve()
EXPORT_DIR = (BASE_DIR / "exports")


def _ensure_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                command TEXT NOT NULL,
                plan_json TEXT NOT NULL,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.commit()


def _connect() -> sqlite3.Connection:
    _ensure_db()
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def save_task(command: str, plan_json: Dict[str, Any], result_json: Dict[str, Any], timestamp: Optional[str] = None) -> str:
    task_id = uuid4().hex[:10]
    created_at = timestamp or datetime.utcnow().isoformat() + "Z"
    with _connect() as connection:
        connection.execute(
            "INSERT INTO tasks (id, command, plan_json, result_json, created_at) VALUES (?, ?, ?, ?, ?)",
            (
                task_id,
                command,
                json.dumps(plan_json, ensure_ascii=False),
                json.dumps(result_json, ensure_ascii=False),
                created_at,
            ),
        )
        connection.commit()
    return task_id


def list_tasks(limit: int = 50) -> List[Dict[str, Any]]:
    with _connect() as connection:
        cursor = connection.execute(
            "SELECT id, command, created_at FROM tasks ORDER BY datetime(created_at) DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    with _connect() as connection:
        cursor = connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "command": row["command"],
            "created_at": row["created_at"],
            "plan": json.loads(row["plan_json"]),
            "result": json.loads(row["result_json"]),
        }


def export_task(task_id: str, export_format: str = "json") -> Path:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    task = get_task(task_id)
    if not task:
        raise ValueError(f"Task {task_id} not found")

    if export_format.lower() == "json":
        target = EXPORT_DIR / f"{task_id}.json"
        target.write_text(json.dumps(task["result"], indent=2, ensure_ascii=False), encoding="utf-8")
        return target

    if export_format.lower() == "csv":
        return _export_csv(task_id, task["result"])

    raise ValueError("Unsupported export format. Use 'json' or 'csv'.")


def _export_csv(task_id: str, result: Dict[str, Any]) -> Path:
    import csv

    target = EXPORT_DIR / f"{task_id}.csv"
    rows: List[Dict[str, Any]] = []
    for key, value in result.get("results", result).items():
        if isinstance(value, list):
            for index, item in enumerate(value):
                rows.append(
                    {
                        "key": key,
                        "index": index,
                        "value": json.dumps(item, ensure_ascii=False) if isinstance(item, (dict, list)) else str(item),
                    }
                )
        else:
            rows.append({"key": key, "index": 0, "value": json.dumps(value, ensure_ascii=False)})

    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["key", "index", "value"])
        writer.writeheader()
        writer.writerows(rows)
    return target
