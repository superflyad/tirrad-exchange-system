"""Strict benchmark result contracts and regression comparison logic."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class BenchmarkScenario:
    """Measured performance for one benchmark scenario."""

    name: str
    operation_count: int
    elapsed_ms: float
    ops_per_sec: float
    notes: str | None = None
    config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": self.name,
            "operation_count": self.operation_count,
            "elapsed_ms": self.elapsed_ms,
            "ops_per_sec": self.ops_per_sec,
            "config": dict(self.config),
        }
        if self.notes is not None:
            payload["notes"] = self.notes
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "BenchmarkScenario":
        return cls(
            name=str(payload["name"]),
            operation_count=_require_int(payload["operation_count"], "operation_count"),
            elapsed_ms=float(payload["elapsed_ms"]),
            ops_per_sec=float(payload["ops_per_sec"]),
            notes=str(payload["notes"]) if payload.get("notes") is not None else None,
            config=dict(payload.get("config", {})),
        )


@dataclass(frozen=True)
class BenchmarkRun:
    """Structured benchmark output persisted by TES."""

    benchmark_id: str
    created_at: datetime
    git_sha: str | None
    machine: dict[str, Any]
    scenarios: list[BenchmarkScenario]
    notes: str | None = None
    config: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        scenarios: list[BenchmarkScenario],
        git_sha: str | None,
        machine: dict[str, Any],
        notes: str | None = None,
        config: dict[str, Any] | None = None,
        benchmark_id: str | None = None,
        created_at: datetime | None = None,
    ) -> "BenchmarkRun":
        return cls(
            benchmark_id=benchmark_id or uuid4().hex,
            created_at=created_at or datetime.now(UTC),
            git_sha=git_sha,
            machine=dict(machine),
            scenarios=list(scenarios),
            notes=notes,
            config=dict(config or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "benchmark_id": self.benchmark_id,
            "created_at": self.created_at.isoformat(),
            "git_sha": self.git_sha,
            "machine": dict(self.machine),
            "scenarios": [scenario.to_dict() for scenario in self.scenarios],
            "config": dict(self.config),
        }
        if self.notes is not None:
            payload["notes"] = self.notes
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "BenchmarkRun":
        return cls(
            benchmark_id=str(payload["benchmark_id"]),
            created_at=_parse_datetime(str(payload["created_at"])),
            git_sha=str(payload["git_sha"]) if payload.get("git_sha") is not None else None,
            machine=dict(payload.get("machine", {})),
            scenarios=[BenchmarkScenario.from_dict(item) for item in payload.get("scenarios", [])],
            notes=str(payload["notes"]) if payload.get("notes") is not None else None,
            config=dict(payload.get("config", {})),
        )


@dataclass(frozen=True)
class ScenarioComparison:
    """Scenario-level benchmark comparison."""

    name: str
    baseline_ops_per_sec: float | None
    candidate_ops_per_sec: float | None
    percent_delta: float | None
    regression: bool
    improvement: bool
    threshold_percent: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "baseline_ops_per_sec": self.baseline_ops_per_sec,
            "candidate_ops_per_sec": self.candidate_ops_per_sec,
            "percent_delta": self.percent_delta,
            "regression": self.regression,
            "improvement": self.improvement,
            "threshold_percent": self.threshold_percent,
        }


@dataclass(frozen=True)
class BenchmarkComparison:
    """Benchmark run comparison with regression signals."""

    baseline_id: str
    candidate_id: str
    threshold_percent: float
    has_regression: bool
    scenarios: list[ScenarioComparison]

    def to_dict(self) -> dict[str, Any]:
        return {
            "baseline_id": self.baseline_id,
            "candidate_id": self.candidate_id,
            "threshold_percent": self.threshold_percent,
            "has_regression": self.has_regression,
            "scenarios": [scenario.to_dict() for scenario in self.scenarios],
        }


def compare_benchmark_runs(
    baseline: BenchmarkRun, candidate: BenchmarkRun, *, threshold_percent: float = 10.0
) -> BenchmarkComparison:
    """Compare candidate ops/sec against baseline and flag threshold breaches."""

    baseline_by_name = {scenario.name: scenario for scenario in baseline.scenarios}
    candidate_by_name = {scenario.name: scenario for scenario in candidate.scenarios}
    names = sorted(baseline_by_name.keys() | candidate_by_name.keys())
    comparisons: list[ScenarioComparison] = []
    for name in names:
        baseline_scenario = baseline_by_name.get(name)
        candidate_scenario = candidate_by_name.get(name)
        baseline_ops = baseline_scenario.ops_per_sec if baseline_scenario is not None else None
        candidate_ops = candidate_scenario.ops_per_sec if candidate_scenario is not None else None
        percent_delta: float | None = None
        if baseline_ops is not None and candidate_ops is not None and baseline_ops > 0.0:
            percent_delta = ((candidate_ops - baseline_ops) / baseline_ops) * 100.0
        regression = percent_delta is not None and percent_delta < -abs(threshold_percent)
        improvement = percent_delta is not None and percent_delta > abs(threshold_percent)
        comparisons.append(
            ScenarioComparison(
                name=name,
                baseline_ops_per_sec=baseline_ops,
                candidate_ops_per_sec=candidate_ops,
                percent_delta=percent_delta,
                regression=regression,
                improvement=improvement,
                threshold_percent=threshold_percent,
            )
        )
    return BenchmarkComparison(
        baseline_id=baseline.benchmark_id,
        candidate_id=candidate.benchmark_id,
        threshold_percent=threshold_percent,
        has_regression=any(item.regression for item in comparisons),
        scenarios=comparisons,
    )


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _require_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer")
    return value
