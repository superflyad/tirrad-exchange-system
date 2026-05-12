"""Pydantic request and response models for the TES API service."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictFloat, StrictInt, StrictStr, field_validator

RunType = Literal["session", "backtest", "benchmark"]
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
    priority: StrictInt = 0
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
    priority: StrictInt = 0
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


class BenchmarkRunRequest(StrictApiModel):
    mode: ExecutionMode | None = None
    priority: StrictInt = 10
    threshold_percent: StrictFloat = Field(default=10.0, ge=0.0)
    persist: StrictBool = True


class BenchmarkScenarioModel(StrictApiModel):
    name: str
    operation_count: StrictInt
    elapsed_ms: StrictFloat
    ops_per_sec: StrictFloat
    notes: str | None = None
    config: dict[str, Any]


class BenchmarkRunModel(StrictApiModel):
    benchmark_id: str
    created_at: datetime
    git_sha: str | None
    machine: dict[str, Any]
    scenarios: list[BenchmarkScenarioModel]
    notes: str | None = None
    config: dict[str, Any]


class BenchmarkCompareRequest(StrictApiModel):
    baseline_id: StrictStr | None = None
    candidate_id: StrictStr | None = None
    threshold_percent: StrictFloat = Field(default=10.0, ge=0.0)


class BenchmarkScenarioComparisonModel(StrictApiModel):
    name: str
    baseline_ops_per_sec: StrictFloat | None
    candidate_ops_per_sec: StrictFloat | None
    percent_delta: StrictFloat | None
    regression: StrictBool
    improvement: StrictBool
    threshold_percent: StrictFloat


class BenchmarkComparisonModel(StrictApiModel):
    baseline_id: str
    candidate_id: str
    threshold_percent: StrictFloat
    has_regression: StrictBool
    scenarios: list[BenchmarkScenarioComparisonModel]


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
    priority: StrictInt = 5
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
    scenario: str | None = None
    strategy: str | None = None
    step_count: StrictInt = 0
    trade_count: StrictInt = 0
    rejection_count: StrictInt = 0
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




class ReplayFrame(StrictApiModel):
    step: StrictInt
    timestamp: Any | None
    symbols: list[str]
    symbol: str | None
    trades: list[dict[str, Any]]
    snapshots: list[dict[str, Any]]
    top_of_book: dict[str, Any]
    account_deltas: list[dict[str, Any]]
    accounts: list[dict[str, Any]]
    market_metrics: dict[str, Any]
    event_summaries: list[dict[str, Any]]


class ReplayCursorModel(StrictApiModel):
    step: StrictInt
    state: Literal["playing", "paused"]
    speed: StrictFloat


class ReplayTimelineModel(StrictApiModel):
    start_step: StrictInt
    end_step: StrictInt
    steps: list[StrictInt]
    total_frames: StrictInt
    event_steps: list[StrictInt]
    symbols: list[str]


class ReplaySessionResponse(StrictApiModel):
    run_id: str
    event_count: StrictInt
    events: list[dict[str, Any]]
    cursor: ReplayCursorModel
    timeline: ReplayTimelineModel
    frame: ReplayFrame | None


class ReplayRangeResponse(StrictApiModel):
    run_id: str
    start_step: StrictInt
    end_step: StrictInt
    frames: list[ReplayFrame]
    next_start_step: StrictInt | None
    total_frames: StrictInt


class ReplaySummaryResponse(StrictApiModel):
    run_id: str
    symbols: list[str]
    total_steps: StrictInt
    total_frames: StrictInt
    total_events: StrictInt
    total_trades: StrictInt
    total_snapshots: StrictInt
    total_accounts: StrictInt
    start_step: StrictInt
    end_step: StrictInt
    first_divergence_step: StrictInt | None
    available_event_types: list[str]
    performance_notes: list[str]


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
    hostname: str = "unknown"
    process_id: int | None = None
    started_at: datetime | None = None
    heartbeat_at: datetime | None = None
    updated_at: datetime
    capabilities: dict[str, Any] = Field(default_factory=dict)
    status: str
    current_run_id: str | None
    progress_summary: dict[str, Any] = Field(default_factory=dict)
    cpu_percent: float | None = None
    memory_bytes: int | None = None
    drain_requested: bool = False
    shutdown_requested: bool = False

    @classmethod
    def from_record(cls, record: Any) -> "WorkerSummary":
        heartbeat_at = getattr(record, "heartbeat_at")
        return cls(
            worker_id=getattr(record, "worker_id"),
            hostname=getattr(record, "hostname", "unknown"),
            process_id=getattr(record, "process_id", None),
            started_at=getattr(record, "started_at", None),
            heartbeat_at=heartbeat_at,
            updated_at=heartbeat_at,
            capabilities=getattr(record, "capabilities", {}),
            status=getattr(record, "status"),
            current_run_id=getattr(record, "current_run_id", None),
            progress_summary=getattr(record, "progress_summary", {}),
            cpu_percent=getattr(record, "cpu_percent", None),
            memory_bytes=getattr(record, "memory_bytes", None),
            drain_requested=getattr(record, "drain_requested", False),
            shutdown_requested=getattr(record, "shutdown_requested", False),
        )


class SchedulerStatusResponse(StrictApiModel):
    pending_count: StrictInt
    running_count: StrictInt
    completed_count: StrictInt
    failed_count: StrictInt
    stale_worker_count: StrictInt
    stale_job_count: StrictInt
    queue_depth: StrictInt
    average_wait_seconds: StrictFloat
    average_run_seconds: StrictFloat
    worker_utilization: StrictFloat
    throughput_per_minute: StrictFloat


class RequeueStaleResponse(StrictApiModel):
    stale_workers: StrictInt
    requeued_runs: list[str]


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
