import { describe, expect, it } from "vitest";
import { detectVr, hudText, VR_ROOM_OFFSET } from "./xr";

describe("detectVr", () => {
  it("is unsupported when the browser has no WebXR", async () => {
    expect(await detectVr({})).toBe("unsupported");
    expect(await detectVr({ xr: {} })).toBe("unsupported");
  });
  it("reports what the browser says and asks about immersive-vr", async () => {
    let asked = "";
    const nav = (ok: boolean) => ({ xr: { isSessionSupported: async (m: string) => { asked = m; return ok; } } });
    expect(await detectVr(nav(true))).toBe("supported");
    expect(asked).toBe("immersive-vr");
    expect(await detectVr(nav(false))).toBe("unsupported");
  });
  it("treats an error as unsupported", async () => {
    expect(await detectVr({ xr: { isSessionSupported: async () => { throw new Error("blocked"); } } })).toBe("unsupported");
  });
});

describe("VR placement and panel text", () => {
  it("puts the room in front of the user and lifts the desktop floor to the real floor", () => {
    expect(VR_ROOM_OFFSET[2]).toBeLessThan(0);
    expect(VR_ROOM_OFFSET[1]).toBeCloseTo(0.9);
  });
  it("builds the panel lines and omits empty feedback", () => {
    expect(hudText(3, 5, "mid_rep", "")).toEqual(["3/5 reps", "mid rep"]);
    expect(hudText(0, 0, "waiting", "Go further")).toEqual(["0/- reps", "waiting", "Go further"]);
  });
});
