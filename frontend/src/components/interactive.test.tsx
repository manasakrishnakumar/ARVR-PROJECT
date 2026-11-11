import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { describe, expect, it } from "vitest";
import CommandPalette from "./CommandPalette";
import { CountUp } from "./Fx";
import MoveDemo from "./MoveDemo";
import { applyTheme, nextTheme } from "../motion";

const slide = (v: number) => fireEvent.change(screen.getByLabelText("Arm angle in degrees"), { target: { value: String(v) } });

describe("MoveDemo", () => {
  it("counts a repetition only after reaching the target and coming back down", () => {
    render(<MoveDemo />);
    expect(screen.getByText("0/5")).toBeInTheDocument();
    slide(60); slide(10);                       // never reached 90: no repetition
    expect(screen.getByText("0/5")).toBeInTheDocument();
    slide(95); expect(screen.getByText("0/5")).toBeInTheDocument(); // up, not yet back
    slide(10); expect(screen.getByText("1/5")).toBeInTheDocument();
    slide(95); slide(60);                       // hysteresis: still above the return threshold
    expect(screen.getByText("1/5")).toBeInTheDocument();
  });
  it("resets", () => {
    render(<MoveDemo />);
    slide(100); slide(5);
    fireEvent.click(screen.getByRole("button", { name: "Reset" }));
    expect(screen.getByText("0/5")).toBeInTheDocument();
  });
});

describe("CountUp", () => {
  it("shows the final value at once when motion is unavailable", () => {
    render(<CountUp value={42} />);
    expect(screen.getByText("42")).toBeInTheDocument();
  });
});

describe("CommandPalette", () => {
  function Where() { return <p data-testid="where">{useLocation().pathname}</p>; }
  it("opens with Ctrl+K, filters, and navigates on Enter", () => {
    let open = false;
    const App = () => (
      <MemoryRouter><Where />
        <Routes><Route path="*" element={<CommandPalette open={open} onOpen={() => { open = true; }} onClose={() => { open = false; }} />} /></Routes>
      </MemoryRouter>
    );
    const { rerender } = render(<App />);
    fireEvent.keyDown(window, { key: "k", ctrlKey: true });
    rerender(<App />);
    const box = screen.getByLabelText("Search pages");
    fireEvent.change(box, { target: { value: "dash" } });
    expect(screen.getAllByRole("button").map((b) => b.textContent)).toEqual(["Dashboard/dashboard"]);
    fireEvent.keyDown(box, { key: "Enter" });
    expect(screen.getByTestId("where")).toHaveTextContent("/dashboard");
  });
});

describe("theme helpers", () => {
  it("cycles auto, light, dark and applies the attribute", () => {
    expect(nextTheme("auto")).toBe("light"); expect(nextTheme("light")).toBe("dark"); expect(nextTheme("dark")).toBe("auto");
    const el = document.createElement("div");
    applyTheme("dark", el); expect(el.dataset.theme).toBe("dark");
    applyTheme("auto", el); expect(el.dataset.theme).toBeUndefined();
  });
});
