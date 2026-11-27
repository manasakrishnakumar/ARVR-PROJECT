import { render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import ErrorBoundary from "../components/ErrorBoundary";
import { api } from "../services/api";
import unity from "../../../docs/results/unity-pose.json";
import Research from "./Research";

afterEach(() => { vi.restoreAllMocks(); });

test("shows the Unity pose validation result and survives an unknown result type", async () => {
  vi.spyOn(api, "researchResults").mockResolvedValue({ results: [
    { id: "unity-pose", ...unity },
    { id: "x", kind: "something-new", title: "A new result", caveat: "c", data: {} },
  ] } as never);
  render(<Research />);
  expect(await screen.findByText("Unity (BlazePose)")).toBeTruthy();
  expect(screen.getByText(/no table view yet/)).toBeTruthy();
});

test("the error boundary replaces a crashing page with a message", () => {
  vi.spyOn(console, "error").mockImplementation(() => {});
  const Broken = (): never => { throw new Error("boom"); };
  render(<ErrorBoundary><Broken /></ErrorBoundary>);
  expect(screen.getByRole("alert").textContent).toContain("could not be shown");
});
