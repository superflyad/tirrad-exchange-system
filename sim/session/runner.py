from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from random import Random
from typing import Any, Callable

import tes_engine
from sim.session.models import MarketSessionConfig, MarketSessionReport, MarketSessionResult
from sim.session.participants import MarketParticipant
from sim.session.scenarios import get_market_scenario
from sim.tes_engine_adapter import execute_command
from sim.tes_models import parse_events


@dataclass
class MarketSessionRunner:
    config: MarketSessionConfig

    def run(self, *, progress_interval: int = 10, progress_callback: Callable[[dict[str, Any]], None] | None = None, verbose: bool = False) -> MarketSessionResult:
        scenario = get_market_scenario(self.config.scenario)
        rng = Random(self.config.seed)
        engine = tes_engine.MatchingEngine()
        participants = self._build_participants()
        last_price = {s: self.config.initial_price for s in self.config.symbols}
        initial_price = dict(last_price)
        steps: list[dict[str, object]] = []
        trades: list[dict[str, object]] = []
        snapshots: list[dict[str, object]] = []
        spreads: dict[str, list[int]] = {s: [] for s in self.config.symbols}
        imbalance: dict[str, list[float]] = {s: [] for s in self.config.symbols}
        per_symbol_volume = {s: 0 for s in self.config.symbols}
        rejected = 0
        halt_count = 0
        halted_symbols: set[str] = set()
        total_orders = 0
        session_cash = 0.0
        session_positions: dict[str, int] = {s: 0 for s in self.config.symbols}

        latest_mid: dict[str, float] = {s: 0.0 for s in self.config.symbols}
        if self.config.scenario in {"volatile_market", "liquidity_shock"}:
            band_width = max(1, int(round(self.config.initial_price * 0.05)))
            for symbol in self.config.symbols:
                engine.set_price_bands(symbol, self.config.initial_price - band_width, self.config.initial_price + band_width)

        if scenario.opening_auction_steps > 0:
            for symbol in self.config.symbols:
                engine.set_trading_phase(symbol, "OpeningAuction")
        for step in range(self.config.steps):
            for symbol in self.config.symbols:
                drift = 1 if self.config.scenario == "trending_up" else -1 if self.config.scenario == "trending_down" else 0
                delta = int(round(rng.gauss(drift, self.config.volatility * scenario.volatility_multiplier * 100)))
                last_price[symbol] = max(1, last_price[symbol] + delta)
                spread = max(1, int(round(self.config.spread_width * scenario.spread_multiplier)))
                step_events = []
                if self.config.scenario in {"volatile_market", "liquidity_shock"}:
                    band_width = max(1, int(round(self.config.initial_price * 0.05)))
                    if last_price[symbol] < self.config.initial_price - band_width or last_price[symbol] > self.config.initial_price + band_width:
                        status = engine.symbol_status(symbol)
                        if not bool(status["halted"]):
                            step_events.extend(parse_events(engine.halt_symbol(symbol, "ScenarioCircuitBreaker")))
                for p in participants:
                    cmds = p.generate(rng=rng, symbol=symbol, fair_price=last_price[symbol], spread=spread, min_qty=self.config.min_order_size, max_qty=self.config.max_order_size, market_order_prob=min(1.0, max(0.0, self.config.probability_market_order + scenario.market_order_bias)))
                    total_orders += len(cmds)
                    for cmd in cmds:
                        events = execute_command(engine, cmd)
                        step_events.extend(events)
                        side = getattr(cmd, "side", None)
                        if side in {"BUY", "SELL"}:
                            sign = 1 if side == "BUY" else -1
                            for event in events:
                                if event.type == "TradeExecuted":
                                    session_positions[symbol] = session_positions.get(symbol, 0) + sign * event.data.qty
                                    session_cash -= sign * event.data.price * event.data.qty

                if scenario.opening_auction_steps > 0 and step == scenario.opening_auction_steps - 1:
                    step_events.extend(parse_events(engine.uncross(symbol)))

                snapshot = engine.snapshot(self.config.depth_levels, symbol)
                snapshots.append({"step": step, "symbol": symbol, "snapshot": snapshot})
                best_bid = snapshot["bids"][0]["price"] if snapshot["bids"] else 0
                best_ask = snapshot["asks"][0]["price"] if snapshot["asks"] else 0
                total_bid_qty = sum(level["qty"] for level in snapshot["bids"])
                total_ask_qty = sum(level["qty"] for level in snapshot["asks"])
                if best_bid > 0 and best_ask > 0:
                    spreads[symbol].append(best_ask - best_bid)
                total = total_bid_qty + total_ask_qty
                if total > 0:
                    imbalance[symbol].append((total_bid_qty - total_ask_qty) / total)

                step_trade_count = 0
                step_trade_volume = 0
                for event in step_events:
                    if event.type == "TradeExecuted":
                        step_trade_count += 1
                        step_trade_volume += event.data.qty
                        per_symbol_volume[symbol] += event.data.qty
                        trades.append({"step": step, "symbol": symbol, "price": event.data.price, "qty": event.data.qty, "maker_order_id": event.data.maker_order_id, "taker_order_id": event.data.taker_order_id})
                    if event.type == "OrderRejected":
                        rejected += 1
                    if event.type == "SymbolHalted":
                        halt_count += 1
                        halted_symbols.add(event.data.symbol)
                    if event.type == "SymbolResumed":
                        halted_symbols.discard(event.data.symbol)
                mid = (best_bid + best_ask) / 2 if best_bid and best_ask else 0
                latest_mid[symbol] = mid
                steps.append({"step": step, "symbol": symbol, "events": len(step_events), "trades": step_trade_count, "volume": step_trade_volume, "mid": mid})

            if progress_callback is not None:
                one_index_step = step + 1
                if one_index_step == 1 or one_index_step == self.config.steps or one_index_step % max(1, progress_interval) == 0:
                    detail = None
                    if verbose:
                        detail = [item for item in steps if item["step"] == step]
                    progress_callback({"step": one_index_step, "total_steps": self.config.steps, "symbols": self.config.symbols, "total_orders": total_orders, "total_trades": len(trades), "latest_mid": dict(latest_mid), "rejected_orders": rejected, "detail": detail})

        total_fees = sum(int(entry.get("fee_delta", 0)) for entry in engine.account_ledger(0)) if hasattr(engine, "account_ledger") else 0
        per_symbol_pnl = {s: float(session_positions.get(s, 0)) * latest_mid.get(s, 0.0) for s in self.config.symbols}
        final_equity = session_cash + sum(per_symbol_pnl.values()) - float(total_fees)
        realized_pnl = session_cash - float(total_fees)
        unrealized_pnl = sum(per_symbol_pnl.values())
        report = MarketSessionReport(
            total_steps=self.config.steps,
            total_orders=total_orders,
            total_trades=len(trades),
            total_volume=sum(t["qty"] for t in trades),
            traded_notional=sum(t["qty"] * t["price"] for t in trades),
            final_mid_price={s: float(last_price[s]) for s in self.config.symbols},
            price_change_pct={s: ((last_price[s] - initial_price[s]) / initial_price[s]) * 100 for s in self.config.symbols},
            average_spread={s: (sum(spreads[s]) / len(spreads[s]) if spreads[s] else 0.0) for s in self.config.symbols},
            max_spread={s: (max(spreads[s]) if spreads[s] else 0) for s in self.config.symbols},
            average_book_imbalance={s: (sum(imbalance[s]) / len(imbalance[s]) if imbalance[s] else 0.0) for s in self.config.symbols},
            per_symbol_volume=per_symbol_volume,
            rejected_orders=rejected,
            per_participant_pnl={p.participant_id: 0 for p in participants},
            final_equity=final_equity,
            per_symbol_pnl=per_symbol_pnl,
            realized_pnl=realized_pnl,
            unrealized_pnl=unrealized_pnl,
            total_fees=total_fees,
            halt_count=halt_count,
            halted_symbols=tuple(sorted(halted_symbols)),
        )
        analytics = {s: {"volume": per_symbol_volume[s], "final_price": last_price[s]} for s in self.config.symbols}
        return MarketSessionResult(self.config, steps, trades, snapshots, report, analytics)

    def save_json(self, result: MarketSessionResult, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")

    def _build_participants(self) -> list[MarketParticipant]:
        styles = ["liquidity_provider", "noise", "momentum", "mean_reversion", "crossing_taker"]
        participants: list[MarketParticipant] = []
        for idx in range(self.config.participant_count):
            participants.append(MarketParticipant(participant_id=f"p{idx}", style=styles[idx % len(styles)]))
        return participants
