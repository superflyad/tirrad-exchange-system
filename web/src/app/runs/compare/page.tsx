import { RunCompareClient } from "@/components/RunCompareClient";
import { tesApi } from "@/lib/api/client";

export const dynamic = "force-dynamic";

export default async function RunComparePage() {
  const runs = await tesApi.listRuns().catch(() => []);
  return (
    <div className="stack">
      <header className="page-header split">
        <div>
          <p className="eyebrow">Run diff</p>
          <h1>Compare runs</h1>
          <p>Diff event hashes, snapshots, account states, sequence timelines, PnL, and report metrics.</p>
        </div>
        <a className="button" href="/runs">Back to runs</a>
      </header>
      <RunCompareClient runs={runs} />
    </div>
  );
}
