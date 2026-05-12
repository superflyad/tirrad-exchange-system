"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { formatDate, formatNumber, runRejections, runScenario, runSteps, runStrategy, runTrades, symbolsForRun } from "@/lib/api/metrics";
import type { RunSummary } from "@/types/api";
import { StatusBadge } from "./StatusBadge";

type SortKey = "created_at" | "status" | "scenario" | "strategy" | "total_trades" | "rejections" | "steps";
const PAGE_SIZE = 12;

export function RunsTable({ runs, onGenerateDemoRun, generatingDemoRun = false }: { runs: RunSummary[]; onGenerateDemoRun?: () => void | Promise<void>; generatingDemoRun?: boolean }) {
  const [filter, setFilter] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("created_at");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(0);

  const filtered = useMemo(() => {
    const needle = filter.trim().toLowerCase();
    const visible = needle
      ? runs.filter((run) => [run.run_id, runScenario(run) ?? "", runStrategy(run) ?? "", run.status, ...symbolsForRun(run)].join(" ").toLowerCase().includes(needle))
      : runs;
    return [...visible].sort((a, b) => compareRuns(a, b, sortKey) * (sortDirection === "asc" ? 1 : -1));
  }, [filter, runs, sortDirection, sortKey]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, pageCount - 1);
  const rows = filtered.slice(safePage * PAGE_SIZE, safePage * PAGE_SIZE + PAGE_SIZE);

  const setSort = (key: SortKey) => {
    if (sortKey === key) setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
    else {
      setSortKey(key);
      setSortDirection("desc");
    }
  };

  return (
    <section className="panel">
      <div className="toolbar">
        <input
          aria-label="Filter runs"
          placeholder="Filter by run, status, scenario, strategy, symbol…"
          value={filter}
          onChange={(event) => {
            setFilter(event.target.value);
            setPage(0);
          }}
        />
        <span className="muted">{filtered.length} runs</span>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <SortableHeader label="run_id" sortKey="created_at" active={sortKey} direction={sortDirection} onSort={setSort} />
              <SortableHeader label="scenario" sortKey="scenario" active={sortKey} direction={sortDirection} onSort={setSort} />
              <SortableHeader label="strategy" sortKey="strategy" active={sortKey} direction={sortDirection} onSort={setSort} />
              <th>created_at</th>
              <SortableHeader label="steps" sortKey="steps" active={sortKey} direction={sortDirection} onSort={setSort} />
              <SortableHeader label="trades" sortKey="total_trades" active={sortKey} direction={sortDirection} onSort={setSort} />
              <SortableHeader label="rejections" sortKey="rejections" active={sortKey} direction={sortDirection} onSort={setSort} />
              <SortableHeader label="status" sortKey="status" active={sortKey} direction={sortDirection} onSort={setSort} />
            </tr>
          </thead>
          <tbody>
            {rows.map((run) => (
              <tr key={run.run_id}>
                <td><Link href={`/runs/${run.run_id}/replay`} className="mono link">{run.run_id}</Link></td>
                <td>{runScenario(run) ?? "—"}</td>
                <td>{runStrategy(run) ?? "—"}</td>
                <td>{formatDate(run.created_at)}</td>
                <td>{formatNumber(runSteps(run))}</td>
                <td>{formatNumber(runTrades(run))}</td>
                <td>{formatNumber(runRejections(run))}</td>
                <td><StatusBadge status={run.status} /></td>
              </tr>
            ))}
            {rows.length === 0 ? <tr><td colSpan={8} className="empty">{runs.length === 0 ? <EmptyRuns onGenerateDemoRun={onGenerateDemoRun} generatingDemoRun={generatingDemoRun} /> : "No runs match this filter."}</td></tr> : null}
          </tbody>
        </table>
      </div>
      <div className="pagination">
        <button onClick={() => setPage(Math.max(0, safePage - 1))} disabled={safePage === 0}>Previous</button>
        <span>Page {safePage + 1} / {pageCount}</span>
        <button onClick={() => setPage(Math.min(pageCount - 1, safePage + 1))} disabled={safePage >= pageCount - 1}>Next</button>
      </div>
    </section>
  );
}

function SortableHeader({ label, sortKey, active, direction, onSort }: { label: string; sortKey: SortKey; active: SortKey; direction: "asc" | "desc"; onSort: (key: SortKey) => void; }) {
  return <th><button className="table-sort" onClick={() => onSort(sortKey)}>{label} {active === sortKey ? (direction === "asc" ? "↑" : "↓") : ""}</button></th>;
}

function compareRuns(a: RunSummary, b: RunSummary, key: SortKey): number {
  const valueA = sortValue(a, key);
  const valueB = sortValue(b, key);
  return typeof valueA === "number" && typeof valueB === "number" ? valueA - valueB : String(valueA).localeCompare(String(valueB));
}

function sortValue(run: RunSummary, key: SortKey): string | number {
  if (key === "created_at") return new Date(run.created_at).getTime();
  if (key === "scenario") return runScenario(run) ?? "";
  if (key === "strategy") return runStrategy(run) ?? "";
  if (key === "status") return run.status;
  if (key === "steps") return runSteps(run) ?? -1;
  if (key === "total_trades") return runTrades(run) ?? -1;
  if (key === "rejections") return runRejections(run) ?? -1;
  return "";
}

function EmptyRuns({ onGenerateDemoRun, generatingDemoRun }: { onGenerateDemoRun?: () => void | Promise<void>; generatingDemoRun: boolean }) {
  return (
    <div className="empty-action">
      <p>No runs yet. Generate demo run.</p>
      {onGenerateDemoRun ? <button className="button primary" onClick={() => void onGenerateDemoRun()} disabled={generatingDemoRun}>{generatingDemoRun ? "Generating demo run…" : "Generate Demo Run"}</button> : null}
    </div>
  );
}
