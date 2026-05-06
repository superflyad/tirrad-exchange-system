from __future__ import annotations

from dataclasses import dataclass
from random import Random

from sim.tes_models.commands import HiddenOrderCommand, IcebergOrderCommand, LimitOrderCommand, MarketOrderCommand, TesCommand


@dataclass(frozen=True)
class MarketParticipant:
    participant_id: str
    style: str

    def generate(self, *, rng: Random, symbol: str, fair_price: int, spread: int, min_qty: int, max_qty: int, market_order_prob: float) -> list[TesCommand]:
        qty = rng.randint(min_qty, max_qty)
        if self.style == "liquidity_provider":
            return [
                LimitOrderCommand("BUY", max(1, fair_price - spread), qty, "GTC", symbol),
                LimitOrderCommand("SELL", max(1, fair_price + spread), qty, "GTC", symbol),
            ]
        if self.style == "hidden_liquidity_provider":
            side = "BUY" if rng.random() < 0.5 else "SELL"
            px = fair_price - spread if side == "BUY" else fair_price + spread
            return [HiddenOrderCommand(side, max(1, px), qty, symbol)]
        if self.style == "iceberg_liquidity_provider":
            display_qty = max(1, min(qty, max(1, qty // 2)))
            total_qty = max(qty, display_qty + 1)
            side = "BUY" if rng.random() < 0.5 else "SELL"
            px = fair_price - spread if side == "BUY" else fair_price + spread
            return [IcebergOrderCommand(side, max(1, px), total_qty, display_qty, symbol)]
        if self.style == "crossing_taker" or rng.random() < market_order_prob:
            side = "BUY" if rng.random() < 0.5 else "SELL"
            return [MarketOrderCommand(side, qty, symbol)]
        if self.style == "momentum":
            return [LimitOrderCommand("BUY", max(1, fair_price + spread // 2), qty, "IOC", symbol)]
        if self.style == "mean_reversion":
            return [LimitOrderCommand("SELL", max(1, fair_price + spread), qty, "IOC", symbol)]
        side = "BUY" if rng.random() < 0.5 else "SELL"
        px = fair_price - spread if side == "BUY" else fair_price + spread
        return [LimitOrderCommand(side, max(1, px), qty, "GTC", symbol)]
