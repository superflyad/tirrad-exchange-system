"use client";

import Link from "next/link";
import { useState } from "react";

import { tesApi } from "@/lib/api/client";
import { formatDate, formatNumber, runSteps, runTrades, runVolume, symbolsForRun } from "@/lib/api/metrics";
import { useAsync } from "@/hooks/useAsync";
import type { JsonObject, ReplayVerificationReport, RunDetail } from "@/types/api";
import { JsonBlock } from "./JsonBlock";
import { MarketDataPanel } from "./MarketDataPanel";
import { MetricCard } from "./MetricCard";
import { StatusBadge } from "./StatusBadge";
import { TimelineViewer } from "./TimelineViewer";

const TABS = ["Overview", "Verification", "Timeline", "Market Data", "Accounts", "Logs", "Raw JSON"] as const;
type Tab = (typeof TABS)[number];

export function RunDetailClient({ run }: { run: RunDetail }) {
  const [tab, setTab] = useState<Tab>("Overview");
  const timeline = useAsync(() => tesApi.getTimeline(run.run_id, { limit: 500 }).then((data) => data.timeline), [run.run_id]);
  const snapshots = useAsync(() => tesApi.getSnapshots(run.run_id, { limit: 200 }).then((data) => data.snapshots), [run.run_id]);
  const accounts = useAsync(() => tesApi.getAccounts(run.run_id).then((data) => data.accounts), [run.run_id]);
  const logs = useAsync(() => tesApi.getLogs(run.run_id, { limit: 200 }).then((data) => data.logs), [run.run_id]);
  const verification = useAsync(() => tesApi.getVerification(run.run_id), [run.run_id]);

  return (
    <div className="stack">
      <header className="page-header split">
        <div>
          <p className="eyebrow">Run detail</p>
          <h1 className="mono">{run.run_id}</h1>
          <p>{run.run_type} · <StatusBadge status={run.status} /> · <StatusBadge status={verification.data?.status ?? "unverified"} /> · created {formatDate(run.created_at)}</p>
          {run.error ? <p className="error-text">{run.error}</p> : null}
        </div>
        <div className="toolbar grid-toolbar"><Link href={`/runs/${run.run_id}/replay`} className="button primary">Open replay viewer</Link><Link href={`/runs/${run.run_id}/live`} className="button">Open live monitor</Link></div>
      </header>
      <nav className="tabs">{TABS.map((item) => <button key={item} className={tab === item ? "active" : ""} onClick={() => setTab(item)}>{item}</button>)}</nav>
      {tab === "Overview" ? <Overview run={run} accounts={accounts.data ?? []} snapshots={snapshots.data ?? []} /> : null}
      {tab === "Verification" ? <VerificationPanel runId={run.run_id} initial={verification.data} /> : null}
      {tab === "Timeline" ? timeline.loading ? <p>Loading timeline…</p> : <TimelineViewer entries={timeline.data ?? []} /> : null}
      {tab === "Market Data" ? <MarketDataPanel snapshots={snapshots.data ?? []} /> : null}
      {tab === "Accounts" ? <DataList title="Account summaries" data={accounts.data ?? []} /> : null}
      {tab === "Logs" ? <DataList title="Logs" data={logs.data ?? []} /> : null}
      {tab === "Raw JSON" ? <JsonBlock value={{ run, verification: verification.data, timeline: timeline.data, snapshots: snapshots.data, accounts: accounts.data, logs: logs.data }} /> : null}
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


function VerificationPanel({ runId, initial }: { runId: string; initial?: ReplayVerificationReport | null }) {
  const [report, setReport] = useState<ReplayVerificationReport | undefined>(initial ?? undefined);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function verify() {
    setLoading(true);
    setError(null);
    try {
      setReport(await tesApi.verifyRun(runId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="panel stack">
      <div className="split">
        <div>
          <h2>Replay verification</h2>
          <p className="muted">Rerun the stored config and compare deterministic event, snapshot, account, report, and sequence hashes.</p>
        </div>
        <button className="button primary" onClick={verify} disabled={loading}>{loading ? "Verifying…" : "Run verification"}</button>
      </div>
      {error ? <p className="error-text">{error}</p> : null}
      {report ? (
        <>
          <div className="metrics-grid">
            <MetricCard label="Status" value={report.status} />
            <MetricCard label="Events" value={formatNumber(report.original_hashes.event_count)} />
            <MetricCard label="Trades" value={formatNumber(report.original_hashes.trade_count)} />
            <MetricCard label="Divergence step" value={report.first_divergence_step ?? "—"} />
          </div>
          <p>{report.message}</p>
          <section><h3>Mismatched fields</h3><p>{report.mismatched_fields.join(", ") || "None"}</p></section>
          <JsonBlock value={report as unknown as JsonObject} />
        </>
      ) : <p className="empty">No verification report loaded.</p>}
    </section>
  );
}

function KeyValueGrid({ value }: { value: JsonObject }) {
  return <dl className="kv-grid">{Object.entries(value).map(([key, item]) => <div key={key}><dt>{key}</dt><dd>{typeof item === "object" ? JSON.stringify(item) : String(item)}</dd></div>)}</dl>;
}

function DataList({ title, data }: { title: string; data: JsonObject[] }) {
  return <section className="panel"><h2>{title}</h2>{data.map((item, index) => <JsonBlock key={index} value={item} />)}{data.length === 0 ? <p className="empty">No records available.</p> : null}</section>;
}
