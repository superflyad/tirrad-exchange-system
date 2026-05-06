import Link from "next/link";

import { formatNumber, jsonPreview } from "@/lib/api/metrics";
import type { TournamentResult } from "@/types/api";

export function TournamentLeaderboard({ results }: { results: TournamentResult[] }) {
  if (results.length === 0) return <p className="empty">No completed child runs to rank yet.</p>;
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr><th>Rank</th><th>Child run</th><th>Strategy</th><th>Scenario</th><th>Symbol/seed</th><th>Ending equity</th><th>PnL</th><th>Volume</th><th>Fill ratio</th><th>Reject rate</th><th>Exposure</th></tr>
        </thead>
        <tbody>
          {results.map((result) => (
            <tr key={result.child_run_id}>
              <td>{result.rank}</td>
              <td><Link className="link mono" href={`/runs/${result.child_run_id}`}>{result.child_run_id.slice(0, 12)}</Link></td>
              <td>{jsonPreview(result.dimensions.strategy)}</td>
              <td>{jsonPreview(result.dimensions.scenario)}</td>
              <td>{jsonPreview(result.dimensions.symbols)} · {jsonPreview(result.dimensions.seed)}</td>
              <td>{formatNumber(numberMetric(result, "ending_equity"))}</td>
              <td>{formatNumber(numberMetric(result, "total_pnl"))}</td>
              <td>{formatNumber(numberMetric(result, "total_volume"))}</td>
              <td>{formatRatio(numberMetric(result, "fill_ratio"))}</td>
              <td>{formatRatio(numberMetric(result, "rejection_rate"))}</td>
              <td>{formatNumber(numberMetric(result, "final_position_exposure"))}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function numberMetric(result: TournamentResult, key: string): number | null {
  const value = result.metrics[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function formatRatio(value: number | null): string {
  return value === null ? "—" : `${(value * 100).toFixed(1)}%`;
}
