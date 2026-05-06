"""Pydantic request and response models for the TES API service."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt, StrictStr, field_validator

RunType = Literal["session", "backtest"]
RunStatus = Literal["pending", "running", "completed", "failed", "canceled"]


class StrictApiModel(BaseModel):
    """Base model that rejects ambiguous or unexpected API fields."""

    model_config = ConfigDict(extra="forbid")


class SessionRunRequest(StrictApiModel):
    scenario: StrictStr = "calm_market"
    steps: StrictInt = Field(default=25, gt=0)
    symbols: list[StrictStr] = Field(default_factory=lambda: ["DEFAULT"])
    seed: StrictInt = 42
    initial_price: StrictInt = Field(default=100, gt=0)
    volatility: StrictFloat = Field(default=0.02, ge=0.0)
    participants: StrictInt = Field(default=20, gt=0)
    depth_levels: StrictInt = Field(default=5, ge=0)
    initial_cash: StrictInt = Field(default=1_000_000, ge=0)

    @field_validator("symbols")
    @classmethod
    def _validate_symbols(cls, value: list[str]) -> list[str]:
        symbols = [symbol.strip() for symbol in value]
        if not symbols or any(symbol == "" for symbol in symbols):
            raise ValueError("symbols must contain at least one non-empty symbol")
        return symbols


class BacktestRunRequest(StrictApiModel):
    strategy: StrictStr
    symbols: list[StrictStr] = Field(default_factory=lambda: ["DEFAULT"])
    initial_cash: StrictInt = Field(default=1_000_000, ge=0)
    depth_levels: StrictInt = Field(default=5, ge=0)

    @field_validator("strategy")
    @classmethod
    def _validate_strategy(cls, value: str) -> str:
        strategy = value.strip()
        if strategy == "":
            raise ValueError("strategy must be a non-empty string")
        return strategy

    @field_validator("symbols")
    @classmethod
    def _validate_symbols(cls, value: list[str]) -> list[str]:
        symbols = [symbol.strip() for symbol in value]
        if not symbols or any(symbol == "" for symbol in symbols):
            raise ValueError("symbols must contain at least one non-empty symbol")
        return symbols


class RunSummary(StrictApiModel):
    run_id: str
    run_type: RunType
    status: RunStatus
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    config: dict[str, Any]
    report_summary: dict[str, Any]
    error: str | None


class RunDetail(RunSummary):
    report: dict[str, Any]


class RunReportResponse(StrictApiModel):
    run_id: str
    report: dict[str, Any]


class RunEventsResponse(StrictApiModel):
    run_id: str
    events: list[dict[str, Any]]


class RunSnapshotsResponse(StrictApiModel):
    run_id: str
    snapshots: list[dict[str, Any]]


class RunAccountsResponse(StrictApiModel):
    run_id: str
    accounts: list[dict[str, Any]]


class RunLogsResponse(StrictApiModel):
    run_id: str
    logs: list[dict[str, Any]]


class ErrorPayload(StrictApiModel):
    code: str
    message: str
    details: Any | None = None


class ErrorResponse(StrictApiModel):
    error: ErrorPayload
