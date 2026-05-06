import { afterEach, describe, expect, it, vi } from "vitest";

import { tesApi, streamRunUrl } from "./client";

describe("tesApi", () => {
  afterEach(() => vi.restoreAllMocks());

  it("fetches runs through the configured API layer", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify([{ run_id: "run-1" }]), { status: 200 }));

    const runs = await tesApi.listRuns();

    expect(runs).toEqual([{ run_id: "run-1" }]);
    expect(fetchMock).toHaveBeenCalledWith("/api/tes/runs", expect.objectContaining({ headers: { Accept: "application/json" } }));
  });

  it("builds stream URLs with replay limits", () => {
    expect(streamRunUrl("abc/123", 25)).toBe("/api/tes/runs/abc%2F123/stream?replay_limit=25");
  });
});
