# Market Controls: Halts, Circuit Breakers, and Price Bands

TES supports deterministic per-symbol market controls for halt/resume workflows, static price bands, and circuit-breaker driven halts.

## Symbol status lifecycle

Each symbol has an independent status. A symbol is normally `Continuous`/active. Calling `halt_symbol(symbol, reason)` moves only that symbol to `Halted` and emits `SymbolHalted`. Calling `resume_symbol(symbol)` returns the symbol to continuous trading and emits `SymbolResumed` when the symbol was halted. `symbol_status(symbol)` returns a dict-friendly status containing the phase, halted flag, halt reason, and any active lower/upper price band.

Auction phases remain explicit through `set_trading_phase`. If an auction phase is active, normal auction order collection still applies unless the symbol is halted.

## Halt and resume behavior

While a symbol is halted:

- new limit, market, stop, stop-limit, hidden, and iceberg orders are rejected with `OrderRejected(reason="SymbolHalted")`;
- cancels remain available and release account reserves normally;
- stop orders are not evaluated or triggered;
- continuous matching does not run;
- depth and snapshots remain readable;
- other symbols continue trading independently.

Resuming a symbol preserves the resting book. TES does not automatically uncross or continuously match old resting interest on resume beyond the normal behavior of subsequent commands.

## Price band rules

`set_price_bands(symbol, lower_price, upper_price)` installs an inclusive static band and emits `PriceBandUpdated`. `clear_price_bands(symbol)` removes the band and emits `PriceBandUpdated` with null bounds.

- Limit, stop-limit, hidden, and iceberg orders outside the band are rejected with `PriceBandViolation`.
- Market orders are converted to their safe executable limit price and rejected when that execution price would be outside the band.
- Auction uncross prices must be inside the band. If the indicative uncross price is outside the band, the uncross emits `OrderRejected(reason="AuctionPriceOutOfBand")`, triggers a circuit breaker, and halts the symbol.

## Circuit breaker rules

A price-band breach that is discovered at execution time emits `CircuitBreakerTriggered` and halts the affected symbol with `SymbolHalted`. The halt is deterministic and symbol-local. Existing resting orders remain on the book unless explicitly canceled.

## Replay behavior

Replay commands include halt, resume, set-price-band, clear-price-band, trading-phase, auction-uncross, and order-entry commands. Replaying a recorded sequence preserves deterministic halt and price-band rejection behavior, including circuit-breaker and market-control events.
