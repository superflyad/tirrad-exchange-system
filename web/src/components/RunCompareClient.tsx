"use client";

import { useState } from "react";

import { tesApi } from "@/lib/api/client";
import type { JsonObject, RunDiffResult, RunSummary } from "@/types/api";
import { JsonBlock } from "./JsonBlock";
import { MetricCard } from "./MetricCard";
import { StatusBadge } from "./StatusBadge";

export function RunCompareClient({ runs }: { runs: RunSummary[] }) {
  const [leftRunId, setLeftRunId] = useState(runs[0]?.run_id ?? "");
  const [rightRunId, setRightRunId] = useState(runs[1]?.run_id ?? runs[0]?.run_id ?? "");
  const [diff, setDiff] = useState<RunDiffResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function compare() {
    setLoading(true);
    setError(null);
    try {
      setDiff(await tesApi.diffRuns({ left_run_id: leftRunId, right_run_id: rightRunId }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Run diff failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="stack">
      <section className="panel stack">
        <div className="split">
          <h2>Select runs</h2>
          <button className="button primary" onClick={compare} disabled={loading || !leftRunId || !rightRunId}>{loading ? "Comparing…" : "Compare runs"}</button>
        </div>
        <div className="metrics-grid">
          <label>Left run<select value={leftRunId} onChange={(event) => setLeftRunId(event.target.value)}>{runs.map((run) => <option key={run.run_id} value={run.run_id}>{run.run_id}</option>)}</select></label>
          <label>Right run<select value={rightRunId} onChange={(event) => setRightRunId(event.target.value)}>{runs.map((run) => <option key={run.run_id} value={run.run_id}>{run.run_id}</option>)}</select></label>
        </div>
        {error ? <p className="error-text">{error}</p> : null}
      </section>
      {diff ? <DiffSummary diff={diff} /> : <p className="empty">Choose two runs to see hash, metric, timeline, and PnL divergence.</p>}
    </div>
  );
}

function DiffSummary({ diff }: { diff: RunDiffResult }) {
  return (
    <section className="panel stack">
      <div className="split"><h2>Diff summary</h2><StatusBadge status={diff.status} /></div>
      <div className="metrics-grid">
        <MetricCard label="Left events" value={diff.left_hashes.event_count} />
        <MetricCard label="Right events" value={diff.right_hashes.event_count} />
        <MetricCard label="Left trades" value={diff.left_hashes.trade_count} />
        <MetricCard label="Right trades" value={diff.right_hashes.trade_count} />
        <MetricCard label="Divergence step" value={diff.first_divergence_step ?? "—"} />
        <MetricCard label="Mismatches" value={diff.mismatched_fields.length} />
      </div>
      <section><h3>Divergence highlights</h3><p>{diff.mismatched_fields.join(", ") || "None"}</p></section>
      <section><h3>Metric deltas</h3><JsonBlock value={diff.metric_deltas as unknown as JsonObject} /></section>
      <JsonBlock value={diff as unknown as JsonObject} />
    </section>
  );
}
