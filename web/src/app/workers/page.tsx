import { MetricCard } from "@/components/MetricCard";
import { StatusBadge } from "@/components/StatusBadge";
import { tesApi } from "@/lib/api/client";

export const dynamic = "force-dynamic";

function formatBytes(value: number | null) {
  if (value === null) return "—";
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KiB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MiB`;
}

export default async function WorkersPage() {
  const [workersResult, statusResult] = await Promise.allSettled([
    tesApi.listWorkers(),
    tesApi.getSchedulerStatus(),
  ]);
  const workers = workersResult.status === "fulfilled" ? workersResult.value : [];
  const scheduler = statusResult.status === "fulfilled" ? statusResult.value : null;
  const staleWorkers = workers.filter((worker) => worker.status === "stale");

  return (
    <div className="stack">
      <header className="page-header split">
        <div>
          <p className="eyebrow">Distributed orchestration</p>
          <h1>Workers</h1>
          <p>Monitor active TES workers, leases, stale alerts, and queue health.</p>
        </div>
        <a className="button" href="/workers">Refresh</a>
      </header>
      <section className="metrics-grid">
        <MetricCard label="Queue depth" value={scheduler?.queue_depth ?? 0} />
        <MetricCard label="Pending" value={scheduler?.pending_count ?? 0} />
        <MetricCard label="Running" value={scheduler?.running_count ?? 0} />
        <MetricCard label="Completed" value={scheduler?.completed_count ?? 0} />
        <MetricCard label="Failed" value={scheduler?.failed_count ?? 0} />
        <MetricCard label="Worker utilization" value={`${Math.round((scheduler?.worker_utilization ?? 0) * 100)}%`} />
        <MetricCard label="Stale jobs" value={scheduler?.stale_job_count ?? 0} />
        <MetricCard label="Throughput/min" value={scheduler?.throughput_per_minute ?? 0} />
      </section>
      {staleWorkers.length > 0 ? (
        <section className="panel alert-panel">
          <h2>Stale worker alert</h2>
          <p>{staleWorkers.length} worker heartbeat has exceeded the scheduler timeout. Use the API to requeue stale jobs after confirming leases are abandoned.</p>
        </section>
      ) : null}
      <section className="panel">
        <div className="split"><h2>Active worker table</h2><span className="muted">{workers.length} registered</span></div>
        {workers.length === 0 ? <p className="empty">No workers have registered with the scheduler.</p> : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>worker</th><th>status</th><th>host</th><th>current job</th><th>progress</th><th>cpu</th><th>memory</th><th>heartbeat</th><th>controls</th></tr>
              </thead>
              <tbody>{workers.map((worker) => (
                <tr key={worker.worker_id}>
                  <td className="mono">{worker.worker_id}</td>
                  <td><StatusBadge status={worker.status} /></td>
                  <td>{worker.hostname}<br /><small className="muted">pid {worker.process_id ?? "—"}</small></td>
                  <td className="mono">{worker.current_run_id ?? "—"}</td>
                  <td><pre className="inline-json">{JSON.stringify(worker.progress_summary)}</pre></td>
                  <td>{worker.cpu_percent ?? "—"}</td>
                  <td>{formatBytes(worker.memory_bytes)}</td>
                  <td>{new Date(worker.updated_at).toLocaleString()}</td>
                  <td>{worker.drain_requested ? "draining" : "accepting"}{worker.shutdown_requested ? " · shutdown" : ""}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </section>
      <section className="panel">
        <h2>Scheduler metrics</h2>
        <div className="kv-grid">
          <dl><dt>Average wait</dt><dd>{(scheduler?.average_wait_seconds ?? 0).toFixed(3)}s</dd></dl>
          <dl><dt>Average run duration</dt><dd>{(scheduler?.average_run_seconds ?? 0).toFixed(3)}s</dd></dl>
          <dl><dt>Stale workers</dt><dd>{scheduler?.stale_worker_count ?? staleWorkers.length}</dd></dl>
        </div>
      </section>
    </div>
  );
}
