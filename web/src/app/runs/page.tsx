import { tesApi } from "@/lib/api/client";
import { RunsTable } from "@/components/RunsTable";

export const dynamic = "force-dynamic";

export default async function RunsPage() {
  const runs = await tesApi.listRuns();
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
      <RunsTable runs={runs} />
    </div>
  );
}
