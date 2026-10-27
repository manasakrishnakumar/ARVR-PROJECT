import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const authState = { user: null as null | { username: string }, loading: false, setUser: vi.fn(), signOut: vi.fn() };
vi.mock("../context/AuthContext", () => ({ useAuth: () => authState }));
vi.mock("../hooks/useExercises", () => ({ useExercises: () => ({ exercises: [], error: null, loading: false }) }));
vi.mock("../services/api", async (orig) => {
  const real = await orig<typeof import("../services/api")>();
  return { ...real, api: { ...real.api, progress: vi.fn(), summary: vi.fn(), researchResults: vi.fn(), sessionDetail: vi.fn() } };
});

import { api } from "../services/api";
import Dashboard from "./Dashboard";
import Research from "./Research";

const wrap = (ui: React.ReactElement) => render(<MemoryRouter>{ui}</MemoryRouter>);
beforeEach(() => { authState.user = null; vi.clearAllMocks(); });

describe("Dashboard", () => {
  it("asks guests to sign in and says guest sessions are not saved", () => {
    wrap(<Dashboard />);
    expect(screen.getByText(/Sign in to see your saved sessions/)).toBeInTheDocument();
    expect(api.progress).not.toHaveBeenCalled(); // no data request without an account
  });

  it("shows an empty state, not fake data, for a new user", async () => {
    authState.user = { username: "ann" };
    vi.mocked(api.progress).mockResolvedValue({ points: [], note: "" });
    vi.mocked(api.summary).mockResolvedValue({ total_sessions: 0, demo_sessions_included: false, completed_repetitions: 0, average_quality_score: null,
      total_duration_s: 0, error_categories: {}, sessions_by_exercise: {}, note: "", disclaimer: "" });
    wrap(<Dashboard />);
    expect(await screen.findByText(/No saved sessions yet/)).toBeInTheDocument();
    expect(screen.getByText(/not validated medical outcomes/i)).toBeInTheDocument();
  });

  it("shows totals and a session row with a link when data exists", async () => {
    authState.user = { username: "ann" };
    vi.mocked(api.progress).mockResolvedValue({ note: "", points: [{
      session_id: "abc", exercise_id: "elbow_flexion", started_at: "2026-10-27T10:00:00Z", is_demo: false, level: 2, counted_reps: 9, target_reps: 8,
      quality: 0.93, error_rate: 0.1, duration_s: 120, mean_rom_deg: 94, classification: "good", action: "maintain", next_level: 2 }] });
    vi.mocked(api.summary).mockResolvedValue({ total_sessions: 1, demo_sessions_included: false, completed_repetitions: 9, average_quality_score: 0.93,
      total_duration_s: 120, error_categories: { too_fast: 1 }, sessions_by_exercise: { elbow_flexion: 1 }, note: "", disclaimer: "" });
    wrap(<Dashboard />);
    expect(await screen.findByText("0.93", { selector: "strong" })).toBeInTheDocument();
    expect(screen.getByText("2 min")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Details" })).toHaveAttribute("href", "/sessions/abc");
  });

  it("shows the error instead of a blank page when loading fails", async () => {
    authState.user = { username: "ann" };
    vi.mocked(api.progress).mockRejectedValue(new Error("boom"));
    vi.mocked(api.summary).mockRejectedValue(new Error("boom"));
    wrap(<Dashboard />);
    expect(await screen.findByRole("alert")).toHaveTextContent("boom");
  });
});

describe("Research page", () => {
  it("flags synthetic results prominently and renders simulation, counting and angle results", async () => {
    vi.mocked(api.researchResults).mockResolvedValue({ note: "", results: [
      { id: "s", kind: "synthetic", title: "Pipeline check on SYNTHETIC data", caveat: "c", data: {
        _sizes: { train_rows: 10, test_rows: 5, train_participants: 3, test_participants: 2 },
        majority_class: { accuracy: 0.2, macro_f1: 0.1 }, rule_based: { accuracy: 0.8, macro_f1: 0.8 }, random_forest: { accuracy: 0.9, macro_f1: 0.9 } } },
      { id: "c", kind: "counting", title: "Counting", caveat: "c", data: { "DS": { auto: { labelled_repetitions: 10, detected_repetitions: 10,
        mean_absolute_count_error: 0.1, exact_count_fraction: 0.9, precision: 0.9, recall: 0.9, f1: 0.9 } } } },
      { id: "a", kind: "angle", title: "Angle accuracy", caveat: "c", data: { recordings: 2, best_lag_frames_median: 0, note: "n", by_exercise: {}, by_camera: {},
        overall: { n: 100, mae_deg: 8, rmse_deg: 14, bias_deg: -2, loa95_deg: [-20, 16], pearson_r: 0.97 } } },
      { id: "m", kind: "simulation", title: "Simulation", caveat: "c", data: { n_users_per_model: 5, n_sessions: 10, models: { stable: {
        best_fixed_by_mismatch: "fixed_level_1", safety_violations_total: 0, adaptive_minus_best_fixed_mismatch_share: { mean: -0.2, ci95: [-0.3, -0.1] },
        policies: { adaptive: { too_hard_share: 0.1, too_easy_share: 0.1, mismatch_share: 0.2, level_changes: 2, direction_reversals: 1, pause_share: 0 } } } } } },
    ] });
    wrap(<Research />);
    expect(await screen.findByText(/SYNTHETIC DATA ONLY/)).toBeInTheDocument();
    expect(screen.getByText(/^SIMULATION\./)).toBeInTheDocument();
    expect(screen.getByText("8.000")).toBeInTheDocument(); // MAE
    expect(screen.getByText(/Nothing here shows that the system, or adaptive difficulty, improves recovery/)).toBeInTheDocument();
  });

  it("handles no result files and a failing request", async () => {
    vi.mocked(api.researchResults).mockResolvedValueOnce({ note: "", results: [] });
    const { unmount } = wrap(<Research />);
    expect(await screen.findByText(/No result files found/)).toBeInTheDocument();
    unmount();
    vi.mocked(api.researchResults).mockRejectedValueOnce(new Error("offline"));
    wrap(<Research />);
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("offline"));
  });
});
