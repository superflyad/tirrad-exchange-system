import { describe, expect, it } from "vitest";

import { deriveStreamState } from "./useRunStream";
import type { StreamMessage } from "@/types/api";

const messages: StreamMessage[] = [
  { run_id: "run-1", timestamp: "2026-01-01T00:00:00Z", step: 1, category: "progress", type: "progress", payload: {} },
  { run_id: "run-1", timestamp: "2026-01-01T00:00:01Z", step: 2, category: "event", type: "TradeExecuted", payload: { symbol: "TES", price: 101 } },
];

describe("deriveStreamState", () => {
  it("derives monitor metrics from stream messages", () => {
    expect(deriveStreamState(messages, "open", null)).toMatchObject({
      currentStep: 2,
      tradeCount: 1,
      latestPrices: { TES: 101 },
      connectionState: "open",
    });
  });
});
