import { beforeEach, describe, expect, it } from "vitest";
import { applyPrefs, loadPrefs, savePrefs } from "./a11y";

beforeEach(() => localStorage.clear());

describe("display preferences", () => {
  it("defaults to off, round-trips, and ignores corrupt storage", () => {
    expect(loadPrefs()).toEqual({ largeText: false, highContrast: false });
    savePrefs({ largeText: true, highContrast: true });
    expect(loadPrefs()).toEqual({ largeText: true, highContrast: true });
    localStorage.setItem("arvr.display", "{not json");
    expect(loadPrefs()).toEqual({ largeText: false, highContrast: false });
  });
  it("sets data attributes the stylesheet reacts to", () => {
    const el = document.createElement("div");
    applyPrefs({ largeText: true, highContrast: false }, el);
    expect(el.dataset.text).toBe("large");
    expect(el.dataset.contrast).toBe("normal");
  });
});
