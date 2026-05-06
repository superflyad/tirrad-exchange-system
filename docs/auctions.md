# Trading Phases and Auctions

TES supports per-symbol trading phases so simulations can distinguish continuous matching from auction-style price discovery.

## Trading phases

Each symbol is independently in one of these phases:

- `Continuous`: standard TES continuous limit-order-book matching.
- `OpeningAuction`: orders rest without continuous matching until an uncross is requested.
- `ClosingAuction`: same mechanics as the opening auction, intended for close scenarios.
- `Halted`: reserved compatibility phase for halted symbols.

C++ uses `set_trading_phase(symbol, phase)` and `trading_phase(symbol)`. Python bindings expose the same names and use string phases: `Continuous`, `OpeningAuction`, `ClosingAuction`, and `Halted`.

## Opening and closing auction flow

A typical auction flow is:

1. Set a symbol to `OpeningAuction` or `ClosingAuction`.
2. Submit limit orders normally. Orders accumulate in price/time priority; marketable interest does not execute immediately.
3. Read indicative data with `indicative_price(symbol)`, `indicative_volume(symbol)`, and `auction_imbalance(symbol)`.
4. Call `uncross(symbol)` to execute the deterministic auction.
5. TES emits ordinary trade/lifecycle events plus auction lifecycle events, and the symbol returns to `Continuous` after a successful uncross phase transition.

Cancel and replace remain available during auction accumulation.

## Uncrossing logic

TES evaluates candidate clearing prices from visible order prices and chooses the deterministic auction price with these rules, in order:

1. Maximize matched quantity.
2. Minimize absolute imbalance.
3. Choose the price closest to the latest reference mark when one is available.
4. Choose the lowest remaining candidate price as the final deterministic tie-break.

At the clearing price, TES matches eligible bids priced at or above the clearing price against eligible asks priced at or below the clearing price. Execution preserves existing book price/time ordering and settles trades at the auction clearing price.

## Indicative semantics

`indicative_price(symbol)` is the current clearing price that would be selected if `uncross(symbol)` ran immediately, or `None` if no executable auction interest exists. `indicative_volume(symbol)` is the executable quantity at that price. `auction_imbalance(symbol)` is signed `eligible_bid_qty - eligible_ask_qty` at the indicative price, so positive values indicate excess buy interest and negative values indicate excess sell interest.
