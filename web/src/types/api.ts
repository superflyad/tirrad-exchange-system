export type RunType = "session" | "backtest";
export type TournamentType = "strategy_vs_strategy" | "strategy_vs_scenario" | "parameter_sweep" | "multi_symbol_sweep";
export type RunStatus = "pending" | "running" | "completed" | "failed" | "canceled";
export type TimelineCategory = "command" | "event" | "snapshot" | "account" | "log";
export type StreamCategory = "status" | "progress" | "event" | "snapshot" | "account" | "log" | "error" | "completed";

export type JsonValue = null | boolean | number | string | JsonValue[] | { [key: string]: JsonValue };
export type JsonObject = { [key: string]: JsonValue };

export interface RunSummary {
  run_id: string;
  run_type: RunType;
  status: RunStatus;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  config: JsonObject;
  report_summary: JsonObject;
  error: string | null;
  polling_url?: string | null;
  stream_url?: string | null;
}

export interface TournamentRun {
  tournament_id: string;
  status: RunStatus;
  tournament_type: TournamentType;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  config: JsonObject;
  child_count: number;
  completed_child_count: number;
  failed_child_count: number;
  error: string | null;
}

export interface TournamentResult {
  rank: number;
  child_run_id: string;
  child_key: string;
  status: RunStatus;
  dimensions: JsonObject;
  metrics: JsonObject;
  score: number;
  error: string | null;
}

export interface TournamentReport {
  tournament_id: string;
  status: RunStatus;
  generated_at: string;
  child_count: number;
  completed_child_count: number;
  failed_child_count: number;
  results: TournamentResult[];
  failures: TournamentResult[];
}

export interface TournamentChildrenResponse { tournament_id: string; children: JsonObject[]; }

export interface WorkerSummary {
  worker_id: string;
  status: string;
  updated_at: string;
  current_run_id: string | null;
}

export interface RunDetail extends RunSummary {
  report: JsonObject;
}

export interface TimelineEntry {
  step: number | null;
  timestamp: string | null;
  sequence: number;
  symbol: string | null;
  category: TimelineCategory;
  type: string;
  summary: string;
  payload: JsonObject;
}

export interface StreamMessage {
  run_id: string;
  timestamp: string;
  step: number | null;
  category: StreamCategory;
  type: string;
  payload: JsonObject;
}

export interface HealthResponse {
  status: string;
  service: string;
}

export interface ReportResponse { run_id: string; report: JsonObject; }
export interface TimelineResponse { run_id: string; timeline: TimelineEntry[]; }
export interface EventsResponse { run_id: string; events: JsonObject[]; }
export interface SnapshotsResponse { run_id: string; snapshots: JsonObject[]; }
export interface AccountsResponse { run_id: string; accounts: JsonObject[]; }
export interface LogsResponse { run_id: string; logs: JsonObject[]; }
