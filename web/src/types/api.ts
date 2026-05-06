export type RunType = "session" | "backtest" | "benchmark";
export type TournamentType = "strategy_vs_strategy" | "strategy_vs_scenario" | "parameter_sweep" | "multi_symbol_sweep";
export type RunStatus = "pending" | "running" | "completed" | "failed" | "canceled";
export type TimelineCategory = "command" | "event" | "snapshot" | "account" | "log";
export type StreamCategory = "status" | "progress" | "event" | "snapshot" | "account" | "log" | "error" | "completed";

export type JsonValue = null | boolean | number | string | JsonValue[] | { [key: string]: JsonValue };
export type JsonObject = { [key: string]: JsonValue };

export interface BenchmarkScenario {
  name: string;
  operation_count: number;
  elapsed_ms: number;
  ops_per_sec: number;
  notes?: string | null;
  config: JsonObject;
}

export interface BenchmarkRun {
  benchmark_id: string;
  created_at: string;
  git_sha: string | null;
  machine: JsonObject;
  scenarios: BenchmarkScenario[];
  notes?: string | null;
  config: JsonObject;
}

export interface BenchmarkScenarioComparison {
  name: string;
  baseline_ops_per_sec: number | null;
  candidate_ops_per_sec: number | null;
  percent_delta: number | null;
  regression: boolean;
  improvement: boolean;
  threshold_percent: number;
}

export interface BenchmarkComparison {
  baseline_id: string;
  candidate_id: string;
  threshold_percent: number;
  has_regression: boolean;
  scenarios: BenchmarkScenarioComparison[];
}

export interface BenchmarkCompareRequest {
  baseline_id?: string | null;
  candidate_id?: string | null;
  threshold_percent?: number;
}

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
  hostname: string;
  process_id: number | null;
  started_at: string | null;
  heartbeat_at: string | null;
  updated_at: string;
  capabilities: JsonObject;
  status: string;
  current_run_id: string | null;
  progress_summary: JsonObject;
  cpu_percent: number | null;
  memory_bytes: number | null;
  drain_requested: boolean;
  shutdown_requested: boolean;
}

export interface SchedulerStatus {
  pending_count: number;
  running_count: number;
  completed_count: number;
  failed_count: number;
  stale_worker_count: number;
  stale_job_count: number;
  queue_depth: number;
  average_wait_seconds: number;
  average_run_seconds: number;
  worker_utilization: number;
  throughput_per_minute: number;
}

export interface RequeueStaleResponse {
  stale_workers: number;
  requeued_runs: string[];
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

export type ReplayVerificationStatus = "verified" | "mismatch" | "partial" | "failed";
export type RunDiffStatus = "matching" | "mismatch" | "partial" | "failed";

export interface EventHashSummary {
  event_hash: string;
  snapshot_hash: string;
  account_hash: string;
  report_hash: string;
  combined_hash: string;
  event_count: number;
  snapshot_count: number;
  account_count: number;
  trade_count: number;
  sequence_count: number;
  sequence_hash: string;
}

export interface ReplayVerificationReport {
  run_id: string;
  status: ReplayVerificationStatus;
  verified_at: string;
  matching_fields: string[];
  mismatched_fields: string[];
  message: string;
  original_hashes: EventHashSummary;
  replay_hashes: EventHashSummary | null;
  first_divergence_step: number | null;
  metric_deltas: Record<string, number>;
  comparisons: Record<string, boolean>;
  error: string | null;
}

export interface RunDiffRequest { left_run_id: string; right_run_id: string; }
export interface RunDiffResult {
  left_run_id: string;
  right_run_id: string;
  status: RunDiffStatus;
  generated_at: string;
  matching_fields: string[];
  mismatched_fields: string[];
  first_divergence_step: number | null;
  metric_deltas: Record<string, number>;
  event_hash_comparison: JsonObject;
  snapshot_hash_comparison: JsonObject;
  account_hash_comparison: JsonObject;
  report_hash_comparison: JsonObject;
  timeline_divergence: JsonObject;
  pnl_divergence: JsonObject;
  sequence_divergence: JsonObject;
  left_hashes: EventHashSummary;
  right_hashes: EventHashSummary;
}
