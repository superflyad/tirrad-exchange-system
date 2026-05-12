"use client";

import { useCallback, useEffect, useState } from "react";

import { tesApi } from "@/lib/api/client";
import type { RunSummary, WorkerSummary } from "@/types/api";
import { RunsTable } from "./RunsTable";

export function RunsBrowser() {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [workers, setWorkers] = useState<WorkerSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [demoError, setDemoError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [nextRuns, nextWorkers] = await Promise.all([
        tesApi.listRuns(),
        tesApi.listWorkers().catch(() => []),
      ]);
      setRuns(nextRuns);
      setWorkers(nextWorkers);
    } catch (caught) {
      setRuns([]);
      setError(apiErrorMessage(caught, "TES API is unreachable. Start it with ./tes api serve and refresh the dashboard."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const generateDemoRun = async () => {
    setGenerating(true);
    setDemoError(null);
    try {
      await tesApi.generateDemoRun();
      await refresh();
    } catch (caught) {
      setDemoError(apiErrorMessage(caught, "Could not generate a demo run. Confirm the TES API is running."));
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="stack">
      <header className="page-header split">
        <div>
          <p className="eyebrow">Run persistence</p>
          <h1>Runs</h1>
          <p>Filter, sort, and open persisted TES sessions and backtests.</p>
          {error ? <p className="error-text" role="alert">{error}</p> : null}
        </div>
        <div className="cluster">
          <button className="button primary" onClick={generateDemoRun} disabled={generating}>
            {generating ? "Generating demo run…" : "Generate Demo Run"}
          </button>
          <a className="button" href="/runs/compare">Compare runs</a>
          <button className="button" onClick={() => void refresh()} disabled={loading}>Refresh</button>
        </div>
      </header>
      {demoError ? <section className="panel alert-panel" role="alert"><p className="error-text">{demoError}</p></section> : null}
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
      {loading ? <p>Loading runs…</p> : <RunsTable runs={runs} onGenerateDemoRun={generateDemoRun} generatingDemoRun={generating} />}
    </div>
  );
}

function apiErrorMessage(caught: unknown, fallback: string): string {
  return caught instanceof Error && caught.message ? caught.message : fallback;
}
