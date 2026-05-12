import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { RunsTable } from "./RunsTable";
import type { RunSummary } from "@/types/api";

const runs: RunSummary[] = [
  { run_id: "run-a", run_type: "session", status: "completed", created_at: "2026-01-01T00:00:00Z", started_at: null, completed_at: null, config: { symbols: ["TES"] }, report_summary: { total_trades: 2, total_volume: 10, total_steps: 5 }, error: null, scenario: "calm_market", strategy: null, step_count: 5, trade_count: 2, rejection_count: 0 },
  { run_id: "run-b", run_type: "backtest", status: "failed", created_at: "2026-01-02T00:00:00Z", started_at: null, completed_at: null, config: { symbols: ["ALT"] }, report_summary: { total_trades: 0, total_volume: 0 }, error: "boom", scenario: null, strategy: "crossing_taker", step_count: 0, trade_count: 0, rejection_count: 1 },
];

describe("RunsTable", () => {
  it("renders run rows and filters by symbol", async () => {
    render(<RunsTable runs={runs} />);
    expect(screen.getByText("run-a")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Filter runs"), "ALT");
    expect(screen.queryByText("run-a")).not.toBeInTheDocument();
    expect(screen.getByText("run-b")).toBeInTheDocument();
  });
});
