import Link from "next/link";

import { JsonBlock } from "@/components/JsonBlock";
import { MetricCard } from "@/components/MetricCard";
import { StatusBadge } from "@/components/StatusBadge";
import { TournamentLeaderboard } from "@/components/tournaments/TournamentLeaderboard";
import { tesApi } from "@/lib/api/client";
import { formatDate } from "@/lib/api/metrics";

export const dynamic = "force-dynamic";

export default async function TournamentDetailPage({ params }: { params: Promise<{ tournamentId: string }> }) {
  const { tournamentId } = await params;
  const [tournamentResult, reportResult, childrenResult] = await Promise.allSettled([
    tesApi.getTournament(tournamentId),
    tesApi.getTournamentReport(tournamentId),
    tesApi.getTournamentChildren(tournamentId),
  ]);
  if (tournamentResult.status === "rejected") {
    return <div className="panel"><p className="error-text">Unable to load tournament: {tournamentResult.reason.message}</p></div>;
  }
  const tournament = tournamentResult.value;
  const report = reportResult.status === "fulfilled" ? reportResult.value : null;
  const children = childrenResult.status === "fulfilled" ? childrenResult.value.children : [];
  return (
    <div className="stack">
      <header className="page-header split">
        <div>
          <p className="eyebrow">Tournament detail</p>
          <h1 className="mono">{tournament.tournament_id}</h1>
          <p>{tournament.tournament_type} · created {formatDate(tournament.created_at)}</p>
        </div>
        <StatusBadge status={tournament.status} />
      </header>
      <section className="metrics-grid">
        <MetricCard label="Children" value={tournament.child_count} />
        <MetricCard label="Completed" value={tournament.completed_child_count} />
        <MetricCard label="Failed" value={tournament.failed_child_count} />
        <MetricCard label="Report status" value={report?.status ?? "pending"} />
      </section>
      <section className="panel"><h2>Leaderboard</h2><TournamentLeaderboard results={report?.results ?? []} /></section>
      <section className="panel">
        <div className="split"><h2>Child runs</h2><span className="muted">{children.length} linked</span></div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Child key</th><th>Run</th><th>Type</th><th>Dimensions</th></tr></thead>
            <tbody>{children.map((child) => {
              const runId = typeof child.child_run_id === "string" ? child.child_run_id : "";
              return <tr key={runId || JSON.stringify(child)}><td className="mono">{String(child.child_key)}</td><td>{runId ? <Link className="link mono" href={`/runs/${runId}`}>{runId}</Link> : "—"}</td><td>{String(child.run_type)}</td><td><JsonBlock value={child.dimensions} /></td></tr>;
            })}</tbody>
          </table>
        </div>
      </section>
      <section className="panel"><h2>Config</h2><JsonBlock value={tournament.config} /></section>
    </div>
  );
}
