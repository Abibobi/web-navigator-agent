# Plan JSON Schema

This document describes the JSON structure expected by the Web Navigator AI Agent planner and executor. Every plan **must** conform to this schema before execution. The planner is responsible for generating the plan, and the executor validates it with Pydantic models defined in `backend/app/models.py`.

## Top-Level Envelope

```json
{
  "plan": {
    "id": "plan_123",
    "description": "Short human-readable summary",
    "actions": [ /* array of action objects, maximum 20 */ ],
    "output": {
      "type": "json",
      "max_results": 10
    }
  }
}
```

- `id`: Unique identifier for the plan.
- `description`: Short statement describing the overall intent.
- `actions`: Ordered list of action objects executed sequentially (max 20).
- `output`: Controls how results should be packaged for the caller.

## Action Object

Each action entry must follow the structure below:

```json
{
  "id": "a1",
  "type": "goto",
  "description": "Navigate to Google",
  "selector": "optional CSS or XPath selector",
  "url": "https://example.com",
  "value": "text value or key press",
  "extract": { "type": "text", "attr": "href" },
  "wait_for": { "selector": "#results", "timeout": 10000, "millis": 500 },
  "retry": { "count": 2, "delay": 1000 },
  "store_as": "results"
}
```

### Required fields

- `id`: Unique within the plan.
- `type`: One of the allowed action types:
  - `goto`, `click`, `fill`, `press`, `wait_for`, `scrape`, `evaluate`,
    `screenshot`, `select`, `scroll`, `back`, `forward`, `set_cookie`,
    `clear_cookies`, `download`, `pause`.
- `description`: Short human-readable context for the action.

### Conditional fields

- `url`: Required when `type` is `goto`.
- `selector`: Required for `click`, `fill`, `scrape`, `select`, and `download`. Optional for other actions where a selector is meaningful.
- `value`: Required for `fill`, `select`, and `press`; optional for others.
- `extract`: Required for `scrape` actions. Must define `type` (`text`, `html`, or `attr`) and optionally `attr` when `type` is `attr`.
- `wait_for`: Optional automatic wait executed **after** the action, ensuring DOM stability. Accepts either `selector` or `millis` (delay in ms).
- `retry`: Optional retry strategy with `count` (max 5) and `delay` in milliseconds.
- `store_as`: Optional key used to collect action outputs in the executor result payload.

### Special Actions

- `wait_for`: Uses `selector` or `wait_for.millis` to pause until a condition is met.
- `scrape`: Extracts text, HTML, or attribute values from matching nodes. Always specify `store_as` to capture data.
- `evaluate`: Runs arbitrary JavaScript (`value` should contain the JS code). Any return value is captured.
- `pause`: Introduces a delay. Provide `wait_for.millis` or a numeric `value` indicating milliseconds.
- `scroll`: `value` can be `{ "x": 0, "y": 400 }` (JSON) or the string `"bottom"`.

## Example Plan

```json
{
  "plan": {
    "id": "plan_001",
    "description": "Search laptops on Google and scrape top 5 results",
    "actions": [
      {"id":"a1","type":"goto","url":"https://www.google.com","description":"Open Google"},
      {"id":"a2","type":"wait_for","selector":"input[name='q']","description":"Ensure search box is visible"},
      {"id":"a3","type":"fill","selector":"input[name='q']","value":"laptops under 50000","description":"Enter query"},
      {"id":"a4","type":"press","value":"Enter","description":"Submit search","wait_for":{"selector":"#search","timeout":15000}},
      {"id":"a5","type":"scrape","selector":"#search .g","extract":{"type":"text"},"store_as":"results","description":"Capture result blocks"}
    ],
    "output": {"type": "json", "max_results": 5}
  }
}
```

Use this schema as the reference when crafting plans manually (e.g., `backend/test_plan.json`) or when adapting the planner prompts.
