import { afterEach, describe, expect, it, vi } from "vitest";

import { tesApi, streamRunUrl } from "./client";

describe("tesApi", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("fetches runs through the configured API layer", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify([{ run_id: "run-1" }]), { status: 200 }));

    const runs = await tesApi.listRuns();

    expect(runs).toEqual([{ run_id: "run-1" }]);
    expect(fetchMock).toHaveBeenCalledWith("/api/tes/runs", expect.objectContaining({ headers: { Accept: "application/json" } }));
  });

  it("uses TES_API_ORIGIN for server-side relative API requests", async () => {
    vi.stubGlobal("window", undefined);
    vi.stubEnv("TES_API_ORIGIN", "http://127.0.0.1:8123");
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ status: "ok" }), { status: 200 }));

    await tesApi.health();

    expect(fetchMock).toHaveBeenCalledWith("http://127.0.0.1:8123/health", expect.objectContaining({ headers: { Accept: "application/json" } }));
  });

  it("builds stream URLs with replay limits", () => {
    expect(streamRunUrl("abc/123", 25)).toBe("/api/tes/runs/abc%2F123/stream?replay_limit=25");
  });
});
