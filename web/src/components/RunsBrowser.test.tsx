import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { RunsBrowser } from "./RunsBrowser";
import { tesApi } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({
  tesApi: {
    listRuns: vi.fn(),
    listWorkers: vi.fn(),
    generateDemoRun: vi.fn(),
  },
}));

describe("RunsBrowser", () => {
  it("shows the empty run list state", async () => {
    vi.mocked(tesApi.listRuns).mockResolvedValue([]);
    vi.mocked(tesApi.listWorkers).mockResolvedValue([]);

    render(<RunsBrowser />);

    expect(await screen.findByText("No runs yet. Generate demo run.")).toBeInTheDocument();
  });

  it("shows populated run list rows", async () => {
    vi.mocked(tesApi.listRuns).mockResolvedValue([
      { run_id: "run-1", run_type: "session", status: "completed", created_at: "2026-01-01T00:00:00Z", started_at: null, completed_at: null, config: { symbols: ["TES"] }, report_summary: {}, error: null, scenario: "calm_market", strategy: null, step_count: 8, trade_count: 2, rejection_count: 0 },
    ]);
    vi.mocked(tesApi.listWorkers).mockResolvedValue([]);

    render(<RunsBrowser />);

    expect(await screen.findByText("run-1")).toBeInTheDocument();
    expect(screen.getByText("calm_market")).toBeInTheDocument();
  });

  it("generates a demo run and refreshes the list", async () => {
    vi.mocked(tesApi.listRuns)
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([
        { run_id: "run-demo", run_type: "session", status: "completed", created_at: "2026-01-01T00:00:00Z", started_at: null, completed_at: null, config: {}, report_summary: {}, error: null, scenario: "calm_market", strategy: null, step_count: 8, trade_count: 1, rejection_count: 0 },
      ]);
    vi.mocked(tesApi.listWorkers).mockResolvedValue([]);
    vi.mocked(tesApi.generateDemoRun).mockResolvedValue({ run_id: "run-demo" } as never);

    render(<RunsBrowser />);
    await userEvent.click(await screen.findByRole("button", { name: "Generate Demo Run" }));

    await waitFor(() => expect(tesApi.generateDemoRun).toHaveBeenCalled());
    expect(await screen.findByText("run-demo")).toBeInTheDocument();
  });

  it("shows an unreachable API message", async () => {
    vi.mocked(tesApi.listRuns).mockRejectedValue(new Error("TES API is unreachable"));
    vi.mocked(tesApi.listWorkers).mockResolvedValue([]);

    render(<RunsBrowser />);

    expect(await screen.findByRole("alert")).toHaveTextContent("TES API is unreachable");
  });
});
