from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.executor import execute_plan
from app.models import validate_plan

pytest.importorskip("playwright")


def load_plan() -> Path:
    return Path(__file__).resolve().parent.parent / "test_plan.json"


@pytest.mark.slow
@pytest.mark.integration
def test_execute_plan_returns_results() -> None:
    plan_data = json.loads(load_plan().read_text(encoding="utf-8"))
    plan = validate_plan(plan_data).plan

    result = execute_plan(plan, headless=True)

    assert result["success"] is True
    heading = result["results"].get("heading")
    assert heading, "Expected heading to be captured"
    paragraphs = result["results"].get("paragraphs")
    assert paragraphs, "Expected paragraphs to be captured"
