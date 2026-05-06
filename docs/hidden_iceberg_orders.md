# Hidden and Iceberg Orders

TES supports three deterministic limit-order visibility types:

- **Displayed**: the existing `place_limit_order(...)` behavior. The full resting quantity is visible and contributes to displayed depth, snapshots, and top-of-book.
- **Hidden**: submitted through `place_hidden_order(...)`. Hidden quantity rests at its limit price but is excluded from displayed depth, snapshots, and top-of-book.
- **Iceberg**: submitted through `place_iceberg_order(...)`. Only the current displayed clip is visible; reserve quantity is hidden until replenished.

## Displayed depth and snapshots

Displayed book depth includes only visible quantity:

- displayed orders contribute their full remaining quantity;
- hidden orders contribute zero displayed quantity;
- iceberg orders contribute only `current_visible_qty`;
- iceberg `reserve_qty` / `hidden_remaining` is excluded until it replenishes a new visible clip.

Hidden-only price levels do not improve the displayed best bid or best ask. Hidden-only submissions also do not advance the displayed-book sequence number. Executions and iceberg replenishments remain deterministic and are recorded as events.

## Iceberg fields

An accepted iceberg event exposes:

- `total_qty`: full submitted quantity;
- `display_qty`: maximum visible clip size;
- `reserve_qty` / `hidden_remaining`: currently hidden reserve after the first clip is displayed;
- `current_visible_qty`: currently displayed clip quantity.

When an iceberg visible clip fully fills, TES replenishes the order with `min(display_qty, reserve_qty)`. The replenishment emits `IcebergReplenished` with the replenished clip, remaining reserve, and total remaining quantity.

## Matching priority

Within a single price level TES uses this deterministic priority:

1. displayed orders, FIFO;
2. iceberg visible clips, FIFO;
3. hidden liquidity, FIFO.

When an iceberg replenishes, the new visible clip is appended to the back of the iceberg-visible queue at that price. This means replenishment loses priority to already resting iceberg visible clips at the same price, while displayed orders at that price still have priority over all iceberg clips.

## Risk and reserve behavior

TES reserves resources for the full remaining hidden or iceberg order quantity, not just the visible portion:

- buy hidden and iceberg orders reserve the full notional or margin-defined worst-case notional for `total_qty`;
- sell hidden and iceberg orders reserve the full sell quantity, and any required short-sale margin, for `total_qty`;
- canceling a hidden or iceberg order releases the remaining reserved resources once.

## Cancel/replace

`cancel(...)` supports hidden and iceberg orders and releases the full remaining reserve/visible resources.

`replace_order(...)` remains available for displayed limit orders. Hidden and iceberg replace is explicitly rejected to keep the priority and reserve contract simple; cancel the order and submit a new hidden or iceberg order instead. A new submission receives new deterministic priority.

## Replay and Python bindings

Python bindings expose:

- `place_hidden_order(side, price_ticks, qty, symbol=..., account_id=...)`;
- `place_iceberg_order(side, price_ticks, total_qty, display_qty, symbol=..., account_id=...)`;
- `HiddenOrderAccepted`, `IcebergOrderAccepted`, and `IcebergReplenished` event conversion.

Replay and serialized event streams preserve hidden submissions, iceberg submissions, replenishment events, and matching results through the normal strict `{ "type": "...", "data": {...} }` event shape.
