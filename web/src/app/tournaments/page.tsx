import Link from "next/link";

import { MetricCard } from "@/components/MetricCard";
import { StatusBadge } from "@/components/StatusBadge";
import { tesApi } from "@/lib/api/client";
import { formatDate } from "@/lib/api/metrics";

export const dynamic = "force-dynamic";

export default async function TournamentsPage() {
  const result = await Promise.allSettled([tesApi.listTournaments()]);
  const tournaments = result[0].status === "fulfilled" ? result[0].value : [];
  const active = tournaments.filter((item) => item.status === "running" || item.status === "pending");
  const completed = tournaments.filter((item) => item.status === "completed");
  return (
    <div className="stack">
      <header className="page-header split">
        <div>
          <p className="eyebrow">Batch research</p>
          <h1>Tournaments</h1>
          <p>Compare strategy, scenario, parameter, and symbol sweeps persisted by the TES API.</p>
        </div>
        <a className="button" href="/tournaments">Refresh</a>
      </header>
      <section className="metrics-grid">
        <MetricCard label="Total tournaments" value={tournaments.length} />
        <MetricCard label="Active" value={active.length} />
        <MetricCard label="Completed" value={completed.length} />
      </section>
      <section className="panel">
        <div className="split"><h2>Tournament history</h2><span className="muted">{tournaments.length} stored</span></div>
        {tournaments.length === 0 ? <p className="empty">No tournaments stored yet. Create one with POST /tournaments/run.</p> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>ID</th><th>Type</th><th>Status</th><th>Children</th><th>Failed</th><th>Created</th></tr></thead>
              <tbody>{tournaments.map((tournament) => (
                <tr key={tournament.tournament_id}>
                  <td><Link className="link mono" href={`/tournaments/${tournament.tournament_id}`}>{tournament.tournament_id}</Link></td>
                  <td>{tournament.tournament_type}</td>
                  <td><StatusBadge status={tournament.status} /></td>
                  <td>{tournament.completed_child_count}/{tournament.child_count}</td>
                  <td>{tournament.failed_child_count}</td>
                  <td>{formatDate(tournament.created_at)}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
