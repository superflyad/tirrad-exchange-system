import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ReplayViewer } from "./ReplayViewer";
import { tesApi } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({
  tesApi: {
    getReplay: vi.fn(),
    getReplaySummary: vi.fn(),
    getReplayRange: vi.fn(),
    getTimeline: vi.fn(),
  },
}));

const frame = {
  step: 1,
  timestamp: null,
  symbols: ["TES"],
  symbol: "TES",
  trades: [{ trade_id: "t1", symbol: "TES", price: 101, qty: 5, step: 1 }],
  snapshots: [],
  top_of_book: { TES: { bid: 100, ask: 102, bid_qty: 10, ask_qty: 8, spread: 2, mid: 101, imbalance: 0.111 } },
  account_deltas: [{ account_id: "acct-1", cash: 1000, pnl: 5, equity: 1005, exposure: 505, leverage: 0.5 }],
  accounts: [],
  market_metrics: { volume: 5, trade_count: 1 },
  event_summaries: [],
};

describe("ReplayViewer", () => {
  it("renders playback controls and supports scrubbing", async () => {
    vi.mocked(tesApi.getReplay).mockResolvedValue({
      run_id: "run-1",
      cursor: { step: 1, state: "paused", speed: 1 },
      timeline: { start_step: 1, end_step: 3, steps: [1, 2, 3], total_frames: 3, event_steps: [2], symbols: ["TES"] },
      frame,
    });
    vi.mocked(tesApi.getReplaySummary).mockResolvedValue({
      run_id: "run-1",
      symbols: ["TES"],
      total_steps: 3,
      total_frames: 3,
      total_events: 1,
      total_trades: 1,
      total_snapshots: 1,
      total_accounts: 1,
      start_step: 1,
      end_step: 3,
      first_divergence_step: null,
      available_event_types: ["TradeExecuted"],
      performance_notes: [],
    });
    vi.mocked(tesApi.getReplayRange).mockResolvedValue({ run_id: "run-1", start_step: 1, end_step: 3, frames: [frame], next_start_step: null, total_frames: 1 });
    vi.mocked(tesApi.getTimeline).mockResolvedValue({ run_id: "run-1", timeline: [] });

    render(<ReplayViewer runId="run-1" />);

    expect(await screen.findByText("Play")).toBeInTheDocument();
    expect(screen.getByText("Trade tape")).toBeInTheDocument();
    await userEvent.click(screen.getByText("Next ▶"));
    await waitFor(() => expect(tesApi.getReplayRange).toHaveBeenCalled());
  });
});
