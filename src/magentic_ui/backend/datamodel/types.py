from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class MessageConfig(BaseModel):
    source: str
    content: str | None
    message_type: str | None = "text"


class MessageMeta(BaseModel):
    task: str | None = None
    summary_method: str | None = "last"
    files: list[dict[str, Any]] | None = None
    time: datetime | None = None
    log: list[dict[str, Any]] | None = None
    usage: list[dict[str, Any]] | None = None


class EnvironmentVariable(BaseModel):
    name: str
    value: str
    type: Literal["string", "number", "boolean", "secret"] = "string"
    description: str | None = None
    required: bool = False


class UISettings(BaseModel):
    show_llm_call_events: bool = False
    expanded_messages_by_default: bool = True
    show_agent_flow_by_default: bool = True


# web request/response data models


class Response(BaseModel):
    message: str
    status: bool
    data: Any | None = None


class SocketMessage(BaseModel):
    connection_id: str
    data: dict[str, Any]
    type: str
