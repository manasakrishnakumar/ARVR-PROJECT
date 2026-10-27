import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, ApiError, tokenStore } from "./api";

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

beforeEach(() => { localStorage.clear(); });
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("tokenStore", () => {
  it("stores and clears a token", () => {
    tokenStore.set("abc");
    expect(tokenStore.get()).toBe("abc");
    tokenStore.set(null);
    expect(tokenStore.get()).toBeNull();
  });

  it("does not throw when browser storage is unavailable", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => { throw new Error("blocked"); });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("blocked"); });
    expect(tokenStore.get()).toBeNull();
    expect(() => tokenStore.set("x")).not.toThrow();
  });
});

describe("request handling", () => {
  it("sends the bearer token and JSON content type", async () => {
    tokenStore.set("tok");
    const fetchMock = vi.fn().mockResolvedValue(json({ username: "a" }));
    vi.stubGlobal("fetch", fetchMock);
    await api.updateMe({ goals: "x" });
    const [, init] = fetchMock.mock.calls[0];
    expect((init.headers as Headers).get("Authorization")).toBe("Bearer tok");
    expect((init.headers as Headers).get("Content-Type")).toBe("application/json");
  });

  it("turns error responses into ApiError with the server's message (string or validation list)", async () => {
    vi.stubGlobal("fetch", vi.fn()
      .mockResolvedValueOnce(json({ detail: "Incorrect username or password" }, 401))
      .mockResolvedValueOnce(json({ detail: [{ msg: "too short" }, { msg: "bad name" }] }, 422))
      .mockResolvedValueOnce(new Response("<html>oops</html>", { status: 500 })));
    await expect(api.login("a", "b")).rejects.toMatchObject({ status: 401, message: "Incorrect username or password" });
    await expect(api.register("a", "b")).rejects.toMatchObject({ status: 422, message: "too short; bad name" });
    const e = await api.me().catch((x) => x);
    expect(e).toBeInstanceOf(ApiError);
    expect(e.status).toBe(500);
  });

  it("handles 204 responses without trying to parse a body", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 204 })));
    await expect(api.deleteMe()).resolves.toBeUndefined();
  });

  it("builds filter query strings and leaves out empty filters", async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(json({ points: [], note: "" }))); // a fresh Response per call
    vi.stubGlobal("fetch", fetchMock);
    await api.progress({ exercise_id: "knee_flexion", from: "2026-01-01", include_demo: true });
    expect(fetchMock.mock.calls[0][0]).toBe("/api/analytics/progress?exercise_id=knee_flexion&from=2026-01-01&include_demo=true");
    await api.progress({});
    expect(fetchMock.mock.calls[1][0]).toBe("/api/analytics/progress");
  });
});
