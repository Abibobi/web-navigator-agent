from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import quote_plus
from uuid import uuid4

from .adapters.llm_ollama import OllamaClient, OllamaError, detect_model_from_env, load_prompt_template
from .models import PlanModel, validate_plan
from .config import get_settings

LOGGER = logging.getLogger("planner")
LOGGER.setLevel(logging.INFO)

SETTINGS = get_settings()

_DEFAULT_MASTER_PROMPT = """SYSTEM: You are a local planning assistant. Your job is to convert a user's natural-language web task into a strict JSON plan for a browser automation Executor. ONLY OUTPUT VALID JSON (no commentary, no markdown, no extra fields). The top-level object must be:
{
  "plan": {
    "id": "<short-id>",
    "description": "<one-line description>",
    "actions": [ <action-objects-array> ],
    "output": { "type": "json" | "csv", "max_results": 10 }
  }
}

Allowed action types (strict): 
- goto (url)
- click (selector)
- fill (selector, value)
- press (key)  // supports "Enter", "ArrowDown"
- wait_for (selector | millis)
- scrape (selector, extract: text|html|attr, attr_name?)
- evaluate (js_code)  // returns value
- screenshot (path)
- select (selector, value)
- scroll (x,y | to="bottom")
- back
- forward
- set_cookie (name,value,domain)
- clear_cookies
- download (selector) // returns path
- pause (millis)

Each action object MUST contain:
{
  "id": "a1",
  "type": "<one of allowed>",
  "description": "<human-readable>",
  "selector": "<css or xpath> (optional)",
  "url": "<for goto>",
  "value": "<for fill/select>",
  "extract": {"type":"text"|"html"|"attr", "attr":"href" (optional)},
  "wait_for": {"selector":"", "timeout": 10000} (optional),
  "retry": {"count": 2, "delay": 1000} (optional),
  "store_as": "<key>" (optional)
}

Constraints:
- Max 20 actions in plan.
- For scraping, include "store_as" to collect results under that key.
- Provide explicit waits after navigation or actions that change DOM.
- If task requires searching (e.g., Google or Amazon), planner should use a stable path: goto -> fill(selector) -> press("Enter") -> wait_for(result_selector) -> scrape(result_selector).
- If uncertain, split task to sub-steps and ask to confirm (but in this project planner must NOT prompt the user mid-execution; instead generate safe conservative steps).
- ALWAYS include selectors when possible; otherwise use robust fallback (search box by name or input[type='search']).
- Output only JSON (the executor will validate it). If the task cannot be done (e.g., requires login or paid data), respond with a plan with a single action of type "evaluate" that returns an explanation in the "result_error" field.
"""

_GOOGLE_CONSENT_SCRIPT = """
(async () => {
    const selectors = [
        'button#L2AGLb',
        'button[aria-label="Accept all"]',
        'button[aria-label="Agree to the use of cookies and other data for the purposes described"]'
    ];
    const btn = selectors.map((s) => document.querySelector(s)).find(Boolean);
    if (btn) {
        btn.click();
        return 'consent accepted';
    }
    return 'no consent prompt';
})()
""".strip()


@lru_cache()
def _load_master_prompt() -> str:
    docs_path = Path(__file__).resolve().parents[2] / "docs" / "MASTER_PROMPT.md"
    try:
        return load_prompt_template(docs_path)
    except FileNotFoundError:
        LOGGER.warning("MASTER_PROMPT.md not found at %s, using embedded default", docs_path)
        return _DEFAULT_MASTER_PROMPT


def _new_plan_id() -> str:
    return f"plan_{uuid4().hex[:8]}"


def _extract_search_query(command: str) -> str:
    cleaned = command.strip()
    cleaned = re.sub(r"^(search|find|lookup)\s+for\s+", "", cleaned, flags=re.IGNORECASE)
    return cleaned


def _rule_based_google_plan(command: str) -> Optional[PlanModel]:
    query = _extract_search_query(command)
    if not query:
        return None

    search_url = (
        "https://www.google.com/search?q="
        f"{quote_plus(query)}"
        "&hl=en&gl=us&pws=0&uule=w+CAIQICIuV2FzaGluZ3RvbiwgRGlzdHJpY3Qgb2YgQ29sdW1iaWEsIFVTQQ=="
    )

    plan: Dict[str, Any] = {
        "plan": {
            "id": _new_plan_id(),
            "description": f"Search Google for '{query}' and scrape top results",
            "actions": [
                {
                    "id": "a1",
                    "type": "goto",
                    "url": search_url,
                    "description": "Open Google search results",
                },
                {
                    "id": "a2",
                    "type": "evaluate",
                    "description": "Dismiss Google consent dialog if it appears",
                    "value": _GOOGLE_CONSENT_SCRIPT,
                },
                {
                    "id": "a3",
                    "type": "wait_for",
                    "description": "Ensure Google search box is visible",
                    "selector": "input[name='q']",
                    "wait_for": {"selector": "input[name='q']", "timeout": 20000},
                },
                {
                    "id": "a4",
                    "type": "wait_for",
                    "description": "Wait for search results container",
                    "selector": "#search, div.MjjYud",
                    "wait_for": {"selector": "#search", "timeout": 35000},
                },
                {
                    "id": "a5",
                    "type": "scrape",
                    "selector": "#search .g, div.MjjYud",
                    "description": "Scrape search result blocks",
                    "extract": {"type": "text"},
                    "store_as": "results",
                    "retry": {"count": 2, "delay": 800},
                },
            ],
            "output": {"type": "json", "max_results": 5},
        }
    }
    return validate_plan(plan).plan


def _rule_based_wikipedia_plan(command: str) -> Optional[PlanModel]:
    match = re.search(r"wikipedia[^\w]+(?:page\s+)?'?(?P<title>[^']+)'?", command, re.IGNORECASE)
    title = match.group("title").strip() if match else None
    if not title:
        title = command

    plan: Dict[str, Any] = {
        "plan": {
            "id": _new_plan_id(),
            "description": f"Open Wikipedia for {title} and capture intro",
            "actions": [
                {
                    "id": "a1",
                    "type": "goto",
                    "url": "https://www.wikipedia.org",
                    "description": "Open Wikipedia home",
                },
                {
                    "id": "a2",
                    "type": "wait_for",
                    "selector": "input[name='search']",
                    "description": "Wait for search box",
                },
                {
                    "id": "a3",
                    "type": "fill",
                    "selector": "input[name='search']",
                    "value": title,
                    "description": "Enter topic name",
                },
                {
                    "id": "a4",
                    "type": "press",
                    "value": "Enter",
                    "description": "Submit search",
                    "wait_for": {"selector": "#firstHeading", "timeout": 15000},
                },
                {
                    "id": "a5",
                    "type": "scrape",
                    "selector": "p",
                    "description": "Scrape first paragraph",
                    "extract": {"type": "text"},
                    "store_as": "paragraphs",
                    "retry": {"count": 2, "delay": 500},
                },
            ],
            "output": {"type": "json", "max_results": 3},
        }
    }
    return validate_plan(plan).plan


def _rule_based_plan(command: str) -> Optional[PlanModel]:
    lower_command = command.lower()
    if "search" in lower_command or "google" in lower_command:
        return _rule_based_google_plan(command)
    if "wikipedia" in lower_command:
        return _rule_based_wikipedia_plan(command)
    return None


def _extract_json(text: str) -> Dict[str, Any]:
    candidate = text.strip()
    if not candidate:
        raise ValueError("Empty LLM response")

    if candidate.startswith("{"):
        cleaned = candidate
    else:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("LLM response does not contain JSON object")
        cleaned = candidate[start : end + 1]

    return json.loads(cleaned)


def _call_ollama(prompt: str) -> str:
    model_name = SETTINGS.llm_model or detect_model_from_env()
    client = OllamaClient(model=model_name)
    if not client.is_available():
        raise OllamaError("Configured Ollama backend is not available")
    return client.generate(prompt)


def generate_plan(command: str) -> PlanModel:
    if not command or not command.strip():
        raise ValueError("Command must be a non-empty string")

    command = command.strip()
    master_prompt = _load_master_prompt()
    fallback_plan = _rule_based_plan(command)

    backend_raw = SETTINGS.llm_backend or "fallback"
    backend = backend_raw.strip().lower()
    prompt = f"{master_prompt.strip()}\n\nUSER COMMAND:\n{command}\n"

    if backend == "ollama":
        try:
            raw_output = _call_ollama(prompt)
            LOGGER.info("LLM raw output: %s", raw_output)
            plan_data = _extract_json(raw_output)
            return validate_plan(plan_data).plan
        except (OllamaError, ValueError, json.JSONDecodeError) as exc:
            LOGGER.warning("LLM planner failed, switching to rule-based fallback: %s", exc, exc_info=True)
            if fallback_plan:
                return fallback_plan
            raise

    if fallback_plan:
        LOGGER.warning(
            "LLM backend not configured (LLM_BACKEND=%s). Using rule-based planner for command: %s",
            backend_raw,
            command,
        )
        return fallback_plan

    raise RuntimeError(
        "Unable to generate plan. Set LLM_BACKEND=ollama with a local model or use a supported command for fallback."
    )
