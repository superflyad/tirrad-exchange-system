import Link from "next/link";

import { tesApi } from "@/lib/api/client";
import { formatNumber, runTrades, runVolume, symbolsForRun } from "@/lib/api/metrics";
import { MetricCard } from "@/components/MetricCard";
import { RunsTable } from "@/components/RunsTable";
import { StatusBadge } from "@/components/StatusBadge";

export const dynamic = "force-dynamic";

export default async function DashboardHome() {
  const [runsResult, healthResult] = await Promise.allSettled([tesApi.listRuns(), tesApi.health()]);
  const runs = runsResult.status === "fulfilled" ? runsResult.value : [];
  const health = healthResult.status === "fulfilled" ? healthResult.value : null;
  const active = runs.filter((run) => run.status === "running" || run.status === "pending");
  const completed = runs.filter((run) => run.status === "completed");
  const failed = runs.filter((run) => run.status === "failed");
  const recentSymbols = Array.from(new Set(runs.flatMap(symbolsForRun))).slice(0, 8);
  const recentRuns = [...runs].sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at)).slice(0, 6);

  return (
    <div className="stack">
      <header className="page-header split">
        <div>
          <p className="eyebrow">Tirrad Exchange System</p>
          <h1>Dashboard</h1>
          <p>Inspect stored runs, replay timelines, and monitor live TES sessions.</p>
        </div>
        <Link href="/runs" className="button primary">View all runs</Link>
      </header>
      <section className="metrics-grid">
        <MetricCard label="API health" value={health?.status ?? "offline"} hint={health?.service ?? (healthResult.status === "rejected" ? healthResult.reason.message : undefined)} />
        <MetricCard label="Total stored runs" value={runs.length} />
        <MetricCard label="Active runs" value={active.length} />
        <MetricCard label="Completed runs" value={completed.length} />
        <MetricCard label="Failed runs" value={failed.length} />
        <MetricCard label="Recent symbols" value={recentSymbols.join(", ") || "—"} />
      </section>
      <section className="panel">
        <div className="split"><h2>Recent runs</h2><Link href="/runs" className="link">Open run list</Link></div>
        <div className="run-cards">
          {recentRuns.map((run) => (
            <Link className="run-card" href={`/runs/${run.run_id}`} key={run.run_id}>
              <span className="mono">{run.run_id}</span>
              <StatusBadge status={run.status} />
              <small>{symbolsForRun(run).join(", ") || "No symbols"}</small>
              <small>{formatNumber(runTrades(run))} trades · {formatNumber(runVolume(run))} volume</small>
            </Link>
          ))}
          {recentRuns.length === 0 ? <p className="empty">No runs stored yet. Start the API and execute a TES session or backtest.</p> : null}
        </div>
      </section>
      <RunsTable runs={runs.slice(0, 24)} />
    </div>
  );
}
