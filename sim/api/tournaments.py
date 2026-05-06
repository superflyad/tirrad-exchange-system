"""Tournament expansion and aggregation utilities for TES API runs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import product
from typing import Any

from sim.api.models import BacktestRunRequest, SessionRunRequest, TournamentConfig


@dataclass(frozen=True)
class ChildRunSpec:
    """Deterministic child run specification generated from a tournament."""

    child_key: str
    run_type: str
    config: dict[str, Any]
    dimensions: dict[str, Any]


def expand_tournament(config: TournamentConfig) -> list[ChildRunSpec]:
    """Expand a tournament config into deterministic child run specs."""

    specs: list[ChildRunSpec]
    if config.tournament_type == "strategy_vs_strategy":
        specs = _strategy_backtests(config, include_parameters=False)
    elif config.tournament_type == "strategy_vs_scenario":
        specs = _scenario_sessions(config)
    elif config.tournament_type == "parameter_sweep":
        specs = _parameter_sweep(config)
    elif config.tournament_type == "multi_symbol_sweep":
        specs = _multi_symbol_sweep(config)
    else:
        raise ValueError(f"unsupported tournament type: {config.tournament_type}")
    return sorted(specs, key=lambda item: item.child_key)


def build_report(tournament_id: str, child_links: list[dict[str, Any]], runs: list[Any]) -> dict[str, Any]:
    """Aggregate child run records into a ranked tournament report."""

    records = {run.run_id: run for run in runs}
    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    completed = 0
    failed = 0
    for link in sorted(child_links, key=lambda item: str(item["child_key"])):
        record = records.get(str(link["child_run_id"]))
        status = record.status if record is not None else "failed"
        error = record.error if record is not None else "missing child run"
        dimensions = dict(link.get("dimensions", {}))
        if status == "completed" and record is not None:
            completed += 1
            metrics = _metrics(record.report, record.config)
            results.append(
                {
                    "rank": 0,
                    "child_run_id": record.run_id,
                    "child_key": str(link["child_key"]),
                    "status": status,
                    "dimensions": dimensions,
                    "metrics": metrics,
                    "score": float(metrics["score"]),
                    "error": None,
                }
            )
        elif status == "failed":
            failed += 1
            failures.append(_failure_result(link, status, error))
        elif status == "canceled":
            failures.append(_failure_result(link, status, error or "canceled"))

    ranked = sorted(
        results,
        key=lambda item: (
            float(item["score"]),
            float(item["metrics"].get("ending_equity", 0.0)),
            str(item["child_key"]),
        ),
        reverse=True,
    )
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index
    for index, item in enumerate(failures, start=len(ranked) + 1):
        item["rank"] = index
    total = len(child_links)
    terminal = completed + failed + sum(1 for item in failures if item["status"] == "canceled")
    status = "completed" if total > 0 and terminal == total else "running"
    if total == 0:
        status = "failed"
    return {
        "tournament_id": tournament_id,
        "status": status,
        "generated_at": datetime.now(UTC).isoformat(),
        "child_count": total,
        "completed_child_count": completed,
        "failed_child_count": failed,
        "results": ranked,
        "failures": failures,
    }


def _strategy_backtests(config: TournamentConfig, *, include_parameters: bool) -> list[ChildRunSpec]:
    strategies = _require(config.strategies, "strategies")
    symbols = _require(config.symbols, "symbols")
    specs: list[ChildRunSpec] = []
    for strategy, seed in product(strategies, config.seeds):
        params = dict(config.strategy_parameters) if include_parameters else {}
        key = _key(strategy=strategy, seed=seed, symbols=symbols, parameters=params)
        run_config = BacktestRunRequest(
            strategy=strategy,
            symbols=symbols,
            initial_cash=config.initial_cash,
        ).model_dump(exclude={"mode"})
        specs.append(
            ChildRunSpec(
                child_key=key,
                run_type="backtest",
                config=run_config,
                dimensions={"strategy": strategy, "seed": seed, "symbols": symbols, "parameters": params},
            )
        )
    return specs


def _scenario_sessions(config: TournamentConfig) -> list[ChildRunSpec]:
    scenarios = _require(config.scenarios, "scenarios")
    symbols = _require(config.symbols, "symbols")
    strategies = config.strategies or ["session_participants"]
    specs: list[ChildRunSpec] = []
    for strategy, scenario, seed, participants, volatility in product(
        strategies, scenarios, config.seeds, config.participant_counts, config.volatility_ranges
    ):
        key = _key(strategy=strategy, scenario=scenario, seed=seed, participants=participants, volatility=volatility)
        run_config = SessionRunRequest(
            scenario=scenario,
            steps=config.steps,
            symbols=symbols,
            seed=seed,
            volatility=volatility,
            participants=participants,
            initial_cash=config.initial_cash,
        ).model_dump(exclude={"mode"})
        specs.append(
            ChildRunSpec(
                child_key=key,
                run_type="session",
                config=run_config,
                dimensions={
                    "strategy": strategy,
                    "scenario": scenario,
                    "seed": seed,
                    "symbols": symbols,
                    "participants": participants,
                    "volatility": volatility,
                },
            )
        )
    return specs


def _parameter_sweep(config: TournamentConfig) -> list[ChildRunSpec]:
    sweep = config.parameter_sweep
    strategy = sweep.strategy if sweep is not None else (_require(config.strategies, "strategies")[0])
    parameters = sweep.parameters if sweep is not None else config.strategy_parameters
    combos = _parameter_combinations(parameters)
    symbols = _require(config.symbols, "symbols")
    specs: list[ChildRunSpec] = []
    for seed, params in product(config.seeds, combos):
        key = _key(strategy=strategy, seed=seed, symbols=symbols, parameters=params)
        run_config = BacktestRunRequest(
            strategy=strategy,
            symbols=symbols,
            initial_cash=config.initial_cash,
        ).model_dump(exclude={"mode"})
        specs.append(
            ChildRunSpec(
                child_key=key,
                run_type="backtest",
                config=run_config,
                dimensions={"strategy": strategy, "seed": seed, "symbols": symbols, "parameters": params},
            )
        )
    return specs


def _multi_symbol_sweep(config: TournamentConfig) -> list[ChildRunSpec]:
    strategies = _require(config.strategies, "strategies")
    symbol_sets = [[symbol] for symbol in _require(config.symbols, "symbols")]
    if len(config.symbols) > 1:
        symbol_sets.append(list(config.symbols))
    specs: list[ChildRunSpec] = []
    for strategy, symbols, seed in product(strategies, symbol_sets, config.seeds):
        key = _key(strategy=strategy, symbols=symbols, seed=seed)
        run_config = BacktestRunRequest(
            strategy=strategy,
            symbols=symbols,
            initial_cash=config.initial_cash,
        ).model_dump(exclude={"mode"})
        specs.append(
            ChildRunSpec(
                child_key=key,
                run_type="backtest",
                config=run_config,
                dimensions={"strategy": strategy, "seed": seed, "symbols": symbols},
            )
        )
    return specs


def _parameter_combinations(parameters: dict[str, list[int | float | str | bool]]) -> list[dict[str, Any]]:
    if not parameters:
        return [{}]
    keys = sorted(parameters)
    return [dict(zip(keys, values, strict=True)) for values in product(*(parameters[key] for key in keys))]


def _metrics(report: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    starting = _number(report.get("starting_equity"), _number(config.get("initial_cash"), 0.0))
    ending = _number(report.get("ending_equity"), _number(report.get("final_equity"), starting))
    total_pnl = _number(report.get("total_pnl"), ending - starting)
    total_volume = _number(report.get("total_volume"), _sum_mapping(report.get("per_symbol_volume")))
    total_orders = _number(report.get("total_orders"), 0.0)
    rejected = _number(report.get("rejected_orders"), _number(report.get("total_rejections"), 0.0))
    fill_ratio = _number(report.get("fill_ratio"), 0.0)
    rejection_rate = rejected / total_orders if total_orders > 0 else 0.0
    exposure = _sum_abs_mapping(report.get("per_symbol_position") or report.get("final_positions"))
    drawdown = _max_drawdown(report.get("equity_curve"))
    stability = _stability(report.get("equity_curve"))
    score = ending + total_pnl + (stability * 1000.0) - drawdown - (rejection_rate * 100.0)
    return {
        "ending_equity": ending,
        "total_pnl": total_pnl,
        "return_stability": stability,
        "max_drawdown": drawdown,
        "total_volume": total_volume,
        "fill_ratio": fill_ratio,
        "rejection_rate": rejection_rate,
        "final_position_exposure": exposure,
        "score": score,
    }


def _failure_result(link: dict[str, Any], status: str, error: str | None) -> dict[str, Any]:
    return {
        "rank": 0,
        "child_run_id": str(link["child_run_id"]),
        "child_key": str(link["child_key"]),
        "status": status,
        "dimensions": dict(link.get("dimensions", {})),
        "metrics": {},
        "score": 0.0,
        "error": error,
    }


def _max_drawdown(curve: Any) -> float:
    if not isinstance(curve, list) or not curve:
        return 0.0
    peak = _number(curve[0], 0.0)
    drawdown = 0.0
    for item in curve:
        value = _number(item, peak)
        peak = max(peak, value)
        drawdown = max(drawdown, peak - value)
    return drawdown


def _stability(curve: Any) -> float:
    if not isinstance(curve, list) or len(curve) < 2:
        return 0.0
    returns: list[float] = []
    for before, after in zip(curve, curve[1:], strict=False):
        base = _number(before, 0.0)
        if base != 0.0:
            returns.append((_number(after, base) - base) / abs(base))
    if not returns:
        return 0.0
    average = sum(returns) / len(returns)
    variance = sum((item - average) ** 2 for item in returns) / len(returns)
    return average / (variance**0.5) if variance > 0.0 else average


def _sum_mapping(value: Any) -> float:
    return sum(_number(item, 0.0) for item in value.values()) if isinstance(value, dict) else 0.0


def _sum_abs_mapping(value: Any) -> float:
    return sum(abs(_number(item, 0.0)) for item in value.values()) if isinstance(value, dict) else 0.0


def _number(value: Any, fallback: float) -> float:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else fallback


def _require(values: list[str], label: str) -> list[str]:
    if not values:
        raise ValueError(f"{label} must contain at least one value")
    return values


def _key(**parts: Any) -> str:
    serialized: list[str] = []
    for key in sorted(parts):
        value = parts[key]
        if isinstance(value, dict):
            rendered = ",".join(f"{item_key}={value[item_key]}" for item_key in sorted(value)) or "none"
        elif isinstance(value, list):
            rendered = "+".join(str(item) for item in value)
        else:
            rendered = str(value)
        serialized.append(f"{key}={rendered}")
    return "|".join(serialized)
