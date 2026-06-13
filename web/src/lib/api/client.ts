import type {
  AccountsResponse,
  BenchmarkCompareRequest,
  BenchmarkComparison,
  BenchmarkRun,
  EventsResponse,
  HealthResponse,
  LogsResponse,
  ReportResponse,
  ReplayFrame,
  ReplayRangeResponse,
  ReplaySessionResponse,
  ReplaySummaryResponse,
  ReplayVerificationReport,
  RunDiffRequest,
  RunDiffResult,
  RunDetail,
  RunSummary,
  SnapshotsResponse,
  TimelineCategory,
  TimelineResponse,
  TournamentChildrenResponse,
  TournamentReport,
  TournamentRun,
  WorkerSummary,
  SchedulerStatus,
  RequeueStaleResponse,
} from "@/types/api";

export interface TimelineQuery {
  symbol?: string;
  category?: TimelineCategory | "";
  type?: string;
  limit?: number;
  offset?: number;
}

export interface ReplayRangeQuery {
  start_step?: number;
  end_step?: number;
  symbol?: string;
  include_snapshots?: boolean;
  include_events?: boolean;
  include_accounts?: boolean;
}

export interface CollectionQuery {
  symbol?: string;
  event_type?: string;
  account_id?: string;
  limit?: number;
  offset?: number;
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly payload: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const DEFAULT_API_ORIGIN = "http://127.0.0.1:8000";
const LOCAL_PROXY_BASE = "/api/tes";

// NEXT_PUBLIC_TES_API_URL is the browser-visible dashboard API setting; the local default uses the Next.js proxy.
export const API_BASE_URL = normalizeBaseUrl(process.env.NEXT_PUBLIC_TES_API_URL ?? LOCAL_PROXY_BASE);

function normalizeBaseUrl(value: string): string {
  return value.endsWith("/") ? value.slice(0, -1) : value;
}

function appendQuery(path: string, query?: object): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query ?? {}) as [string, unknown][]) {
    if ((typeof value === "string" || typeof value === "number" || typeof value === "boolean") && value !== "") params.set(key, String(value));
  }
  const serialized = params.toString();
  return serialized ? `${path}?${serialized}` : path;
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${runtimeApiBaseUrl()}${path}`, {
      ...init,
      headers: { Accept: "application/json", ...init?.headers },
    });
  } catch (caught) {
    const details = caught instanceof Error && caught.message ? ` Details: ${caught.message}` : "";
    throw new Error(`TES API is unreachable. Start it with ./tes api serve and try again.${details}`);
  }
  const text = await response.text();
  const payload = text ? JSON.parse(text) : null;
  if (!response.ok) {
    const message = extractErrorMessage(payload) ?? `TES API request failed with ${response.status}`;
    throw new ApiError(response.status, message, payload);
  }
  return payload as T;
}

function runtimeApiBaseUrl(): string {
  if (typeof window !== "undefined" || !API_BASE_URL.startsWith("/")) {
    return API_BASE_URL;
  }

  const apiOrigin = process.env.TES_API_ORIGIN?.trim();
  return normalizeBaseUrl(apiOrigin && apiOrigin !== "" ? apiOrigin : DEFAULT_API_ORIGIN);
}

function extractErrorMessage(payload: unknown): string | undefined {
  if (payload && typeof payload === "object" && "error" in payload) {
    const error = (payload as { error?: { message?: unknown } }).error;
    return typeof error?.message === "string" ? error.message : undefined;
  }
  return undefined;
}

export function streamRunUrl(runId: string, replayLimit = 100): string {
  return `${API_BASE_URL}${appendQuery(`/runs/${encodeURIComponent(runId)}/stream`, { replay_limit: replayLimit })}`;
}

export const tesApi = {
  health: () => apiFetch<HealthResponse>("/health"),
  listBenchmarks: () => apiFetch<BenchmarkRun[]>("/benchmarks"),
  getLatestBenchmark: () => apiFetch<BenchmarkRun>("/benchmarks/latest"),
  compareBenchmarks: (request: BenchmarkCompareRequest) =>
    apiFetch<BenchmarkComparison>("/benchmarks/compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    }),
  getLatestRegressions: (threshold_percent = 10) =>
    apiFetch<BenchmarkComparison>(appendQuery("/benchmarks/regressions", { threshold_percent })),
  listRuns: () => apiFetch<RunSummary[]>("/runs"),
  generateDemoRun: () => apiFetch<RunDetail>("/sessions/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      scenario: "calm_market",
      steps: 8,
      symbols: ["DEFAULT"],
      seed: 42,
      initial_price: 100,
      volatility: 0.02,
      participants: 6,
      depth_levels: 3,
      initial_cash: 1_000_000,
      mode: "sync",
    }),
  }),
  listWorkers: () => apiFetch<WorkerSummary[]>("/workers"),
  getSchedulerStatus: () => apiFetch<SchedulerStatus>("/scheduler/status"),
  requeueStale: () => apiFetch<RequeueStaleResponse>("/scheduler/requeue-stale", { method: "POST" }),
  getRun: (runId: string) => apiFetch<RunDetail>(`/runs/${encodeURIComponent(runId)}`),
  verifyRun: (runId: string) =>
    apiFetch<ReplayVerificationReport>(`/runs/${encodeURIComponent(runId)}/verify`, { method: "POST" }),
  getVerification: (runId: string) =>
    apiFetch<ReplayVerificationReport>(`/runs/${encodeURIComponent(runId)}/verification`),
  diffRuns: (request: RunDiffRequest) =>
    apiFetch<RunDiffResult>("/runs/diff", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    }),
  getReplay: (runId: string) => apiFetch<ReplaySessionResponse>(`/runs/${encodeURIComponent(runId)}/replay`),
  getReplayFrame: (runId: string, step: number, symbol?: string) =>
    apiFetch<ReplayFrame>(appendQuery(`/runs/${encodeURIComponent(runId)}/replay/frame/${step}`, { symbol })),
  getReplayRange: (runId: string, query?: ReplayRangeQuery) =>
    apiFetch<ReplayRangeResponse>(appendQuery(`/runs/${encodeURIComponent(runId)}/replay/range`, query)),
  getReplaySummary: (runId: string) => apiFetch<ReplaySummaryResponse>(`/runs/${encodeURIComponent(runId)}/replay/summary`),
  getReport: (runId: string) => apiFetch<ReportResponse>(`/runs/${encodeURIComponent(runId)}/report`),
  getTimeline: (runId: string, query?: TimelineQuery) =>
    apiFetch<TimelineResponse>(appendQuery(`/runs/${encodeURIComponent(runId)}/timeline`, query)),
  getEvents: (runId: string, query?: CollectionQuery) =>
    apiFetch<EventsResponse>(appendQuery(`/runs/${encodeURIComponent(runId)}/events`, query)),
  getSnapshots: (runId: string, query?: CollectionQuery) =>
    apiFetch<SnapshotsResponse>(appendQuery(`/runs/${encodeURIComponent(runId)}/snapshots`, query)),
  getAccounts: (runId: string, query?: CollectionQuery) =>
    apiFetch<AccountsResponse>(appendQuery(`/runs/${encodeURIComponent(runId)}/accounts`, query)),
  getLogs: (runId: string, query?: CollectionQuery) =>
    apiFetch<LogsResponse>(appendQuery(`/runs/${encodeURIComponent(runId)}/logs`, query)),
  cancelRun: (runId: string) =>
    apiFetch<RunDetail>(`/runs/${encodeURIComponent(runId)}/cancel`, { method: "POST" }),
  listTournaments: () => apiFetch<TournamentRun[]>("/tournaments"),
  getTournament: (tournamentId: string) => apiFetch<TournamentRun>(`/tournaments/${encodeURIComponent(tournamentId)}`),
  getTournamentReport: (tournamentId: string) =>
    apiFetch<TournamentReport>(`/tournaments/${encodeURIComponent(tournamentId)}/report`),
  getTournamentChildren: (tournamentId: string) =>
    apiFetch<TournamentChildrenResponse>(`/tournaments/${encodeURIComponent(tournamentId)}/children`),
  cancelTournament: (tournamentId: string) =>
    apiFetch<TournamentRun>(`/tournaments/${encodeURIComponent(tournamentId)}/cancel`, { method: "POST" }),
};
