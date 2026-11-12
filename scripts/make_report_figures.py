"""Draws the two figures used in docs/ARVR_Project_Report.docx from the project's real result numbers.
Run:  python scripts/make_report_figures.py   (needs matplotlib)"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "screenshots"
NAVY, BLUE, LIGHT = "#1A5376", "#2E74B5", "#EBF5FB"


def box(ax, x, y, w, h, text, fill=LIGHT, edge=NAVY, color="#14202b", size=9):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fill, ec=edge, lw=1.4))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size, color=color, wrap=True)


def arrow(ax, x1, y1, x2, y2, label=None, at=None):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="-|>", color=NAVY, lw=1.4))
    if label:
        lx, ly = at or ((x1 + x2) / 2, (y1 + y2) / 2)
        ax.text(lx, ly, label, fontsize=7.5, color=BLUE, ha="center", va="center", bbox=dict(fc="white", ec="none", pad=1.5))


def architecture() -> None:
    fig, ax = plt.subplots(figsize=(9.2, 5.6))
    ax.set_xlim(0, 10); ax.set_ylim(0, 6.2); ax.axis("off")
    ax.text(2.2, 5.95, "Browser (React + TypeScript)", fontsize=10, color=NAVY, weight="bold", ha="center")
    ax.text(7.7, 5.95, "Backend (FastAPI + Python, local)", fontsize=10, color=NAVY, weight="bold", ha="center")
    ax.plot([5.0, 5.0], [0.2, 5.8], ls="--", color="#9aa8b3", lw=1)
    box(ax, 0.4, 4.7, 3.6, 0.7, "Webcam  or  synthetic demo figure")
    box(ax, 0.4, 3.6, 3.6, 0.7, "Pose estimation in the browser\n(MediaPipe Pose Landmarker, CPU)")
    box(ax, 0.4, 2.5, 3.6, 0.7, "Landmark validation +\n2D joint angle (confidence-gated)")
    box(ax, 0.4, 0.4, 3.6, 1.5, "Pages: Live session, Pose analysis,\nAR overlay, 3D room, Dashboard,\nResearch, Record data, Settings", fill="#ffffff")
    box(ax, 5.5, 4.7, 4.0, 0.7, "StreamAnalyzer: smoothing +\nrepetition counter (state machine)")
    box(ax, 5.5, 3.6, 4.0, 0.7, "Rule-based assessment\n(range, pace, control, reliability)")
    box(ax, 5.5, 2.5, 4.0, 0.7, "SQLite: users, sessions,\nrepetitions, decisions")
    box(ax, 5.5, 1.4, 4.0, 0.7, "Adaptive controller\n(hysteresis, pain rule, reasons)")
    box(ax, 5.5, 0.3, 4.0, 0.7, "Recommendation: next level,\ntargets, plain-language reasons", fill="#D9E2F3")
    arrow(ax, 2.2, 4.7, 2.2, 4.3); arrow(ax, 2.2, 3.6, 2.2, 3.2)
    arrow(ax, 4.0, 2.85, 5.5, 4.95, "angle + time\n~15 Hz (WebSocket)", at=(4.75, 3.2))
    arrow(ax, 7.5, 4.7, 7.5, 4.3); arrow(ax, 7.5, 3.6, 7.5, 3.2); arrow(ax, 7.5, 2.5, 7.5, 2.1); arrow(ax, 7.5, 1.4, 7.5, 1.0)
    arrow(ax, 5.5, 0.65, 4.0, 1.1, "results\nback to UI", at=(4.75, 0.55))
    ax.text(5.0, 0.0, "No video leaves the browser: only joint-angle numbers go to the backend on the same computer.", fontsize=8, ha="center", color="#55656f")
    fig.savefig(OUT / "fig-architecture.png", dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def results() -> None:
    labels = ["Angle only\n(external)", "All features\n(external)", "Tuned threshold\n(external)", "In-domain\n(leave one person out)"]
    vals = [0.49, 0.61, 0.686, 0.72]
    colors = ["#9aa8b3", BLUE, NAVY, "#4a9d7a"]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    bars = ax.bar(labels, vals, color=colors, width=0.6)
    ax.axhline(0.5, color="#b42318", ls="--", lw=1.2); ax.text(-0.45, 0.455, "chance = 0.50", color="#b42318", fontsize=8, ha="left")
    ax.errorbar([2], [0.686], yerr=[[0.686 - 0.625], [0.761 - 0.686]], fmt="none", ecolor="black", capsize=5, lw=1.3)
    for b, v in zip(bars, vals):
        top = 0.761 if v == 0.686 else v
        ax.text(b.get_x() + b.get_width() / 2, top + 0.012, f"{v:.3g}", ha="center", fontsize=9, weight="bold")
    ax.set_ylim(0.4, 0.82); ax.set_ylabel("Balanced accuracy"); ax.spines[["top", "right"]].set_visible(False)
    ax.set_title("Movement-quality classification: train on REHAB26, test on REHAB24-6", fontsize=10, color=NAVY)
    fig.text(0.5, -0.02, "Bar with whisker: 95% confidence interval over participants (0.625 to 0.761). Source: docs/results/external-mocap.json", ha="center", fontsize=7.5, color="#55656f")
    fig.savefig(OUT / "fig-results.png", dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def counting() -> None:
    d = json.loads((ROOT / "docs" / "results" / "counting.json").read_text(encoding="utf8"))
    print("counting.json keys:", list(d)[:8])


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    architecture(); results(); counting()
    print("wrote fig-architecture.png and fig-results.png")
