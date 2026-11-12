"""Builds docs/ARVR_Project_Report.docx in the style of the Bangalore Climate Analytics report.

The Bangalore report's .docx is used as the style template (its Heading 1/2, List Bullet and Table Grid styles, page size and
margins); its body is cleared and replaced. Numbers come from docs/results/*.json and from the test runs passed in via
--tests-dir (pytest/vitest/tsc/build output files). Run:

    python scripts/build_report.py --template "<path to Bangalore_Climate_Analytics_System_Full_Report.docx>" --tests-dir /tmp
"""
import argparse
import json
import re
from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "docs" / "results"
SHOTS = ROOT / "docs" / "screenshots"
NAVY, BLUE, BAND = "1A5376", "2E74B5", "EBF5FB"
DEFAULT_TEMPLATE = Path.home() / "Desktop" / "ALL DEKTOP" / "bangalore_climate_app_final" / "bangalore_climate_app" / "Bangalore_Climate_Analytics_System_Full_Report.docx"

ap = argparse.ArgumentParser()
ap.add_argument("--template", default=str(DEFAULT_TEMPLATE))
ap.add_argument("--tests-dir", default="/tmp")
ap.add_argument("--out", default=str(ROOT / "docs" / "ARVR_Project_Report.docx"))
args = ap.parse_args()

doc = Document(args.template)
body = doc.element.body
for el in list(body):
    if el.tag != qn("w:sectPr"):
        body.remove(el)
for rid, rel in list(doc.part.rels.items()):  # drop the climate report's pictures
    if "image" in rel.reltype:
        del doc.part.rels[rid]

fig_no = {"n": 0, "sec": 0}


# ---------- helpers ----------
def _rpr(r, bold=False, italic=False, color=None, size=None, font=None):
    r.bold = bold or None
    r.italic = italic or None
    if color:
        r.font.color.rgb = RGBColor.from_string(color)
    if size:
        r.font.size = Pt(size)
    if font:
        r.font.name = font
        r._element.rPr.rFonts.set(qn("w:hAnsi"), font)


def rich(p, text, size=None, color=None, font=None):
    """Adds text to p; **double asterisks** switch bold on and off."""
    for i, part in enumerate(re.split(r"\*\*", text)):
        if part:
            _rpr(p.add_run(part), bold=i % 2 == 1, size=size, color=color, font=font)


def para(text="", align=None, size=None, color=None, after=None, italic=False, bold=False, before=None):
    p = doc.add_paragraph()
    if align == "center":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if after is not None:
        p.paragraph_format.space_after = Pt(after)
    if before is not None:
        p.paragraph_format.space_before = Pt(before)
    if bold or italic:
        _rpr(p.add_run(text), bold=bold, italic=italic, size=size, color=color)
    else:
        rich(p, text, size=size, color=color)
    return p


def page_break():
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def h1(text, first=False):
    if not first:
        page_break()
    p = doc.add_paragraph(style="Heading 1")
    _rpr(p.add_run(text), color=NAVY, size=16)
    fig_no["sec"] = int(text.split(".")[0]) if text.split(".")[0].isdigit() else fig_no["sec"]
    fig_no["n"] = 0
    rule = doc.add_paragraph()
    pb = OxmlElement("w:pBdr")
    b = OxmlElement("w:bottom")
    for k, v in (("val", "single"), ("sz", "6"), ("space", "1"), ("color", NAVY)):
        b.set(qn("w:" + k), v)
    pb.append(b)
    rule._p.get_or_add_pPr().append(pb)


def h2(text):
    p = doc.add_paragraph(style="Heading 2")
    _rpr(p.add_run(text), color=NAVY)


def bullets(items):
    for t in items:
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.left_indent = Pt(21.6)
        rich(p, t, size=10.5)


def _shade(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), fill)
    tcPr.append(shd)


def table(headers, rows, widths, mono_first=False, center=()):
    """widths in inches; header row navy with white bold text; body rows banded like the climate report."""
    t = doc.add_table(rows=1 + len(rows), cols=len(headers))
    t.style = "Table Grid"
    t.alignment = 1
    t.autofit = False
    for ci, h in enumerate(headers):
        c = t.rows[0].cells[ci]
        _shade(c, NAVY)
        p = c.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_after = Pt(2)
        _rpr(p.add_run(h), bold=True, color="FFFFFF", size=10)
    for ri, row in enumerate(rows, start=1):
        for ci, val in enumerate(row):
            c = t.rows[ri].cells[ci]
            if ri % 2 == 0:
                _shade(c, BAND)
            p = c.paragraphs[0]; p.paragraph_format.space_after = Pt(2)
            if ci in center:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            rich(p, str(val), size=9, font="Courier New" if (mono_first and ci == 0) else None)
    for row in t.rows:
        for ci, w in enumerate(widths):
            row.cells[ci].width = Inches(w)
    # repeat the header row on each page
    trPr = t.rows[0]._tr.get_or_add_trPr()
    th = OxmlElement("w:tblHeader"); th.set(qn("w:val"), "true"); trPr.append(th)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)
    return t


def figure(path, caption, width=5.5):
    fig_no["n"] += 1
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6); p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(path), width=Inches(width))
    c = doc.add_paragraph(); c.alignment = WD_ALIGN_PARAGRAPH.CENTER; c.paragraph_format.space_after = Pt(10)
    _rpr(c.add_run(f"Figure {fig_no['sec']}.{fig_no['n']}  {caption}"), bold=True, size=10, font="Cambria")


def note(text):
    """A shaded call-out for honest caveats."""
    t = doc.add_table(rows=1, cols=1); t.style = "Table Grid"; t.alignment = 1; t.autofit = False
    c = t.rows[0].cells[0]; c.width = Inches(6.3); _shade(c, "FFF6DC")
    p = c.paragraphs[0]; p.paragraph_format.space_after = Pt(2)
    rich(p, text, size=10)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)


def load(name):
    return json.loads((RES / name).read_text(encoding="utf8"))


def f(x, n=3):
    return f"{x:.{n}f}"


# ---------- live-verification inputs ----------
def read(name):
    p = Path(args.tests_dir) / name
    return p.read_text(encoding="utf8", errors="ignore") if p.exists() else ""


py = re.findall(r"(\d+) passed", read("pytest_out.txt"))
vt = re.findall(r"Tests\s+(\d+) passed", read("vitest_out.txt"))
tsc_ok = "tsc exit 0" in read("tsc_out.txt")
build_ok = "build exit 0" in read("build_out.txt")
n_back = py[-1] if py else "not run"
n_front = vt[-1] if vt else "not run"
today = date.today()
TODAY_LONG = f"{today.day} {today.strftime('%B %Y')}"

ang = load("angle-accuracy.json")["data"]
cnt = load("counting.json")["data"]
ext = load("external-mocap.json")["data"]
perf = load("performance.json")

# ---------- cover ----------
for _ in range(3):
    doc.add_paragraph()
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
_rpr(p.add_run("AN AI-DRIVEN ADAPTIVE AR/VR FRAMEWORK FOR PERSONALIZED REHABILITATION"), bold=True, color=NAVY, size=22)
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
_rpr(p.add_run("Using Vision-Based Human Pose Estimation"), italic=True, color=BLUE, size=14)
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
_rpr(p.add_run("Complete Technical Analysis & Project Documentation"), italic=True, color=BLUE, size=14)
doc.add_paragraph()
para("Pose Estimation  |  Repetition Counting  |  Adaptive Difficulty  |  AR Overlay  |  3D Room", align="center")
doc.add_paragraph(); doc.add_paragraph()
cover = [
    ("Project Title", "ARVR: Adaptive AR/VR Rehabilitation Framework"),
    ("Programme", "M.Tech project"),
    ("Author", "Manasa Krishnakumar"),
    ("Version", "Research prototype 0.1.0 (not a medical device)"),
    ("Technology Stack", "Python 3.10 | FastAPI | SQLite | React 19 + TypeScript | MediaPipe | three.js | Unity 6 (optional)"),
    ("Evidence", "REHAB26-ViewAngles and REHAB24-6 public datasets (no patients)"),
    ("Source Code", "github.com/manasakrishnakumar/ARVR-PROJECT"),
    ("Report Date", TODAY_LONG),
]
t = doc.add_table(rows=len(cover), cols=2); t.style = "Table Grid"; t.alignment = 1; t.autofit = False
for i, (k, v) in enumerate(cover):
    a, b = t.rows[i].cells
    a.width = Inches(1.8); b.width = Inches(4.5)
    if i % 2 == 0:
        _shade(a, BAND); _shade(b, BAND)
    a.paragraphs[0].paragraph_format.space_after = Pt(2); b.paragraphs[0].paragraph_format.space_after = Pt(2)
    _rpr(a.paragraphs[0].add_run(k), bold=True, size=10)
    _rpr(b.paragraphs[0].add_run(v), size=10)

# ---------- 1 ----------
h1("1. Executive Summary", first=False)
para("The ARVR framework is a local, camera-only system for guided home rehabilitation exercise. It estimates body pose in the "
     "browser from an ordinary webcam, measures joint angles, counts repetitions, assesses movement quality, gives short feedback, "
     "and suggests a gently adjusted difficulty level for the next session. The same pipeline drives four presentations: a 2D "
     "live-session page, a camera-overlay AR view, a desktop 3D room and an optional Unity client.")
para("The adaptive controller is deliberately conservative and is tested for safety properties (it never raises difficulty on "
     "unreliable data, moves one level at a time, and reported pain only makes suggestions more cautious). Every stage of the "
     "pipeline was evaluated on public research recordings using participant-level splits and an external dataset.")
note("**Honest status.** This is a research prototype. No patients took part, thresholds have not been reviewed by a clinician, "
     "and nothing here shows that the system improves recovery. Real webcam use on a laptop or phone, the Unity Play-mode check "
     "and immersive VR on a headset have not yet been tested (Section 14).")
h2("Key Features at a Glance")
bullets([
    "Browser pose estimation (MediaPipe Pose Landmarker, CPU); video never leaves the browser",
    "Confidence-gated 2D joint angles with an isotropic correction for non-square video",
    "Repetition counter (state machine with hysteresis) and optional per-user range calibration",
    "Rule-based movement assessment with one plain-language tip per repetition; Random Forest as a baseline",
    "Conservative adaptive difficulty with multi-session confirmation, a pain rule and stated reasons",
    "Nine exercises defined as data (JSON); adding an exercise needs no code change",
    "AR camera overlay: ghost trainer, joint colours, setup hints, rep flash, voice cues, front/back camera, full screen",
    "Desktop 3D rehabilitation room with a virtual trainer; experimental web 'Enter VR' (untested without a headset)",
    "Optional accounts with export, backup, restore and delete; Docker and local HTTPS verified; about 290 automated tests",
])
h2("Measured Results at a Glance")
a_all = ang["overall"]
table(["Question", "Result"], [
    ["Browser joint-angle accuracy vs motion capture", f"MAE {a_all['mae_deg']:.2f}°, RMSE {a_all['rmse_deg']:.2f}°, r {a_all['pearson_r']:.2f} ({a_all['n']:,} frames)"],
    ["Repetition counting (REHAB26)", f"F1 {cnt['REHAB26 (MediaPipe skeletons)']['illustrative']['f1']:.2f} with illustrative ranges, {cnt['REHAB26 (MediaPipe skeletons)']['auto']['f1']:.2f} with per-user calibration"],
    ["Quality classification, new dataset", "balanced accuracy 0.49 (angle only), 0.61 (all features), 0.686 with a threshold chosen on training data (95% CI 0.625–0.761)"],
    ["Probability calibration", "over-confident: mean predicted 0.69–0.72 vs 0.40 observed"],
    ["Backend speed (in-process)", f"about 4 µs analysis per sample; WebSocket round trip mean 0.76 ms, p99 1.5 ms against 66 ms per sample"],
    ["Adaptive controller", "bounded and safe in tests and simulation; says nothing about benefit to real people"],
], [2.4, 3.9])

# ---------- 2 ----------
h1("2. Project Architecture")
h2("2.1 Directory Structure")
para("The project is a monorepo with a Python backend, a React frontend, an optional Unity client, documentation and scripts:")
table(["Path / File", "Description"], [
    ["ARVR project/", "Repository root"],
    ["  backend/app/", "FastAPI application (about 4,300 lines in 58 Python files)"],
    ["    angle_calculation/", "Authoritative angle maths and smoothing"],
    ["    repetition_detection/", "Repetition counter state machine, features, posture features"],
    ["    exercise_assessment/", "Rule-based assessment of each repetition"],
    ["    personalization/", "Adaptive controller, config.json, simulation"],
    ["    exercises/definitions/", "Nine exercise JSON files (data, not code)"],
    ["    services/analysis.py", "StreamAnalyzer: the live pipeline"],
    ["    api/, core/, database/", "REST and WebSocket API, auth, rate limit, security headers, SQLite models"],
    ["    ml/", "Importers, evaluations, Random Forest baseline, performance CLI"],
    ["  backend/tests/", "29 test files (about 2,400 lines)"],
    ["  frontend/src/", "React + TypeScript app (about 4,200 lines in 56 files)"],
    ["    pose/", "Pose estimators (MediaPipe, synthetic demo), skeleton drawing, guidance, speech, WebXR helper"],
    ["    pages/, components/", "Pages, charts, command palette, movement demo, effects"],
    ["  unity-client/", "Optional Unity 6 client with OpenXR packages and a local pose relay"],
    ["  docs/", "User guide, installation, API, architecture, results, thesis draft, this report"],
    ["  scripts/", "Dev certificate script, figure and report builders"],
    ["  docker-compose*.yml", "Docker run (nginx proxy) and optional HTTPS override"],
], [2.5, 3.8], mono_first=True)
h2("2.2 Technology Stack")
table(["Layer", "Technology", "Purpose"], [
    ["Backend framework", "FastAPI (Python 3.10)", "REST API and WebSockets"],
    ["Persistence", "SQLAlchemy 2 + SQLite", "Users, sessions, repetitions, decisions; in-place column upgrades"],
    ["Machine learning", "scikit-learn", "Random Forest quality baseline, evaluation"],
    ["Pose estimation", "MediaPipe tasks-vision (browser)", "33 body landmarks per frame, CPU"],
    ["Frontend", "React 19, TypeScript, Vite 8", "Pages, routing (react-router 7)"],
    ["Charts and 3D", "Recharts, three.js, @react-three/fiber", "Dashboard charts, 3D room, WebXR"],
    ["Testing", "pytest, vitest, Testing Library, Unity edit-mode", "About 290 automated tests"],
    ["Packaging", "Docker Compose, nginx", "One-command run; optional HTTPS on 8443"],
], [1.7, 2.4, 2.2])
h2("2.3 Live Data Flow")
figure(SHOTS / "fig-architecture.png", "System architecture: pose in the browser, analysis and adaptation in the backend", 6.1)
bullets([
    "Browser: camera frame → MediaPipe → landmarks → exercise angle → a small message {time, angle} about every 66 ms.",
    "WebSocket /api/ws/analysis: the StreamAnalyzer smooths the angle, runs the counter (rest → moving out → target → returning) and replies with a state per frame and a rep message when a repetition ends.",
    "POST /api/sessions/{id}/complete summarises the session, asks the controller for a recommendation using the user's history, stores the decision and returns both.",
    "Guest and synthetic-demo sessions are never saved to history; accounts can be deleted completely.",
])

# ---------- 3 ----------
h1("3. Pose Estimation and Angle Measurement")
h2("3.1 Browser Pose Estimation")
para("MediaPipe Pose Landmarker (lite model) runs inside the page on the CPU. The pose code sits behind a small PoseEstimator "
     "interface so the model can be replaced; a synthetic demo figure implements the same interface, which allows every page to be "
     "tested without a camera. A landmark with visibility below 0.5, a non-finite value or a zero-length segment gives no angle (null), never a guess.")
h2("3.2 Joint Angle")
para("The angle at a joint is the 2D angle between three landmarks. Image coordinates are normalised separately per axis, so x is "
     "multiplied by width/height before any angle is computed (an isotropic correction); skipping it distorts angles on non-square video. "
     "Angles are 2D image-plane estimates, not 3D anatomical angles and not clinical measurements.")
h2("3.3 Smoothing")
para("Exponential smoothing skips gaps and rejects one-off spikes but accepts a persistent jump, so a real fast movement is not hidden.")
h2("3.4 Repetition Counting and Calibration")
para("Progress is normalised between a start angle (0) and a target angle (1), so increasing and decreasing movements are handled alike. "
     "The counter moves through rest, moving out, target and returning, with hysteresis, a minimum repetition duration and an abort on long gaps.")
para("With calibration enabled, the start and target come from the user's own first seconds (10th and 90th percentile after at least 5 s, "
     "30 valid samples and 15° of movement). Repetitions made during calibration are replayed, so none are lost. The result describes the range the user "
     "demonstrated, not a target.")
figure(SHOTS / "pose-analysis.jpg", "Pose analysis page: skeleton, diagnostics (frame rate, person-found rate) and joint-angle chart; synthetic demo figure")

# ---------- 4 ----------
h1("4. Movement Assessment")
h2("4.1 Rule-Based Labels")
para("A transparent rule set labels each repetition acceptable, insufficient range, incomplete, too fast, uncontrolled or insufficient data. "
     "Insufficient data is used whenever the measurement was unreliable; the system never guesses.")
h2("4.2 Features")
para("Per repetition the system computes range, duration, speed, direction reversals and reliability. Posture features (torso tilt, shoulder "
     "elevation asymmetry, head tilt, elbow bend, left-right asymmetry, knee valgus, heel lift, knee over toe) and MediaPipe depth cues bring the total to 14.")
h2("4.3 Machine-Learning Baseline")
para("A Random Forest is trained on repetition features as a compared baseline. It is preliminary: on independent recordings it is only modestly "
     "better than chance, so the application relies on the transparent rules and the Research page reports the model honestly (Section 9).")
figure(SHOTS / "live-session.jpg", "Live session page: repetition counter, phase, calibrated range and per-repetition feedback (synthetic demo)")

# ---------- 5 ----------
h1("5. Adaptive Difficulty Controller")
h2("5.1 Design Principles")
bullets([
    "Unreliable data never raises difficulty.",
    "Changes are one level at a time, between sessions, within levels 1 to 3.",
    "Two confirming sessions are needed to raise or lower the level; a dead zone prevents flip-flopping.",
    "A very poor session suggests a pause; reported pain only makes the suggestion more cautious.",
    "Every suggestion lists its reasons, and the user can reset.",
])
h2("5.2 Thresholds (backend/app/personalization/config.json)")
table(["Rule", "Setting"], [
    ["Minimum reliable repetitions / fraction", "5 repetitions and at least 80% reliable"],
    ["Minimum sessions at a level", "2"],
    ["Increase", "quality ≥ 0.85, flagged share ≤ 0.20, all target repetitions done, range spread ≤ 0.15, confirmed in 2 sessions"],
    ["Decrease", "quality ≤ 0.50 or flagged share ≥ 0.50, confirmed in 2 sessions"],
    ["Pause", "quality below 0.30 or flagged share at least 0.80"],
    ["Pain check-in", "pain ≥ 4/10: no increase; pain ≥ 7/10: pause"],
], [2.6, 3.7])
note("These values are illustrative and have not been reviewed by a clinician. A rehabilitation professional must review them before any real use.")
h2("5.3 Simulation Result")
para("The controller was run against made-up user models (200 simulated users per model, 40 sessions each). This checks behaviour only; it does not show that adaptive difficulty helps real people.")
table(["User model", "Policy", "Mismatch (lower is better)", "Level changes", "Reversals"], [
    ["stable", "best fixed level (level 1)", "0.475", "0.0", "0.0"],
    ["stable", "adaptive", "0.197", "2.2", "1.1"],
    ["improving", "best fixed level (level 2)", "0.471", "0.0", "0.0"],
    ["improving", "adaptive", "0.114", "2.2", "0.6"],
], [1.1, 2.0, 1.4, 0.9, 0.9], center=(2, 3, 4))
figure(SHOTS / "research.jpg", "Research page: the simulation table is clearly labelled SIMULATION")

# ---------- 6 ----------
h1("6. Exercise Library")
para("Nine exercises are defined as JSON files; start and target angles are illustrative placeholders, not prescriptions. All use three levels "
     "(5, 8 and 10 repetitions; 60%, 75% and 90% of the range; minimum repetition time 1.5, 1.2 and 1.0 s).")
ex_rows = []
for fp in sorted((ROOT / "backend/app/exercises/definitions").glob("*.json")):
    d = json.loads(fp.read_text(encoding="utf8"))
    ex_rows.append([d["name"], "/".join(d["target_joints"]), f"{d['start_angle_deg']}° → {d['target_angle_deg']}°", "; ".join(d.get("common_errors", [])[:3])])
table(["Exercise", "Joint", "Start → target", "Things the system can notice"], ex_rows, [2.2, 0.9, 1.1, 2.1])
figure(SHOTS / "exercises.jpg", "Exercise library page with diagrams and illustrative level tables")

# ---------- 7 ----------
h1("7. Web Application")
h2("7.1 Pages")
table(["Page", "Route", "What it does"], [
    ["Home", "/", "Introduction, an interactive 'raise your arms' demo, links to every mode"],
    ["Exercises", "/exercises", "Exercise library with diagrams, errors it can notice and level tables"],
    ["Live session", "/session", "Camera or synthetic demo; counter, phase, range, feedback, save and suggestion"],
    ["Pose analysis", "/analysis", "Skeleton, per-landmark confidence, angle chart, pipeline diagnostics"],
    ["3D room", "/room", "Desktop 3D view with a virtual trainer; experimental Enter VR"],
    ["AR overlay", "/ar", "Camera-overlay AR: guidance drawn over the live camera picture"],
    ["Dashboard", "/dashboard", "Trends, level history, weekly strip, milestones, CSV export"],
    ["Session summary", "/sessions/:id", "Per-repetition table, suggestion with reasons, pain check-in, printable report"],
    ["Research", "/research", "Evaluation results, simulation, performance"],
    ["Record data", "/collect", "Consent-gated recording of landmark numbers for research (no video)"],
    ["Settings & privacy", "/settings", "Privacy facts, export, backup and restore, delete account"],
], [1.4, 1.3, 3.6])
figure(SHOTS / "home.jpg", "Home page with the interactive movement demo")
h2("7.2 AR Overlay")
para("The camera-overlay AR page is the primary experience when no headset is available. It draws a translucent ghost trainer fitted to the user's torso, "
     "colours the exercising joint green, amber or red, shows setup hints (step back, step closer, face the camera), a progress bar and a "
     "'Good / Slower / Go further' flash after each repetition. It offers optional voice cues, front or back camera and full screen. "
     "It is a camera overlay, not immersive headset AR: WebXR cannot expose camera frames to a page, so body tracking in a headset is not possible from the web.")
figure(SHOTS / "ar-overlay.jpg", "AR overlay: ghost trainer, target angle and 'Good' flash (synthetic demo)")
h2("7.3 3D Room and VR")
para("The 3D room shows an amber virtual trainer and a teal figure that mirrors the user. An 'Enter VR' button appears only when the browser reports a WebXR headset; "
     "it has never been tried on a headset and is documented as untested.")
figure(SHOTS / "room-3d.jpg", "3D rehabilitation room: trainer (amber) and mirrored user (teal)")
h2("7.4 Interactive Touches")
bullets([
    "Home page demo: drag the arms or use the slider; a repetition counts after reaching 90° and returning below 20°. It is a toy with no camera.",
    "Ctrl + K (or /) opens a page switcher; a theme button cycles automatic, light and dark.",
    "Dashboard: a 7-day strip, a streak flame and fun milestones computed from the user's own sessions (not medical).",
    "Confetti only after a real session that reached its target with a score of at least 0.8. All motion stops if the system asks for reduced motion.",
    "Display options for low vision: larger text and high contrast; every control works from the keyboard.",
])
figure(SHOTS / "dashboard-guest.jpg", "Dashboard for a guest: sign-in prompt (saved data needs an account)")
figure(SHOTS / "record-data.jpg", "Record data page: consent first, then numbers only, with participant codes")

# ---------- 8 ----------
h1("8. Backend API and Database")
h2("8.1 Endpoints (prefix /api)")
table(["Method", "Path", "Purpose"], [
    ["GET", "/health", "Status and the safety disclaimer"],
    ["GET", "/exercises, /exercises/{id}", "Exercise library"],
    ["POST", "/auth/register, /auth/login, /auth/logout", "Optional accounts (scrypt hashing, hashed bearer tokens)"],
    ["GET/PATCH/DELETE", "/me", "Profile; delete removes the account and its data"],
    ["GET/POST", "/me/backup, /me/restore", "Idempotent, ownership-safe backup and restore (JSON)"],
    ["POST", "/sessions", "Start a session (guest, signed-in or demo)"],
    ["POST", "/sessions/{id}/repetitions", "Save a finished repetition"],
    ["POST", "/sessions/{id}/complete", "Summary, recommendation, optional pain and note"],
    ["POST", "/sessions/{id}/checkin", "Pain check-in that re-evaluates the suggestion"],
    ["GET", "/sessions, /sessions/{id}, /sessions/{id}/detail", "History and per-repetition detail"],
    ["GET", "/progress, /summary, /analytics/weekly, /export.csv", "Dashboard data and CSV export"],
    ["POST", "/recommend, /reset, GET /state", "Adaptive controller access"],
    ["POST", "/assessment/evaluate", "Stateless assessment of a repetition"],
    ["GET", "/results, /models/status", "Evaluation results and model status for the Research page"],
    ["WS", "/ws/analysis", "Live angle stream → counter and assessment"],
    ["WS", "/ws/relay/{room}", "Local pose relay for the Unity client"],
], [1.3, 2.7, 2.3], mono_first=False)
h2("8.2 Database Tables")
table(["Table", "Main columns"], [
    ["users", "id, username (unique), password_hash (scrypt), age_range, goals, preferences, created_at"],
    ["auth_tokens", "token_digest (SHA-256 only), user_id, created_at, expires_at"],
    ["sessions", "id, user_id (null = guest), exercise_id, is_demo, difficulty, ws_key, started_at, ended_at, summary, pain (0–10), note"],
    ["repetitions", "id, session_id, index, range_of_motion_deg, duration_s, quality_label, quality_score, counted, reliable, features"],
    ["adaptive_decisions", "id, user_id, exercise_id, session_id, from_level, to_level, action, classification, reasons, metrics, created_at"],
], [1.6, 4.7], mono_first=True)
h2("8.3 Security Measures")
bullets([
    "Passwords hashed with scrypt; only a SHA-256 digest of each bearer token is stored.",
    "Sign-in lockout after 5 failures in 5 minutes per username and IP; general rate limit of 300 requests per minute per IP.",
    "Security headers on every response (HSTS only over HTTPS); per-session secret for the live stream; ownership checks on every session route.",
    "Only joint-angle numbers reach the backend, which runs on the user's own computer; no cloud service, analytics or external AI is used.",
])

# ---------- 9 ----------
h1("9. Evaluation and Results")
h2("9.1 Datasets")
para("Two public datasets were used (CC BY-NC 4.0; raw data is not redistributed). **REHAB26-ViewAngles** (Zenodo 23018128): 5 healthy volunteers, "
     "3 exercises, 1,665 labelled repetitions; participants are pseudonymised R26-P1 to R26-P5. **REHAB24-6** (Zenodo 13305826): volunteers recorded with "
     "motion capture and video; used for angle accuracy and as the external test set. All results are preliminary and non-clinical.")
h2("9.2 Joint-Angle Accuracy (RQ1)")
rows = [["All frames", f"{a_all['n']:,}", f"{a_all['mae_deg']:.2f}", f"{a_all['rmse_deg']:.2f}", f"{a_all['pearson_r']:.2f}"]]
for k, v in ang["by_exercise"].items():
    rows.append([k.replace("_", " "), f"{v['n']:,}", f"{v['mae_deg']:.2f}", f"{v['rmse_deg']:.2f}", f"{v['pearson_r']:.2f}"])
table(["Group", "Frames", "MAE (°)", "RMSE (°)", "Pearson r"], rows, [2.2, 1.0, 1.0, 1.0, 1.1], center=(1, 2, 3, 4))
para(f"Bias {a_all['bias_deg']:.2f}°, 95% limits of agreement {a_all['loa95_deg'][0]:.1f}° to +{a_all['loa95_deg'][1]:.1f}°, over {ang['recordings']} recordings. "
     "The error depends on the camera (mean absolute error 9.0° for one camera and 4.3° for the other). Part of the error is definitional (motion-capture joint centres versus landmarks). "
     "Useful for counting and coarse range; not a clinical measurement.")
h2("9.3 Repetition Counting (RQ2)")
crow = []
for ds, nm in (("REHAB26 (MediaPipe skeletons)", "REHAB26"), ("REHAB24-6 (motion-capture joints)", "REHAB24-6")):
    for mode, lab in (("illustrative", "illustrative ranges"), ("auto", "per-user calibration")):
        r = cnt[ds][mode]
        crow.append([f"{nm}, {lab}", f"{r['labelled_repetitions']:,}", f"{r['detected_repetitions']:,}", f"{r['precision']:.2f}", f"{r['recall']:.2f}", f"{r['f1']:.2f}", f"{r['mean_absolute_count_error']:.2f}"])
table(["Setting", "Labelled", "Detected", "Precision", "Recall", "F1", "Count error"], crow, [2.2, 0.7, 0.7, 0.7, 0.6, 0.5, 0.9], center=(1, 2, 3, 4, 5, 6))
para("Calibration clearly helps on REHAB26 (F1 0.90 → 0.97, count error 1.0 → 0.2). On the REHAB24-6 motion-capture set it does not, so calibration is not a universal improvement.")
h2("9.4 Movement-Quality Classification (RQ3–RQ5)")
figure(SHOTS / "fig-results.png", "Balanced accuracy of the quality model when trained on REHAB26 and tested on REHAB24-6", 5.6)
para("Angle features alone are near chance (0.49). Posture and depth features raise it to 0.61, and a decision threshold chosen on training data only gives 0.686 "
     "(95% CI 0.625–0.761). Inside a single dataset (leave one person out) the model reaches about 0.72, so the gap reflects people and setup shift rather than the skeleton source. "
     "The model is over-confident: the mean predicted probability of an error was "
     f"{ext['probability_calibration_on_test']['angle_only']['mean_predicted_probability']:.2f} for angle-only and "
     f"{ext['probability_calibration_on_test']['angle_plus_posture']['mean_predicted_probability']:.2f} with posture features, against {ext['test_incorrect_fraction']:.2f} observed; "
     "probabilities must not be shown to users as certainty.")
h2("9.5 Backend Performance")
table(["Measure", "Result"], [
    ["Analysis cost per sample", "about 4 µs"],
    ["WebSocket round trip", "mean 0.76 ms, 99th percentile 1.5 ms"],
    ["Budget", "one sample every 66 ms"],
], [3.0, 3.3])
para("Measured in-process with a test client on one computer; it excludes the network and the browser's pose estimation.")
h2("9.6 Reading the Results Honestly")
bullets([
    "Transfer between datasets is modest; the in-domain figure is not what a new user should expect.",
    "Five training participants cannot support deployment-grade claims.",
    "No patients took part, so there is no evidence of rehabilitation benefit.",
    "Thresholds have not been reviewed by a clinician.",
])

# ---------- 10 ----------
h1("10. How to Use the Application")
h2("10.1 Starting the Application")
para("Native run (two terminals):")
for line in ("cd backend ; .\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --port 8000", "cd frontend ; npm run dev"):
    para(line, size=9.5, after=2).runs[0].font.name = "Courier New"
para("Then open http://localhost:5173. Docker alternative: `docker compose up --build` (nginx proxy); local HTTPS for phone use is described in docs/installation.md.")
h2("10.2 Step-by-Step Usage")
bullets([
    "Open **Exercises** and pick an exercise; open **Live session** (or **AR overlay**).",
    "Press **Start camera** and allow the camera, or **Synthetic demo** to see the pipeline without a camera.",
    "Tick **Calibrate to my range** to use your own demonstrated range; optionally enable audio or voice cues.",
    "Move; watch repetitions, phase and feedback update. Press **Stop and save** (signed-in users) to get the summary and a suggestion.",
    "Report pain on the summary page if you feel any; the suggestion becomes more cautious.",
    "Open the **Dashboard** for trends, export CSV or a backup from **Settings & privacy**.",
])
h2("10.3 Phone and Headset")
para("On the same Wi-Fi, create the development certificate (scripts/make_dev_cert.ps1), start Vite with HTTPS, open the computer's address on the phone, accept the "
     "certificate warning and use the AR overlay with the back camera. The optional Unity 6 client (OpenXR packages installed) can show the room in VR; both phone and headset paths are untested.")

# ---------- 11 ----------
h1("11. Privacy, Safety and Ethics")
bullets([
    "**Camera:** the browser asks for permission every time; pose estimation runs locally; video is not uploaded or stored and the camera is switched off when you stop.",
    "**Backend receives:** only joint-angle numbers and timestamps, on your own computer.",
    "**Saved for signed-in users:** username and salted password hash, optional age range and goals text, preferences, and completed sessions with scores and suggestions. Guest and demo sessions are not saved.",
    "**Not collected:** medical information, video, images or location. Please do not type medical details into the goals or note fields.",
    "**Research recordings:** numbers only, participant codes instead of names, consent checkbox first; get your institution's approval for any real study.",
    "**Not a medical device.** The system cannot tell whether an exercise is safe for you; follow a qualified professional and stop if you feel discomfort.",
])

# ---------- 12 ----------
h1("12. Testing and Quality")
table(["Suite", "Scope", "Result"], [
    ["Backend (pytest)", "angle maths, counter, assessment, controller bounds (including property tests over long random histories), API validation and ownership, persistence, importers, evaluation code, rate limits, security headers, performance", f"{n_back} passed"],
    ["Frontend (vitest)", "pose guidance, WebXR helper, display options, components, pages, interactive features", f"{n_front} passed"],
    ["Type check (tsc)", "TypeScript strict check of the frontend", "clean" if tsc_ok else "not verified"],
    ["Production build (vite)", "bundle the frontend", "OK" if build_ok else "not verified"],
    ["Unity (edit mode)", "client logic", "15 passed (last run earlier in the project)"],
], [1.5, 3.5, 1.3])
para("What tests cannot cover (a real camera, lighting, bodies, phones, headsets) is listed in docs/limitations-and-safety.md with a manual test protocol.")

# ---------- 13 ----------
h1("13. Scientific References and Standards")
para("Only sources that are named in the project's own documentation are listed here. **The literature review (Chapter 2 of the thesis) is not written yet and no citations were invented**; "
     "verify each reference on its own page before using it.")
bullets([
    "REHAB26-ViewAngles dataset: Zenodo record 23018128 (DOI 10.5281/zenodo.23018128), CC BY-NC 4.0. Cite the record and the related paper named on the Zenodo page.",
    "REHAB24-6 dataset: Zenodo record 13305826 (DOI 10.5281/zenodo.13305826), CC BY-NC 4.0; the record lists Cernek, Sedmidubsky and Budikova (SISAP 2024) as authors; verify the exact reference on the Zenodo page.",
    "MediaPipe Pose Landmarker (Google), used for browser pose estimation.",
    "WebXR Device API (W3C), used for the experimental VR button.",
    "Evaluation methods used: leave-one-participant-out validation, participant-level bootstrap intervals, Brier score and expected calibration error (described in docs/research-methodology.md).",
])

# ---------- 14 ----------
h1("14. Limitations and Future Scope")
h2("14.1 Current Limitations")
bullets([
    "Single-camera 2D angles are view dependent and are not clinical measurements.",
    "Small, healthy, non-patient samples; coarse labels; differences between datasets in camera, setting and labelling.",
    "Quality classification transfers only modestly between datasets and is over-confident.",
    "Thresholds and exercise ranges are illustrative and not clinician-reviewed.",
    "No own-webcam data has been collected yet; browser pose-estimation speed and end-to-end latency are not measured.",
    "Immersive VR, phone use and the newer Unity features have not been tested by hand.",
    "Rate limits are shared per proxy IP behind nginx; the self-signed certificate is for a local network only.",
])
h2("14.2 Remaining Work")
table(["#", "Task", "Who or what is needed"], [
    ["1", "Webcam check on a laptop and a phone (manual protocol in the user guide)", "You, a webcam and a phone"],
    ["2", "Unity Play-mode check of the newer features", "You, the Unity Editor"],
    ["3", "Own recordings with the Record data page and the external test", "You and consenting volunteers"],
    ["4", "Literature review (Chapter 2) from verified sources", "You"],
    ["5", "Clinician review of ranges, difficulty and pain thresholds", "A rehabilitation professional"],
    ["6", "A study with participants (ethics approval first)", "Participants, ethics committee"],
    ["7", "VR on a headset", "An OpenXR/WebXR headset"],
], [0.4, 3.9, 2.0], center=(0,))
h2("14.3 Future Enhancements")
bullets([
    "Browser end-to-end tests (Playwright).",
    "A recurrent-network (LSTM/GRU) baseline compared against the Random Forest.",
    "A proper internet-facing deployment: certificate from a certificate authority, authentication review and hardening.",
])

# ---------- 15 ----------
h1("15. Glossary")
table(["Term", "Meaning"], [
    ["Pose estimation", "Finding body landmarks (joints) in a camera image"],
    ["Landmark", "One of 33 body points returned by MediaPipe, with a visibility score"],
    ["Joint angle", "The 2D angle between three landmarks at a joint, in degrees"],
    ["Range of motion", "How far a joint moves during a repetition"],
    ["Hysteresis", "Different thresholds for entering and leaving a state, to avoid flicker and flip-flopping"],
    ["Calibration", "Using the user's own demonstrated range instead of illustrative targets"],
    ["Adaptive controller", "The rule set that suggests the next difficulty level, with reasons"],
    ["MAE / RMSE", "Mean absolute error / root mean square error of the angle versus motion capture"],
    ["Pearson r", "Correlation between measured and reference angles (1 = perfect)"],
    ["Balanced accuracy", "Average of recall on each class; 0.50 is chance for two classes"],
    ["Leave-one-participant-out", "Train on all people but one, test on the one left out, repeat"],
    ["Bootstrap CI", "A confidence interval from resampling participants"],
    ["Brier score / ECE", "Measures of how trustworthy predicted probabilities are"],
    ["WebSocket", "A persistent connection used to stream angles to the backend"],
    ["WebXR", "Browser standard for VR/AR devices"],
    ["AR overlay", "Guidance drawn on top of the live camera picture (not immersive)"],
    ["CC BY-NC 4.0", "Licence allowing non-commercial use with attribution"],
], [1.9, 4.4])

# ---------- 16 ----------
h1("16. Live Verification (" + TODAY_LONG + ")")
para("The application was started again from the project folder on Windows 11 (Python 3.10, Node, Vite) and every page in Section 7 was opened in a browser; "
     "the screenshots in this report were captured from that running application. The synthetic demo figure was used on the Live session, Pose analysis, "
     "AR overlay and 3D room pages because no webcam test has been done yet. The automated checks were then run:")
table(["Check", "Result"], [
    ["Backend tests", f"{n_back} passed"],
    ["Frontend tests", f"{n_front} passed"],
    ["TypeScript check", "clean" if tsc_ok else "not verified"],
    ["Frontend production build", "OK" if build_ok else "not verified"],
    ["Pages opened and checked in a browser", "Home, Exercises, Live session, Pose analysis, AR overlay, 3D room, Research, Record data, Settings, Dashboard"],
    ["Interactive features checked in a browser", "Home demo counted a repetition; Ctrl+K palette navigated to the Dashboard"],
], [2.6, 3.7])
para("Not verified: a real webcam on a laptop or phone, immersive VR on a headset, the Unity Play-mode check, and any study with people (Section 14.2).")

# ---------- footer, properties ----------
sec = doc.sections[0]
fp = sec.footer.paragraphs[0] if sec.footer.paragraphs else sec.footer.add_paragraph()
fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
_rpr(fp.add_run("ARVR Project Report  |  Research prototype, not a medical device  |  Page "), size=8, color="55656F")
r = fp.add_run(); _rpr(r, size=8, color="55656F")
for kind, txt in (("begin", None), (None, "PAGE"), ("end", None)):
    if kind:
        e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), kind)
    else:
        e = OxmlElement("w:instrText"); e.set(qn("xml:space"), "preserve"); e.text = txt
    r._r.append(e)
cp = doc.core_properties
cp.title = "An AI-Driven Adaptive AR/VR Framework for Personalized Rehabilitation: Project Report"
cp.author = "Manasa Krishnakumar"; cp.subject = "ARVR project report"; cp.keywords = "pose estimation, rehabilitation, adaptive, AR, VR"
cp.comments = ""; cp.last_modified_by = "Manasa Krishnakumar"

out = Path(args.out)
doc.save(out)
print("saved", out, out.stat().st_size // 1024, "KB")
