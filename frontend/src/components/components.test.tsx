import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { CompleteOut } from "../types/api";

const authState = { user: null as null | { username: string }, loading: false, setUser: vi.fn(), signOut: vi.fn() };
vi.mock("../context/AuthContext", () => ({ useAuth: () => authState }));
vi.mock("../services/api", async (orig) => {
  const real = await orig<typeof import("../services/api")>();
  return { ...real, api: { ...real.api, health: vi.fn(), checkin: vi.fn(), login: vi.fn(), register: vi.fn() } };
});

import { api } from "../services/api";
import AccountPanel from "./AccountPanel";
import Layout from "./Layout";
import RecommendationCard from "./RecommendationCard";

const result = (over: Partial<CompleteOut> = {}): CompleteOut => ({
  saved_to_history: false, history_used: false,
  recommendation: {
    action: "maintain", current_level: 1, next_level: 1, target_reps: 5, range_fraction: 0.6, min_rep_duration_s: 1.5,
    feedback_intensity: "low", classification: "good", reasons: ["Good session. 1 of 2 confirming sessions needed."],
    safety_note: "Software suggestion, not a clinical decision.",
    metrics: { n_reps: 6, n_reliable: 6, counted_reps: 6, target_reps: 5, quality: 0.95, error_rate: 0, completion: 1.2, range_std: 0.02, reliable_fraction: 1 },
  }, ...over,
});

beforeEach(() => { authState.user = null; vi.clearAllMocks(); });

describe("RecommendationCard", () => {
  it("shows the suggestion, reasons, targets, metrics and safety note", () => {
    render(<RecommendationCard result={result()} />);
    expect(screen.getByText(/keep the same level: level 1/i)).toBeInTheDocument();
    expect(screen.getByText(/1 of 2 confirming sessions/)).toBeInTheDocument();
    expect(screen.getByText(/5 repetitions, reach at least 60%/)).toBeInTheDocument();
    expect(screen.getByText(/6\/5 repetitions counted/)).toBeInTheDocument();
    expect(screen.getByText(/not a clinical decision/i)).toBeInTheDocument();
  });

  it("says when a session was not saved to any history, and when it was", () => {
    const { rerender } = render(<RecommendationCard result={result()} />);
    expect(screen.getByText(/Not saved to any history/)).toBeInTheDocument();
    rerender(<RecommendationCard result={result({ saved_to_history: true, history_used: true })} />);
    expect(screen.getByText(/Saved to your adaptive history/)).toBeInTheDocument();
  });

  it("shows the level change when the suggestion differs from the level played", () => {
    const r = result();
    r.recommendation = { ...r.recommendation, action: "increase", next_level: 2 };
    render(<RecommendationCard result={r} />);
    expect(screen.getByText(/a small step up: level 2 \(was 1\)/i)).toBeInTheDocument();
  });
});

describe("RecommendationCard pain check-in", () => {
  it("is hidden without a session id", () => {
    render(<RecommendationCard result={result()} />);
    expect(screen.queryByLabelText("Pain check-in")).toBeNull();
  });

  it("sends the pain report and shows the updated, more cautious suggestion", async () => {
    const paused = result();
    paused.recommendation = { ...paused.recommendation, action: "pause", reasons: ["You reported pain 8/10. Stop for now."] };
    vi.mocked(api.checkin).mockResolvedValue(paused);
    render(<RecommendationCard result={result()} sessionId="s1" />);
    fireEvent.change(screen.getByLabelText("Pain from 0 to 10"), { target: { value: "8" } });
    await userEvent.click(screen.getByRole("button", { name: /save check-in/i }));
    await waitFor(() => expect(api.checkin).toHaveBeenCalledWith("s1", 8, ""));
    expect(await screen.findByText(/take a break/i)).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(/pain report/i);
  });
});

describe("AccountPanel", () => {
  it("explains guest mode and signs in with the entered credentials", async () => {
    vi.mocked(api.login).mockResolvedValue({ token: "t", user: { id: "1", username: "ann", age_range: null, goals: null, preferences: {}, created_at: "" } });
    const done = vi.fn();
    render(<AccountPanel onDone={done} />);
    expect(screen.getByText(/Guest mode needs no account/i)).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Username"), "ann");
    await userEvent.type(screen.getByLabelText("Password"), "pw-12345678");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => expect(done).toHaveBeenCalled());
    expect(api.login).toHaveBeenCalledWith("ann", "pw-12345678");
    expect(authState.setUser).toHaveBeenCalled();
  });

  it("shows the server's error and does not navigate when sign-in fails", async () => {
    vi.mocked(api.login).mockRejectedValue(new Error("Incorrect username or password"));
    const done = vi.fn();
    render(<AccountPanel onDone={done} />);
    await userEvent.type(screen.getByLabelText("Username"), "ann");
    await userEvent.type(screen.getByLabelText("Password"), "wrong-password");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Incorrect username or password");
    expect(done).not.toHaveBeenCalled();
  });

  it("switches to account creation", async () => {
    render(<AccountPanel />);
    await userEvent.click(screen.getByRole("button", { name: /Need an account/ }));
    expect(screen.getByRole("button", { name: "Create account" })).toBeInTheDocument();
  });
});

describe("Layout", () => {
  it("always shows the safety banner and shows the backend-down banner when health fails", async () => {
    vi.mocked(api.health).mockRejectedValue(new Error("down"));
    render(<MemoryRouter><Layout /></MemoryRouter>);
    expect(screen.getByText(/Not a medical device/i)).toBeInTheDocument();
    expect(await screen.findByText(/Cannot reach the backend/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Guest · sign in/ })).toBeInTheDocument();
  });

  it("uses the backend's disclaimer text and the signed-in username", async () => {
    authState.user = { username: "ann" };
    vi.mocked(api.health).mockResolvedValue({ status: "ok", version: "1", disclaimer: "Backend disclaimer text." });
    render(<MemoryRouter><Layout /></MemoryRouter>);
    expect(await screen.findByText("Backend disclaimer text.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "ann" })).toBeInTheDocument();
  });
});

describe("Layout display options", () => {
  it("toggles large text and high contrast on the document", async () => {
    vi.mocked(api.health).mockResolvedValue({ status: "ok", disclaimer: "d" } as never);
    render(<MemoryRouter><Layout /></MemoryRouter>);
    await userEvent.click(screen.getByRole("button", { name: "A+" }));
    expect(document.documentElement.dataset.text).toBe("large");
    await userEvent.click(screen.getByRole("button", { name: "Contrast" }));
    expect(document.documentElement.dataset.contrast).toBe("high");
    await userEvent.click(screen.getByRole("button", { name: "Contrast" }));
    expect(document.documentElement.dataset.contrast).toBe("normal");
  });
});
