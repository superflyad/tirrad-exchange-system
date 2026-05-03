from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NewOrderApiSupport:
    market_order: bool
    ioc: bool
    fok: bool

    @property
    def available(self) -> bool:
        return self.market_order and self.ioc and self.fok


def detect_new_order_api_support() -> NewOrderApiSupport:
    from sim.tes_models import commands as command_models

    market_order = hasattr(command_models, "MarketOrderCommand")
    ioc = hasattr(command_models, "ImmediateOrCancelOrderCommand")
    fok = hasattr(command_models, "FillOrKillOrderCommand")

    return NewOrderApiSupport(market_order=market_order, ioc=ioc, fok=fok)


def missing_reason() -> str:
    support = detect_new_order_api_support()
    missing: list[str] = []
    if not support.market_order:
        missing.append("MarketOrderCommand")
    if not support.ioc:
        missing.append("ImmediateOrCancelOrderCommand")
    if not support.fok:
        missing.append("FillOrKillOrderCommand")
    return "New order APIs are not exposed by Python bindings yet (missing: " + ", ".join(missing) + ")."
