from pydantic import BaseModel, Field
from typing import List, Optional
from enum import StrEnum
from uuid import uuid4
from datetime import datetime, timezone


def _utc_now():
    return datetime.now(timezone.utc)


class Streams(StrEnum):
    EVENTS = "honeypot:events"
    CLASSIFIED = "honeypot:classified"
    SANDBOX = "honeypot:sandbox"
    TELEMETRY = "honeypot:telemetry"
    RECOMMENDATIONS = "honeypot:recommendations"


class BaseEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    correlation_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: str
    schema_version: str = "1.0"


class SessionEvent(BaseEvent):
    source: str
    timestamp: datetime = Field(default_factory=_utc_now)
    session: dict


class ClassificationResult(BaseModel):
    session_id: str
    classification: str  # "benign", "malicious", "mixed"
    tactics: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    model_version: str = "v1.0"
    model_name: str = "unknown"


class ClassifiedEvent(BaseEvent):
    session_id: str
    classification: ClassificationResult
    classified_at: datetime = Field(default_factory=_utc_now)


class RiskDecision(BaseModel):
    session_id: str
    risk_score: float
    sandbox_required: bool
    reason: List[str] = Field(default_factory=list)
    observe_commands: List[str] = Field(default_factory=list)
    commands_to_sandbox: List[str] = Field(default_factory=list)
    ignored_commands: List[str] = Field(default_factory=list)


class RiskDecisionEvent(BaseEvent):
    session_id: str
    decision: RiskDecision
    decided_at: datetime = Field(default_factory=_utc_now)


class CommandResult(BaseModel):
    command: str
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = 0
    network_indicators: List[str] = Field(default_factory=list)


class SandboxResult(BaseModel):
    session_id: str
    exit_code: int

    sandbox_level: str = "isolated"

    commands_executed: List[str] = Field(default_factory=list)
    command_results: List[CommandResult] = Field(default_factory=list)

    files_created: List[str] = Field(default_factory=list)
    files_modified: List[str] = Field(default_factory=list)
    files_deleted: List[str] = Field(default_factory=list)

    network_connections: List[str] = Field(default_factory=list)
    syscalls: List[str] = Field(default_factory=list)

    stdout: str = ""
    stderr: str = ""


class SandboxResultEvent(BaseEvent):
    session_id: str
    result: SandboxResult
    executed_at: datetime = Field(default_factory=_utc_now)