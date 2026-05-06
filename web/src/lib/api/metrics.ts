import type { JsonObject, JsonValue, RunSummary, TimelineEntry } from "@/types/api";

export function numberField(source: JsonObject | undefined, keys: string[]): number | null {
  for (const key of keys) {
    const value = source?.[key];
    if (typeof value === "number" && Number.isFinite(value)) return value;
  }
  return null;
}

export function stringArrayField(source: JsonObject | undefined, key: string): string[] {
  const value = source?.[key];
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

export function symbolsForRun(run: RunSummary): string[] {
  const configured = stringArrayField(run.config, "symbols");
  if (configured.length > 0) return configured;
  const reportSymbols = stringArrayField(run.report_summary, "symbols");
  return reportSymbols;
}

export function runSteps(run: RunSummary): number | null {
  return numberField(run.report_summary, ["total_steps", "steps"]) ?? numberField(run.config, ["steps"]);
}

export function runTrades(run: RunSummary): number | null {
  return numberField(run.report_summary, ["total_trades", "trade_count", "trades"]);
}

export function runVolume(run: RunSummary): number | null {
  return numberField(run.report_summary, ["total_volume", "volume"]);
}

export function finalEquity(run: RunSummary): number | null {
  return numberField(run.report_summary, ["final_equity", "equity", "pnl", "final_pnl"]);
}

export function formatNumber(value: number | null | undefined): string {
  return typeof value === "number" ? new Intl.NumberFormat("en-US").format(value) : "—";
}

export function formatDate(value: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export function jsonPreview(value: JsonValue | undefined): string {
  if (value === undefined || value === null) return "—";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value);
}

export function symbolFromPayload(payload: JsonObject): string | null {
  const symbol = payload.symbol;
  if (typeof symbol === "string") return symbol;
  const data = payload.data;
  if (data && typeof data === "object" && !Array.isArray(data)) {
    const nested = (data as JsonObject).symbol;
    if (typeof nested === "string") return nested;
  }
  return null;
}

export function timelineSymbols(entries: TimelineEntry[]): string[] {
  return Array.from(new Set(entries.map((entry) => entry.symbol ?? symbolFromPayload(entry.payload)).filter(Boolean) as string[])).sort();
}
