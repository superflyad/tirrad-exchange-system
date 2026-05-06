import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { TimelineViewer } from "./TimelineViewer";
import type { TimelineEntry } from "@/types/api";

const entries: TimelineEntry[] = [
  { sequence: 1, step: 1, timestamp: null, symbol: "TES", category: "event", type: "TradeExecuted", summary: "trade", payload: { symbol: "TES", price: 101 } },
  { sequence: 2, step: 2, timestamp: null, symbol: "ALT", category: "snapshot", type: "TopOfBook", summary: "book", payload: { symbol: "ALT" } },
];

describe("TimelineViewer", () => {
  it("renders and filters timeline entries", async () => {
    render(<TimelineViewer entries={entries} />);
    expect(screen.getByText("trade")).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("Symbol"), "ALT");
    expect(screen.queryByText("trade")).not.toBeInTheDocument();
    expect(screen.getByText("book")).toBeInTheDocument();
  });
});
