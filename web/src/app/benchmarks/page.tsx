import { tesApi } from "@/lib/api/client";
import type { BenchmarkComparison, BenchmarkRun } from "@/types/api";

export const dynamic = "force-dynamic";

interface BenchmarksPageProps {
  searchParams?: Promise<{ baseline?: string; candidate?: string; threshold?: string }>;
}

export default async function BenchmarksPage({ searchParams }: BenchmarksPageProps) {
  const params = (await searchParams) ?? {};
  const threshold = Number(params.threshold ?? "10");
  const [runsResult, regressionsResult] = await Promise.allSettled([
    tesApi.listBenchmarks(),
    tesApi.getLatestRegressions(Number.isFinite(threshold) ? threshold : 10),
  ]);
  const runs = runsResult.status === "fulfilled" ? runsResult.value : [];
  let comparison: BenchmarkComparison | null = regressionsResult.status === "fulfilled" ? regressionsResult.value : null;

  if (params.baseline && params.candidate) {
    const explicitComparison = await tesApi
      .compareBenchmarks({ baseline_id: params.baseline, candidate_id: params.candidate, threshold_percent: Number.isFinite(threshold) ? threshold : 10 })
      .catch(() => null);
    comparison = explicitComparison ?? comparison;
  }

  const latest = runs.at(-1) ?? null;
  return (
    <div className="stack">
      <header className="page-header split">
        <div>
          <p className="eyebrow">Performance regression tracking</p>
          <h1>Benchmarks</h1>
          <p>Track TES benchmark runs, scenario throughput, elapsed time, and regression signals.</p>
        </div>
        <a className="button" href="/benchmarks">Refresh</a>
      </header>

      <section className="metrics-grid">
        <div className="metric-card"><span>Benchmark runs</span><strong>{runs.length}</strong></div>
        <div className="metric-card"><span>Latest scenarios</span><strong>{latest?.scenarios.length ?? 0}</strong></div>
        <div className="metric-card"><span>Regression status</span><strong>{comparison?.has_regression ? "Regression" : "Clear"}</strong></div>
      </section>

      <ComparePanel runs={runs} threshold={Number.isFinite(threshold) ? threshold : 10} />
      {comparison ? <ComparisonTable comparison={comparison} /> : <p className="empty">At least two benchmark runs are needed for regression comparison.</p>}
      <RunsTable runs={runs} comparison={comparison} />
      {latest ? <ScenarioTable run={latest} /> : null}
    </div>
  );
}

function ComparePanel({ runs, threshold }: { runs: BenchmarkRun[]; threshold: number }) {
  return (
    <section className="panel">
      <div className="split"><h2>Compare benchmark runs</h2><span className="muted">Default regression threshold: 10%</span></div>
      <form className="toolbar" action="/benchmarks">
        <label>Baseline
          <select name="baseline" defaultValue={runs.at(-2)?.benchmark_id ?? ""}>
            {runs.map((run) => <option key={run.benchmark_id} value={run.benchmark_id}>{shortId(run.benchmark_id)} · {new Date(run.created_at).toLocaleString()}</option>)}
          </select>
        </label>
        <label>Candidate
          <select name="candidate" defaultValue={runs.at(-1)?.benchmark_id ?? ""}>
            {runs.map((run) => <option key={run.benchmark_id} value={run.benchmark_id}>{shortId(run.benchmark_id)} · {new Date(run.created_at).toLocaleString()}</option>)}
          </select>
        </label>
        <label>Threshold %
          <input name="threshold" type="number" min="0" step="0.1" defaultValue={threshold} />
        </label>
        <button type="submit">Compare</button>
      </form>
    </section>
  );
}

function RunsTable({ runs, comparison }: { runs: BenchmarkRun[]; comparison: BenchmarkComparison | null }) {
  return (
    <section className="panel">
      <div className="split"><h2>Benchmark runs</h2><span className="muted">{runs.length} persisted</span></div>
      {runs.length === 0 ? <p className="empty">No benchmark runs have been stored.</p> : (
        <div className="table-wrap"><table><thead><tr><th>benchmark_id</th><th>created_at</th><th>git_sha</th><th>scenarios</th><th>regression</th></tr></thead>
          <tbody>{[...runs].reverse().map((run) => (
            <tr key={run.benchmark_id}>
              <td className="mono">{run.benchmark_id}</td>
              <td>{new Date(run.created_at).toLocaleString()}</td>
              <td className="mono">{run.git_sha?.slice(0, 12) ?? "—"}</td>
              <td>{run.scenarios.length}</td>
              <td>{comparison?.candidate_id === run.benchmark_id && comparison.has_regression ? <span className="status status-failed">Regression</span> : <span className="status status-completed">Clear</span>}</td>
            </tr>
          ))}</tbody></table></div>
      )}
    </section>
  );
}

function ScenarioTable({ run }: { run: BenchmarkRun }) {
  return (
    <section className="panel">
      <div className="split"><h2>Latest scenario results</h2><span className="muted">{shortId(run.benchmark_id)}</span></div>
      <div className="table-wrap"><table><thead><tr><th>scenario</th><th>operation_count</th><th>elapsed_ms</th><th>ops/sec</th><th>notes</th></tr></thead>
        <tbody>{run.scenarios.map((scenario) => (
          <tr key={scenario.name}>
            <td>{scenario.name}</td>
            <td>{scenario.operation_count.toLocaleString()}</td>
            <td>{scenario.elapsed_ms.toFixed(3)}</td>
            <td>{scenario.ops_per_sec.toLocaleString(undefined, { maximumFractionDigits: 2 })}</td>
            <td>{scenario.notes ?? "—"}</td>
          </tr>
        ))}</tbody></table></div>
    </section>
  );
}

function ComparisonTable({ comparison }: { comparison: BenchmarkComparison }) {
  return (
    <section className="panel">
      <div className="split"><h2>Comparison</h2><span className={comparison.has_regression ? "status status-failed" : "status status-completed"}>{comparison.has_regression ? "Regression detected" : "No regression"}</span></div>
      <div className="table-wrap"><table><thead><tr><th>scenario</th><th>baseline ops/sec</th><th>candidate ops/sec</th><th>percent change</th><th>badge</th></tr></thead>
        <tbody>{comparison.scenarios.map((scenario) => (
          <tr key={scenario.name}>
            <td>{scenario.name}</td>
            <td>{formatNumber(scenario.baseline_ops_per_sec)}</td>
            <td>{formatNumber(scenario.candidate_ops_per_sec)}</td>
            <td>{scenario.percent_delta === null ? "—" : `${scenario.percent_delta.toFixed(2)}%`}</td>
            <td>{scenario.regression ? <span className="status status-failed">Regression</span> : scenario.improvement ? <span className="status status-completed">Improvement</span> : <span className="status">Stable</span>}</td>
          </tr>
        ))}</tbody></table></div>
    </section>
  );
}

function shortId(value: string): string { return value.slice(0, 8); }
function formatNumber(value: number | null): string { return value === null ? "—" : value.toLocaleString(undefined, { maximumFractionDigits: 2 }); }
