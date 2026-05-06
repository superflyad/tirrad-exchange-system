import type { JsonObject } from "@/types/api";
import { formatNumber } from "@/lib/api/metrics";

interface MarketRow {
  symbol: string;
  bid: number | null;
  ask: number | null;
  spread: number | null;
  mid: number | null;
  volume: number | null;
  imbalance: number | null;
}

export function MarketDataPanel({ snapshots }: { snapshots: JsonObject[] }) {
  const rows = latestRows(snapshots);
  return (
    <section className="panel">
      <h2>Market data</h2>
      <div className="market-grid">
        {rows.map((row) => (
          <article className="market-card" key={row.symbol}>
            <h3>{row.symbol}</h3>
            <div className="price-line"><span>Bid {formatNumber(row.bid)}</span><span>Ask {formatNumber(row.ask)}</span></div>
            <div className="spread-bar" title="Relative spread"><span style={{ width: `${spreadWidth(row)}%` }} /></div>
            <dl>
              <div><dt>Mid</dt><dd>{formatNumber(row.mid)}</dd></div>
              <div><dt>Spread</dt><dd>{formatNumber(row.spread)}</dd></div>
              <div><dt>Volume</dt><dd>{formatNumber(row.volume)}</dd></div>
              <div><dt>Imbalance</dt><dd>{formatNumber(row.imbalance)}</dd></div>
            </dl>
          </article>
        ))}
      </div>
      {rows.length === 0 ? <p className="empty">No snapshots are available for this run.</p> : null}
    </section>
  );
}

function latestRows(snapshots: JsonObject[]): MarketRow[] {
  const latest = snapshots.at(-1);
  const symbols = latest?.symbols;
  if (!symbols || typeof symbols !== "object" || Array.isArray(symbols)) return [];
  return Object.entries(symbols as Record<string, JsonObject>).map(([symbol, value]) => {
    const bid = readNumber(value, ["bid", "best_bid"]);
    const ask = readNumber(value, ["ask", "best_ask"]);
    const mid = readNumber(value, ["mid", "mid_price"]) ?? (bid !== null && ask !== null ? (bid + ask) / 2 : null);
    return {
      symbol,
      bid,
      ask,
      spread: bid !== null && ask !== null ? ask - bid : readNumber(value, ["spread"]),
      mid,
      volume: readNumber(value, ["volume", "total_volume"]),
      imbalance: readNumber(value, ["imbalance"]),
    };
  });
}

function readNumber(payload: JsonObject, keys: string[]): number | null {
  for (const key of keys) {
    const value = payload[key];
    if (typeof value === "number") return value;
  }
  return null;
}

function spreadWidth(row: MarketRow): number {
  if (row.spread === null || row.mid === null || row.mid === 0) return 8;
  return Math.min(100, Math.max(4, Math.abs(row.spread / row.mid) * 1000));
}
