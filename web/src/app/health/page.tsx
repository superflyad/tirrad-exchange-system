import { JsonBlock } from "@/components/JsonBlock";
import { tesApi } from "@/lib/api/client";

export const dynamic = "force-dynamic";

export default async function HealthPage() {
  const started = Date.now();
  const result = await Promise.allSettled([tesApi.health(), tesApi.listRuns()]);
  const elapsedMs = Date.now() - started;
  return (
    <div className="stack">
      <header className="page-header">
        <p className="eyebrow">API debug</p>
        <h1>Health</h1>
        <p>Checks the proxied TES API target used by the dashboard.</p>
      </header>
      <section className="metrics-grid">
        <article className="metric-card"><span>Status</span><strong>{result[0].status === "fulfilled" ? result[0].value.status : "error"}</strong><small>{elapsedMs} ms</small></article>
        <article className="metric-card"><span>Runs endpoint</span><strong>{result[1].status === "fulfilled" ? `${result[1].value.length} runs` : "error"}</strong></article>
      </section>
      <section className="panel"><h2>Raw checks</h2><JsonBlock value={result.map((item) => item.status === "fulfilled" ? item.value : { error: item.reason.message })} /></section>
    </div>
  );
}
