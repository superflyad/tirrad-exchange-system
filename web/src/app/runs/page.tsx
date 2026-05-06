import { tesApi } from "@/lib/api/client";
import { RunsTable } from "@/components/RunsTable";

export const dynamic = "force-dynamic";

export default async function RunsPage() {
  const [runsResult, workersResult] = await Promise.allSettled([tesApi.listRuns(), tesApi.listWorkers()]);
  const runs = runsResult.status === "fulfilled" ? runsResult.value : [];
  const workers = workersResult.status === "fulfilled" ? workersResult.value : [];
  return (
    <div className="stack">
      <header className="page-header split">
        <div>
          <p className="eyebrow">Run persistence</p>
          <h1>Runs</h1>
          <p>Filter, sort, and open persisted TES sessions and backtests.</p>
        </div>
        <a className="button" href="/runs">Refresh</a>
      </header>
      <section className="panel">
        <div className="split"><h2>Workers</h2><span className="muted">{workers.length} observed</span></div>
        {workers.length === 0 ? <p className="empty">No worker heartbeats recorded.</p> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>worker_id</th><th>status</th><th>current_run</th><th>updated_at</th></tr></thead>
              <tbody>{workers.map((worker) => (
                <tr key={worker.worker_id}>
                  <td className="mono">{worker.worker_id}</td>
                  <td>{worker.status}</td>
                  <td>{worker.current_run_id ?? "—"}</td>
                  <td>{new Date(worker.updated_at).toLocaleString()}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </section>
      <RunsTable runs={runs} />
    </div>
  );
}
