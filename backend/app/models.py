from __future__ import annotations

from typing import Any, List, Literal, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

ALLOWED_ACTION_TYPES: List[str] = [
    "goto",
    "click",
    "fill",
    "press",
    "wait_for",
    "scrape",
    "evaluate",
    "screenshot",
    "select",
    "scroll",
    "back",
    "forward",
    "set_cookie",
    "clear_cookies",
    "download",
    "pause",
]

ActionType = Literal[
    "goto",
    "click",
    "fill",
    "press",
    "wait_for",
    "scrape",
    "evaluate",
    "screenshot",
    "select",
    "scroll",
    "back",
    "forward",
    "set_cookie",
    "clear_cookies",
    "download",
    "pause",
]


class RetrySpec(BaseModel):
    count: int = Field(ge=0, le=5, default=0)
    delay: int = Field(ge=0, default=1000)


class WaitForSpec(BaseModel):
    selector: Optional[str] = None
    timeout: int = Field(default=10000, ge=100)
    millis: Optional[int] = Field(default=None, ge=100)

    @model_validator(mode="after")
    def validate_selector_or_time(cls, values: "WaitForSpec") -> "WaitForSpec":
        if not values.selector and values.millis is None:
            raise ValueError("wait_for requires either selector or millis")
        return values


class ExtractSpec(BaseModel):
    type: Literal["text", "html", "attr"]
    attr: Optional[str] = None

    @model_validator(mode="after")
    def validate_attr(cls, values: "ExtractSpec") -> "ExtractSpec":
        if values.type == "attr" and not values.attr:
            raise ValueError("extract.attr is required when type is 'attr'")
        return values


class OutputSpec(BaseModel):
    type: Literal["json", "csv"] = "json"
    max_results: int = Field(default=10, ge=1, le=100)


class ActionModel(BaseModel):
    id: str = Field(min_length=1)
    type: ActionType
    description: str = Field(min_length=1)
    selector: Optional[str] = None
    url: Optional[str] = None
    value: Optional[str] = None
    extract: Optional[ExtractSpec] = None
    wait_for: Optional[WaitForSpec] = Field(default=None)
    retry: Optional[RetrySpec] = Field(default=None)
    store_as: Optional[str] = Field(default=None, min_length=1)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_action(cls, values: "ActionModel") -> "ActionModel":
        action_type = values.type
        selector = values.selector
        url = values.url
        value = values.value

        if action_type == "goto" and not url:
            raise ValueError("goto action requires 'url'")
        if action_type in {"click", "fill", "scrape", "select", "download"} and not selector:
            raise ValueError(f"{action_type} action requires 'selector'")
        if action_type == "fill" and value is None:
            raise ValueError("fill action requires 'value'")
        if action_type == "select" and value is None:
            raise ValueError("select action requires 'value'")
        if action_type == "scrape" and values.extract is None:
            raise ValueError("scrape action requires 'extract'")
        if action_type == "press" and not value:
            raise ValueError("press action requires 'value' for key press")
        if action_type == "pause" and (values.wait_for is None or values.wait_for.millis is None):
            raise ValueError("pause action requires wait_for.millis")
        return values


class PlanModel(BaseModel):
    id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    actions: List[ActionModel] = Field(min_length=1, max_length=20)
    output: OutputSpec = Field(default_factory=OutputSpec)

    model_config = ConfigDict(extra="forbid")

    @field_validator("actions")
    @classmethod
    def validate_action_ids(cls, actions: List[ActionModel]) -> List[ActionModel]:
        seen = set()
        for action in actions:
            if action.id in seen:
                raise ValueError(f"duplicate action id: {action.id}")
            seen.add(action.id)
        return actions


class PlanEnvelope(BaseModel):
    plan: PlanModel

    model_config = ConfigDict(extra="forbid")


def validate_plan(data: Any) -> PlanEnvelope:
    """Validate an arbitrary JSON-like structure, returning a PlanEnvelope."""
    if isinstance(data, PlanEnvelope):
        return data
    try:
        return PlanEnvelope.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"Invalid plan: {exc}") from exc
