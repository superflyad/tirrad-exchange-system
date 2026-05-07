"use client";

import { useEffect, useMemo, useState } from "react";

import { JsonBlock } from "@/components/JsonBlock";
import { MetricCard } from "@/components/MetricCard";
import { useAsync } from "@/hooks/useAsync";
import { tesApi } from "@/lib/api/client";
import type { JsonObject, ReplayFrame, TimelineEntry } from "@/types/api";

const SPEEDS = [0.5, 1, 2, 4, 8];
const WINDOW = 50;

export function ReplayViewer({ runId }: { runId: string }) {
  const session = useAsync(() => tesApi.getReplay(runId), [runId]);
  const summary = useAsync(() => tesApi.getReplaySummary(runId), [runId]);
  const [currentStep, setCurrentStep] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [symbol, setSymbol] = useState("");
  const [frame, setFrame] = useState<ReplayFrame | null>(null);
  const [eventType, setEventType] = useState("");

  const timeline = session.data?.timeline;
  const symbols = timeline?.symbols ?? summary.data?.symbols ?? [];

  useEffect(() => {
    if (session.data) {
      setCurrentStep(session.data.cursor.step);
      setFrame(session.data.frame);
    }
  }, [session.data]);

  useEffect(() => {
    if (!timeline) return;
    const end = Math.min(currentStep + WINDOW, timeline.end_step);
    let cancelled = false;
    tesApi.getReplayRange(runId, {
      start_step: currentStep,
      end_step: end,
      symbol: symbol || undefined,
      include_snapshots: true,
      include_events: true,
      include_accounts: true,
    }).then((data) => {
      if (!cancelled) setFrame(data.frames[0] ?? null);
    }).catch(() => undefined);
    return () => { cancelled = true; };
  }, [currentStep, runId, symbol, timeline]);

  useEffect(() => {
    if (!playing || !timeline) return;
    const interval = window.setInterval(() => {
      setCurrentStep((step) => nextTimelineStep(timeline.steps, step, timeline.end_step));
    }, Math.max(80, 800 / speed));
    return () => window.clearInterval(interval);
  }, [playing, speed, timeline]);

  const eventEntries = useAsync(
    () => tesApi.getTimeline(runId, { category: "event", symbol, type: eventType, limit: 300 }).then((data) => data.timeline),
    [runId, symbol, eventType],
  );

  if (session.loading) return <p>Loading replay…</p>;
  if (session.error) return <p className="error-text">{session.error}</p>;
  if (!timeline) return <p className="empty">Replay timeline is unavailable.</p>;

  const topOfBook = frame?.top_of_book ?? {};
  const selectedSymbol = symbol || frame?.symbol || symbols[0] || "";
  const book = selectedSymbol && isJsonObject(topOfBook[selectedSymbol]) ? topOfBook[selectedSymbol] : {};
  const filteredEvents = (eventEntries.data ?? []).filter((entry) => !eventType || entry.type === eventType);

  return (
    <div className="stack">
      <header className="page-header split">
        <div>
          <p className="eyebrow">Replay viewer</p>
          <h1 className="mono">{runId}</h1>
          <p>Frame {currentStep} of {timeline.end_step} · {timeline.total_frames} indexed frames</p>
        </div>
        <a className="button" href={`/runs/${runId}`}>Back to run</a>
      </header>

      <section className="panel stack">
        <div className="replay-controls">
          <button onClick={() => setCurrentStep(timeline.start_step)}>⏮ First</button>
          <button onClick={() => setCurrentStep(previousTimelineStep(timeline.steps, currentStep, timeline.start_step))}>◀ Prev</button>
          <button className="button primary" onClick={() => setPlaying((value) => !value)}>{playing ? "Pause" : "Play"}</button>
          <button onClick={() => setCurrentStep(nextTimelineStep(timeline.steps, currentStep, timeline.end_step))}>Next ▶</button>
          <button onClick={() => setCurrentStep(timeline.end_step)}>Last ⏭</button>
          <label>Speed<select value={speed} onChange={(event) => setSpeed(Number(event.target.value))}>{SPEEDS.map((item) => <option key={item} value={item}>{item}x</option>)}</select></label>
          <label>Symbol<select value={symbol} onChange={(event) => setSymbol(event.target.value)}><option value="">All symbols</option>{symbols.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
        </div>
        <input aria-label="Timeline scrubber" type="range" min={timeline.start_step} max={timeline.end_step} value={currentStep} onChange={(event) => setCurrentStep(Number(event.target.value))} />
        <div className="timeline-markers">{timeline.event_steps.slice(0, 80).map((step) => <button key={step} title={`Jump to event step ${step}`} style={{ left: `${markerLeft(step, timeline.start_step, timeline.end_step)}%` }} onClick={() => setCurrentStep(step)} />)}</div>
      </section>

      <section className="metrics-grid">
        <MetricCard label="Trades" value={summary.data?.total_trades ?? frame?.trades.length ?? 0} />
        <MetricCard label="Frame volume" value={String(frame?.market_metrics.volume ?? 0)} />
        <MetricCard label="Spread" value={String(book.spread ?? "—")} />
        <MetricCard label="Imbalance" value={formatDecimal(book.imbalance)} />
      </section>

      <div className="replay-grid">
        <OrderBookPanel book={book} symbol={selectedSymbol} />
        <PriceChart frame={frame} symbol={selectedSymbol} />
      </div>

      <div className="replay-grid">
        <TradeTape trades={frame?.trades ?? []} />
        <AccountPanel frame={frame} />
      </div>

      <section className="panel stack">
        <div className="toolbar grid-toolbar">
          <label>Event type<select value={eventType} onChange={(event) => setEventType(event.target.value)}><option value="">All events</option>{summary.data?.available_event_types.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
          {summary.data?.first_divergence_step != null ? <button onClick={() => setCurrentStep(summary.data!.first_divergence_step!)}>Jump to divergence</button> : null}
        </div>
        <EventExplorer entries={filteredEvents} onJump={setCurrentStep} />
      </section>
    </div>
  );
}

function OrderBookPanel({ book, symbol }: { book: JsonObject; symbol: string }) {
  const bids = ladder(book.bids, book.bid, book.bid_qty);
  const asks = ladder(book.asks, book.ask, book.ask_qty);
  return <section className="panel"><h2>Order book {symbol}</h2><div className="book-ladder"><div>{asks.slice().reverse().map((level, index) => <div className="ask" key={index}><span>{level.price}</span><strong>{level.qty}</strong></div>)}</div><div className="midline">Spread {String(book.spread ?? "—")}</div><div>{bids.map((level, index) => <div className="bid" key={index}><span>{level.price}</span><strong>{level.qty}</strong></div>)}</div></div></section>;
}

function TradeTape({ trades }: { trades: JsonObject[] }) {
  return <section className="panel"><h2>Trade tape</h2><div className="trade-tape">{trades.map((trade, index) => <div key={index}><span className="mono">{String(trade.trade_id ?? index)}</span><span>{String(trade.symbol ?? "—")}</span><strong>{String(trade.price ?? "—")}</strong><span>{String(trade.qty ?? "—")}</span><span>{String(trade.aggressor_side ?? "—")}</span><span>step {String(trade.step ?? "—")}</span></div>)}{trades.length === 0 ? <p className="empty">No trades in this frame.</p> : null}</div></section>;
}

function PriceChart({ frame, symbol }: { frame: ReplayFrame | null; symbol: string }) {
  const book = frame && isJsonObject(frame.top_of_book[symbol]) ? frame.top_of_book[symbol] : {};
  const mid = Number(book.mid ?? 0);
  const last = Number(frame?.trades.at(-1)?.price ?? mid ?? 0);
  const height = 120;
  return <section className="panel"><h2>Price chart</h2><svg viewBox="0 0 320 140" className="price-chart" role="img" aria-label="mid price and last trade price"><polyline points={`10,${height - mid} 160,${height - mid} 310,${height - last}`} fill="none" stroke="var(--accent)" strokeWidth="3"/><circle cx="310" cy={height - last} r="5" fill="var(--accent-2)"/><text x="10" y="132" fill="currentColor">mid {mid || "—"} · last {last || "—"}</text></svg></section>;
}

function AccountPanel({ frame }: { frame: ReplayFrame | null }) {
  return <section className="panel"><h2>Accounts</h2><div className="account-grid">{(frame?.account_deltas ?? []).map((account, index) => <div key={index}><strong>{String(account.account_id ?? "account")}</strong><span>Cash {String(account.cash ?? "—")}</span><span>PnL {String(account.pnl ?? "—")}</span><span>Equity {String(account.equity ?? "—")}</span><span>Exposure {String(account.exposure ?? "—")}</span><span>Leverage {String(account.leverage ?? "—")}</span></div>)}{!frame?.account_deltas.length ? <p className="empty">No account updates in this frame.</p> : null}</div></section>;
}

function EventExplorer({ entries, onJump }: { entries: TimelineEntry[]; onJump: (step: number) => void }) {
  return <div className="timeline-list">{entries.map((entry) => <details className="timeline-entry" key={`${entry.sequence}-${entry.step}-${entry.type}`}><summary><button onClick={(event) => { event.preventDefault(); if (entry.step != null) onJump(entry.step); }}>Jump</button> step {entry.step ?? "—"} · {entry.type} · {entry.symbol ?? "—"} · {entry.summary}</summary><JsonBlock value={entry.payload} /></details>)}{entries.length === 0 ? <p className="empty">No matching events.</p> : null}</div>;
}

function nextTimelineStep(steps: number[], current: number, fallback: number): number { return steps.find((step) => step > current) ?? fallback; }
function previousTimelineStep(steps: number[], current: number, fallback: number): number { return steps.filter((step) => step < current).at(-1) ?? fallback; }
function markerLeft(step: number, start: number, end: number): number { return end === start ? 0 : ((step - start) / (end - start)) * 100; }
function isJsonObject(value: unknown): value is JsonObject { return Boolean(value && typeof value === "object" && !Array.isArray(value)); }
function formatDecimal(value: unknown): string { return typeof value === "number" ? value.toFixed(3) : "—"; }
function ladder(value: unknown, price: unknown, qty: unknown): { price: string; qty: string }[] { if (Array.isArray(value)) return value.slice(0, 8).map((item) => isJsonObject(item) ? { price: String(item.price ?? item[0] ?? "—"), qty: String(item.qty ?? item.quantity ?? item[1] ?? "—") } : { price: String(item), qty: "—" }); return [{ price: String(price ?? "—"), qty: String(qty ?? "—") }]; }
