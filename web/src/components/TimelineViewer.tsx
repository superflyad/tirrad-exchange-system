"use client";

import { useMemo, useState } from "react";

import { timelineSymbols } from "@/lib/api/metrics";
import type { TimelineCategory, TimelineEntry } from "@/types/api";
import { JsonBlock } from "./JsonBlock";

const CATEGORIES: (TimelineCategory | "")[] = ["", "command", "event", "snapshot", "account", "log"];

export function TimelineViewer({ entries }: { entries: TimelineEntry[] }) {
  const [symbol, setSymbol] = useState("");
  const [category, setCategory] = useState<TimelineCategory | "">("");
  const [type, setType] = useState("");
  const [expanded, setExpanded] = useState<number | null>(null);
  const symbols = useMemo(() => timelineSymbols(entries), [entries]);
  const types = useMemo(() => Array.from(new Set(entries.map((entry) => entry.type))).sort(), [entries]);
  const visible = entries.filter((entry) => {
    const matchesSymbol = !symbol || entry.symbol === symbol || JSON.stringify(entry.payload).includes(symbol);
    const matchesCategory = !category || entry.category === category;
    const matchesType = !type || entry.type === type;
    return matchesSymbol && matchesCategory && matchesType;
  });

  return (
    <section className="panel">
      <div className="toolbar grid-toolbar">
        <label>Symbol<select value={symbol} onChange={(event) => setSymbol(event.target.value)}><option value="">All</option>{symbols.map((item) => <option key={item}>{item}</option>)}</select></label>
        <label>Category<select value={category} onChange={(event) => setCategory(event.target.value as TimelineCategory | "")} >{CATEGORIES.map((item) => <option key={item || "all"} value={item}>{item || "All"}</option>)}</select></label>
        <label>Type<select value={type} onChange={(event) => setType(event.target.value)}><option value="">All</option>{types.map((item) => <option key={item}>{item}</option>)}</select></label>
        <span className="muted">{visible.length} / {entries.length} entries</span>
      </div>
      <div className="timeline-list">
        {visible.map((entry) => (
          <article className="timeline-entry" key={entry.sequence}>
            <button className="timeline-main" onClick={() => setExpanded(expanded === entry.sequence ? null : entry.sequence)}>
              <span className="mono">#{entry.sequence}</span>
              <span>step {entry.step ?? "—"}</span>
              <span className={`category category-${entry.category}`}>{entry.category}</span>
              <strong>{entry.type}</strong>
              <span>{entry.symbol ?? "—"}</span>
              <span className="timeline-summary">{entry.summary}</span>
            </button>
            {expanded === entry.sequence ? <JsonBlock value={entry.payload} /> : null}
          </article>
        ))}
        {visible.length === 0 ? <p className="empty">No timeline entries match the selected filters.</p> : null}
      </div>
    </section>
  );
}
