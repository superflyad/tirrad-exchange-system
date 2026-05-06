"use client";

import Link from "next/link";
import { useState } from "react";

import { tesApi } from "@/lib/api/client";
import { formatDate, formatNumber, runSteps, runTrades, runVolume, symbolsForRun } from "@/lib/api/metrics";
import { useAsync } from "@/hooks/useAsync";
import type { JsonObject, RunDetail } from "@/types/api";
import { JsonBlock } from "./JsonBlock";
import { MarketDataPanel } from "./MarketDataPanel";
import { MetricCard } from "./MetricCard";
import { StatusBadge } from "./StatusBadge";
import { TimelineViewer } from "./TimelineViewer";

const TABS = ["Overview", "Timeline", "Market Data", "Accounts", "Logs", "Raw JSON"] as const;
type Tab = (typeof TABS)[number];

export function RunDetailClient({ run }: { run: RunDetail }) {
  const [tab, setTab] = useState<Tab>("Overview");
  const timeline = useAsync(() => tesApi.getTimeline(run.run_id, { limit: 500 }).then((data) => data.timeline), [run.run_id]);
  const snapshots = useAsync(() => tesApi.getSnapshots(run.run_id, { limit: 200 }).then((data) => data.snapshots), [run.run_id]);
  const accounts = useAsync(() => tesApi.getAccounts(run.run_id).then((data) => data.accounts), [run.run_id]);
  const logs = useAsync(() => tesApi.getLogs(run.run_id, { limit: 200 }).then((data) => data.logs), [run.run_id]);

  return (
    <div className="stack">
      <header className="page-header split">
        <div>
          <p className="eyebrow">Run detail</p>
          <h1 className="mono">{run.run_id}</h1>
          <p>{run.run_type} · <StatusBadge status={run.status} /> · created {formatDate(run.created_at)}</p>
          {run.error ? <p className="error-text">{run.error}</p> : null}
        </div>
        <Link href={`/runs/${run.run_id}/live`} className="button primary">Open live monitor</Link>
      </header>
      <nav className="tabs">{TABS.map((item) => <button key={item} className={tab === item ? "active" : ""} onClick={() => setTab(item)}>{item}</button>)}</nav>
      {tab === "Overview" ? <Overview run={run} accounts={accounts.data ?? []} snapshots={snapshots.data ?? []} /> : null}
      {tab === "Timeline" ? timeline.loading ? <p>Loading timeline…</p> : <TimelineViewer entries={timeline.data ?? []} /> : null}
      {tab === "Market Data" ? <MarketDataPanel snapshots={snapshots.data ?? []} /> : null}
      {tab === "Accounts" ? <DataList title="Account summaries" data={accounts.data ?? []} /> : null}
      {tab === "Logs" ? <DataList title="Logs" data={logs.data ?? []} /> : null}
      {tab === "Raw JSON" ? <JsonBlock value={{ run, timeline: timeline.data, snapshots: snapshots.data, accounts: accounts.data, logs: logs.data }} /> : null}
    </div>
  );
}

function Overview({ run, accounts, snapshots }: { run: RunDetail; accounts: JsonObject[]; snapshots: JsonObject[] }) {
  return (
    <div className="stack">
      <section className="metrics-grid">
        <MetricCard label="Symbols" value={symbolsForRun(run).join(", ") || "—"} />
        <MetricCard label="Steps" value={formatNumber(runSteps(run))} />
        <MetricCard label="Trades" value={formatNumber(runTrades(run))} />
        <MetricCard label="Volume" value={formatNumber(runVolume(run))} />
        <MetricCard label="Accounts" value={accounts.length} />
        <MetricCard label="Snapshots" value={snapshots.length} />
      </section>
      <section className="panel"><h2>Report metrics</h2><KeyValueGrid value={run.report} /></section>
      <section className="panel"><h2>Configuration</h2><KeyValueGrid value={run.config} /></section>
    </div>
  );
}

function KeyValueGrid({ value }: { value: JsonObject }) {
  return <dl className="kv-grid">{Object.entries(value).map(([key, item]) => <div key={key}><dt>{key}</dt><dd>{typeof item === "object" ? JSON.stringify(item) : String(item)}</dd></div>)}</dl>;
}

function DataList({ title, data }: { title: string; data: JsonObject[] }) {
  return <section className="panel"><h2>{title}</h2>{data.map((item, index) => <JsonBlock key={index} value={item} />)}{data.length === 0 ? <p className="empty">No records available.</p> : null}</section>;
}
