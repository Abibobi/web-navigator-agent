from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from .models import ActionModel, PlanModel

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

LOGGER = logging.getLogger("executor")
LOGGER.setLevel(logging.INFO)

ARTIFACTS_DIR = Path("artifacts")


class ExecutionError(RuntimeError):
    pass


def _ensure_artifacts_dir() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


def _wait_after_action(action: ActionModel, page) -> None:
    wait_spec = action.wait_for
    if not wait_spec:
        return
    if wait_spec.selector:
        page.wait_for_selector(wait_spec.selector, timeout=wait_spec.timeout)
    elif wait_spec.millis:
        time.sleep(wait_spec.millis / 1000)


def _do_goto(page, action: ActionModel) -> None:
    page.goto(action.url, wait_until="domcontentloaded")


def _do_click(page, action: ActionModel) -> None:
    page.click(action.selector)


def _do_fill(page, action: ActionModel) -> None:
    page.fill(action.selector, action.value or "")


def _do_press(page, action: ActionModel) -> None:
    if action.selector:
        page.press(action.selector, action.value)
    else:
        page.keyboard.press(action.value)


def _do_wait_for(page, action: ActionModel) -> None:
    timeout = 15000
    if action.wait_for and action.wait_for.timeout:
        timeout = action.wait_for.timeout
    if action.selector:
        page.wait_for_selector(action.selector, timeout=timeout)
    elif action.wait_for and action.wait_for.millis:
        time.sleep(action.wait_for.millis / 1000)
    else:
        raise ExecutionError("wait_for action requires selector or wait_for.millis")


def _do_scrape(page, action: ActionModel) -> List[Any]:
    elements = page.query_selector_all(action.selector)
    results: List[Any] = []
    for element in elements:
        extract = action.extract
        if extract.type == "text":
            results.append(element.inner_text().strip())
        elif extract.type == "html":
            results.append(element.inner_html())
        elif extract.type == "attr" and extract.attr:
            results.append(element.get_attribute(extract.attr))
    return results


def _do_evaluate(page, action: ActionModel) -> Any:
    if not action.value:
        raise ExecutionError("evaluate action requires 'value' containing JavaScript code")
    return page.evaluate(action.value)


def _do_screenshot(page, action: ActionModel, plan_id: str) -> str:
    _ensure_artifacts_dir()
    path = action.value or str(ARTIFACTS_DIR / f"{plan_id}_{action.id}.png")
    page.screenshot(path=path, full_page=True)
    return path


def _do_select(page, action: ActionModel) -> Any:
    return page.select_option(action.selector, action.value)


def _do_scroll(page, action: ActionModel) -> None:
    if action.value:
        try:
            coords = json.loads(action.value) if action.value.strip().startswith("{") else None
        except json.JSONDecodeError:
            coords = None
        if isinstance(coords, dict):
            x = coords.get("x", 0)
            y = coords.get("y", 0)
            page.evaluate("window.scrollBy(arguments[0], arguments[1])", x, y)
            return
        if action.value.lower() == "bottom" or action.value.lower() == "to=bottom":
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            return
    page.evaluate("window.scrollBy(0, 400)")


def _do_navigation(page, action: ActionModel) -> None:
    if action.type == "back":
        page.go_back()
    elif action.type == "forward":
        page.go_forward()


def _do_cookies(context, action: ActionModel) -> None:
    if action.type == "clear_cookies":
        context.clear_cookies()
        return
    if action.type == "set_cookie":
        if not action.value:
            raise ExecutionError("set_cookie requires 'value' in 'name=value' format")
        parts = action.value.split("=", 1)
        if len(parts) != 2:
            raise ExecutionError("Invalid cookie format; expected 'name=value'")
        name, value = parts
        domain = action.selector or ""
        context.add_cookies(
            [
                {
                    "name": name.strip(),
                    "value": value.strip(),
                    "domain": domain or None,
                    "path": "/",
                }
            ]
        )


def _do_download(page, action: ActionModel) -> str:
    if not action.selector:
        raise ExecutionError("download action requires a selector")
    with page.expect_download() as download_info:
        page.click(action.selector)
    download = download_info.value
    _ensure_artifacts_dir()
    target_path = ARTIFACTS_DIR / download.suggested_filename
    download.save_as(target_path)
    return str(target_path)


def _do_pause(action: ActionModel) -> None:
    if action.wait_for and action.wait_for.millis:
        time.sleep(action.wait_for.millis / 1000)
    elif action.value:
        try:
            millis = int(action.value)
        except ValueError as exc:
            raise ExecutionError("pause action requires numeric milliseconds") from exc
        time.sleep(millis / 1000)
    else:
        raise ExecutionError("pause action requires wait_for.millis or numeric value")


def _apply_store(results: Dict[str, Any], action: ActionModel, value: Any) -> None:
    if not action.store_as:
        return
    if action.store_as in results:
        existing = results[action.store_as]
        if isinstance(existing, list):
            if isinstance(value, list):
                existing.extend(value)
            else:
                existing.append(value)
        else:
            results[action.store_as] = [existing, value]
    else:
        results[action.store_as] = value


def execute_plan(
    plan: PlanModel,
    *,
    headless: bool = True,
    record_screenshots: bool = False,
) -> Dict[str, Any]:
    """Execute a validated plan using Playwright."""
    logs: List[str] = []
    errors: List[str] = []
    results: Dict[str, Any] = {}

    try:
        if sys.platform.startswith("win"):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            asyncio.set_event_loop(asyncio.new_event_loop())
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=headless)
            context = browser.new_context()
            page = context.new_page()

            for action in plan.actions:
                attempts = (action.retry.count + 1) if action.retry else 1
                for attempt in range(1, attempts + 1):
                    try:
                        LOGGER.info("Running action %s (%s)", action.id, action.type)
                        value = _run_action(action, page, context, plan, record_screenshots)
                        _apply_store(results, action, value)
                        logs.append(f"{action.id}: {action.description}")
                        _wait_after_action(action, page)
                        break
                    except (PlaywrightTimeoutError, PlaywrightError, ExecutionError) as exc:
                        message = f"Action {action.id} failed on attempt {attempt}: {exc}"
                        LOGGER.error(message)
                        if attempt == attempts:
                            errors.append(message)
                            raise
                        delay = (action.retry.delay if action.retry else 1000) / 1000
                        time.sleep(delay)
            browser.close()
        return {"success": True, "results": results, "logs": logs, "errors": errors}
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Plan execution failed: %s", exc)
        errors.append(str(exc))
        return {"success": False, "results": results, "logs": logs, "errors": errors}


def _run_action(action: ActionModel, page, context, plan: PlanModel, record_screenshots: bool) -> Optional[Any]:
    if action.type == "goto":
        _do_goto(page, action)
    elif action.type == "click":
        _do_click(page, action)
    elif action.type == "fill":
        _do_fill(page, action)
    elif action.type == "press":
        _do_press(page, action)
    elif action.type == "wait_for":
        _do_wait_for(page, action)
    elif action.type == "scrape":
        return _do_scrape(page, action)
    elif action.type == "evaluate":
        return _do_evaluate(page, action)
    elif action.type == "screenshot":
        if not record_screenshots and not action.value:
            return None
        return _do_screenshot(page, action, plan.id)
    elif action.type == "select":
        return _do_select(page, action)
    elif action.type == "scroll":
        _do_scroll(page, action)
    elif action.type in {"back", "forward"}:
        _do_navigation(page, action)
    elif action.type in {"set_cookie", "clear_cookies"}:
        _do_cookies(context, action)
    elif action.type == "download":
        return _do_download(page, action)
    elif action.type == "pause":
        _do_pause(action)
    else:
        raise ExecutionError(f"Unsupported action type: {action.type}")
    return None
