"""Pydantic request and response models for the TES API service."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictFloat, StrictInt, StrictStr, field_validator

RunType = Literal["session", "backtest"]
TournamentType = Literal["strategy_vs_strategy", "strategy_vs_scenario", "parameter_sweep", "multi_symbol_sweep"]
ExecutionMode = Literal["sync", "queued"]
RunStatus = Literal["pending", "running", "completed", "failed", "canceled"]
TimelineCategory = Literal["command", "event", "snapshot", "account", "log"]
StreamCategory = Literal["status", "progress", "event", "snapshot", "account", "log", "error", "completed"]
ReplayStatus = Literal["replayed", "reconstructed", "unavailable", "mismatch"]


class StrictApiModel(BaseModel):
    """Base model that rejects ambiguous or unexpected API fields."""

    model_config = ConfigDict(extra="forbid")


class SessionRunRequest(StrictApiModel):
    mode: ExecutionMode | None = None
    scenario: StrictStr = "calm_market"
    steps: StrictInt = Field(default=25, gt=0)
    symbols: list[StrictStr] = Field(default_factory=lambda: ["DEFAULT"])
    seed: StrictInt = 42
    initial_price: StrictInt = Field(default=100, gt=0)
    volatility: StrictFloat = Field(default=0.02, ge=0.0)
    participants: StrictInt = Field(default=20, gt=0)
    depth_levels: StrictInt = Field(default=5, ge=0)
    initial_cash: StrictInt = Field(default=1_000_000, ge=0)
    progress_interval: StrictInt = Field(default=10, gt=0)
    stream_events: StrictBool = False
    stream_snapshots: StrictBool = False

    @field_validator("symbols")
    @classmethod
    def _validate_symbols(cls, value: list[str]) -> list[str]:
        symbols = [symbol.strip() for symbol in value]
        if not symbols or any(symbol == "" for symbol in symbols):
            raise ValueError("symbols must contain at least one non-empty symbol")
        return symbols


class BacktestRunRequest(StrictApiModel):
    mode: ExecutionMode | None = None
    strategy: StrictStr
    symbols: list[StrictStr] = Field(default_factory=lambda: ["DEFAULT"])
    initial_cash: StrictInt = Field(default=1_000_000, ge=0)
    depth_levels: StrictInt = Field(default=5, ge=0)
    progress_interval: StrictInt = Field(default=10, gt=0)
    stream_events: StrictBool = False
    stream_snapshots: StrictBool = False

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


class ParameterSweepConfig(StrictApiModel):
    strategy: StrictStr
    parameters: dict[StrictStr, list[StrictInt | StrictFloat | StrictStr | StrictBool]] = Field(default_factory=dict)

    @field_validator("strategy")
    @classmethod
    def _validate_strategy(cls, value: str) -> str:
        strategy = value.strip()
        if strategy == "":
            raise ValueError("strategy must be a non-empty string")
        return strategy

    @field_validator("parameters")
    @classmethod
    def _validate_parameters(
        cls, value: dict[str, list[int | float | str | bool]]
    ) -> dict[str, list[int | float | str | bool]]:
        for key, values in value.items():
            if key.strip() == "":
                raise ValueError("parameter names must be non-empty strings")
            if not values:
                raise ValueError("parameter value lists must be non-empty")
        return value


class TournamentConfig(StrictApiModel):
    mode: ExecutionMode | None = None
    tournament_type: TournamentType
    strategies: list[StrictStr] = Field(default_factory=list)
    scenarios: list[StrictStr] = Field(default_factory=lambda: ["calm_market"])
    symbols: list[StrictStr] = Field(default_factory=lambda: ["DEFAULT"])
    seeds: list[StrictInt] = Field(default_factory=lambda: [42])
    steps: StrictInt = Field(default=25, gt=0)
    initial_cash: StrictInt = Field(default=1_000_000, ge=0)
    participant_counts: list[StrictInt] = Field(default_factory=lambda: [20])
    volatility_ranges: list[StrictFloat] = Field(default_factory=lambda: [0.02])
    strategy_parameters: dict[StrictStr, list[StrictInt | StrictFloat | StrictStr | StrictBool]] = Field(default_factory=dict)
    parameter_sweep: ParameterSweepConfig | None = None

    @field_validator("strategies", "scenarios", "symbols")
    @classmethod
    def _validate_string_list(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value]
        if any(item == "" for item in normalized):
            raise ValueError("string lists cannot contain empty values")
        return normalized

    @field_validator("seeds")
    @classmethod
    def _validate_seeds(cls, value: list[int]) -> list[int]:
        if not value:
            raise ValueError("seeds must contain at least one seed")
        return value

    @field_validator("participant_counts")
    @classmethod
    def _validate_participants(cls, value: list[int]) -> list[int]:
        if not value or any(item <= 0 for item in value):
            raise ValueError("participant_counts must contain positive integers")
        return value

    @field_validator("volatility_ranges")
    @classmethod
    def _validate_volatility(cls, value: list[float]) -> list[float]:
        if not value or any(item < 0.0 for item in value):
            raise ValueError("volatility_ranges must contain non-negative floats")
        return value


class TournamentRun(StrictApiModel):
    tournament_id: str
    status: RunStatus
    tournament_type: TournamentType
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    config: dict[str, Any]
    child_count: StrictInt
    completed_child_count: StrictInt
    failed_child_count: StrictInt
    error: str | None = None


class TournamentResult(StrictApiModel):
    rank: StrictInt
    child_run_id: str
    child_key: str
    status: RunStatus
    dimensions: dict[str, Any]
    metrics: dict[str, Any]
    score: StrictFloat
    error: str | None = None


class TournamentReport(StrictApiModel):
    tournament_id: str
    status: RunStatus
    generated_at: datetime
    child_count: StrictInt
    completed_child_count: StrictInt
    failed_child_count: StrictInt
    results: list[TournamentResult]
    failures: list[TournamentResult]


class TournamentChildrenResponse(StrictApiModel):
    tournament_id: str
    children: list[dict[str, Any]]


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
    polling_url: str | None = None
    stream_url: str | None = None


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


class TimelineEntry(StrictApiModel):
    step: int | None
    timestamp: Any | None
    sequence: int
    symbol: str | None
    category: TimelineCategory
    type: str
    summary: str
    payload: dict[str, Any]


class RunTimelineResponse(StrictApiModel):
    run_id: str
    timeline: list[TimelineEntry]


class RunReplayResponse(StrictApiModel):
    run_id: str
    status: ReplayStatus
    message: str
    total_events: int
    total_snapshots: int
    total_accounts: int
    total_logs: int
    event_count_matches: bool | None
    event_hash_matches: bool | None


class RunInspectionSummary(StrictApiModel):
    run_id: str
    run_type: RunType
    status: RunStatus
    symbols: list[str]
    total_steps: int
    total_orders: int
    total_events: int
    total_trades: int
    total_snapshots: int
    total_rejections: int
    total_volume: int
    traded_notional: int
    final_prices: dict[str, Any]
    final_positions: dict[str, Any]
    error: str | None


class StreamMessage(StrictApiModel):
    run_id: str
    timestamp: datetime
    step: int | None = None
    category: StreamCategory
    type: str
    payload: dict[str, Any]


class ErrorPayload(StrictApiModel):
    code: str
    message: str
    details: Any | None = None


class ErrorResponse(StrictApiModel):
    error: ErrorPayload


class WorkerSummary(StrictApiModel):
    worker_id: str
    status: str
    updated_at: datetime
    current_run_id: str | None


ReplayVerificationStatus = Literal["verified", "mismatch", "partial", "failed"]
RunDiffStatus = Literal["matching", "mismatch", "partial", "failed"]


class EventHashSummaryModel(StrictApiModel):
    event_hash: str
    snapshot_hash: str
    account_hash: str
    report_hash: str
    combined_hash: str
    event_count: StrictInt
    snapshot_count: StrictInt
    account_count: StrictInt
    trade_count: StrictInt
    sequence_count: StrictInt
    sequence_hash: str


class ReplayVerificationReportModel(StrictApiModel):
    run_id: str
    status: ReplayVerificationStatus
    verified_at: str
    matching_fields: list[str]
    mismatched_fields: list[str]
    message: str
    original_hashes: EventHashSummaryModel
    replay_hashes: EventHashSummaryModel | None
    first_divergence_step: int | None
    metric_deltas: dict[str, float]
    comparisons: dict[str, bool]
    error: str | None = None


class RunDiffRequest(StrictApiModel):
    left_run_id: StrictStr
    right_run_id: StrictStr


class RunDiffResultModel(StrictApiModel):
    left_run_id: str
    right_run_id: str
    status: RunDiffStatus
    generated_at: str
    matching_fields: list[str]
    mismatched_fields: list[str]
    first_divergence_step: int | None
    metric_deltas: dict[str, float]
    event_hash_comparison: dict[str, Any]
    snapshot_hash_comparison: dict[str, Any]
    account_hash_comparison: dict[str, Any]
    report_hash_comparison: dict[str, Any]
    timeline_divergence: dict[str, Any]
    pnl_divergence: dict[str, Any]
    sequence_divergence: dict[str, Any]
    left_hashes: EventHashSummaryModel
    right_hashes: EventHashSummaryModel
