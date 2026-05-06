"use client";

import Link from "next/link";

import { useRunStream } from "@/hooks/useRunStream";
import { formatNumber } from "@/lib/api/metrics";
import { JsonBlock } from "./JsonBlock";
import { MetricCard } from "./MetricCard";

export function LiveMonitor({ runId }: { runId: string }) {
  const stream = useRunStream(runId);
  const recent = [...stream.messages].reverse().slice(0, 60);
  return (
    <div className="stack">
      <header className="page-header split">
        <div>
          <p className="eyebrow">Live stream</p>
          <h1 className="mono">{runId}</h1>
          <p>Reconnects with exponential backoff if the SSE stream drops.</p>
        </div>
        <Link href={`/runs/${runId}`} className="button">Run detail</Link>
      </header>
      <section className="metrics-grid">
        <MetricCard label="Connection" value={stream.connectionState} hint={stream.error ?? undefined} />
        <MetricCard label="Current step" value={formatNumber(stream.currentStep)} />
        <MetricCard label="Trade count" value={formatNumber(stream.tradeCount)} />
        <MetricCard label="Messages" value={stream.messages.length} />
      </section>
      <section className="panel">
        <h2>Latest prices</h2>
        <div className="price-grid">
          {Object.entries(stream.latestPrices).map(([symbol, price]) => <div key={symbol}><strong>{symbol}</strong><span>{formatNumber(price)}</span></div>)}
          {Object.keys(stream.latestPrices).length === 0 ? <p className="empty">No streamed prices yet.</p> : null}
        </div>
      </section>
      <section className="panel">
        <h2>Recent logs and events</h2>
        <div className="live-log">
          {recent.map((message, index) => (
            <article key={`${message.timestamp}-${index}`} className="log-row">
              <span>{new Date(message.timestamp).toLocaleTimeString()}</span>
              <span>step {message.step ?? "—"}</span>
              <span className={`category category-${message.category}`}>{message.category}</span>
              <strong>{message.type}</strong>
              <JsonBlock value={message.payload} />
            </article>
          ))}
          {recent.length === 0 ? <p className="empty">Waiting for stream messages…</p> : null}
        </div>
      </section>
    </div>
  );
}
