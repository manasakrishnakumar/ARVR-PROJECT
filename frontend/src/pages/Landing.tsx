import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Landing() {
  const { user } = useAuth();
  return (
    <>
      <section className="hero">
        <h1>Rehabilitation exercise feedback from an ordinary webcam</h1>
        <p className="lead">
          ARVR watches how you move, counts repetitions, points out what looks off, and suggests a gently adjusted difficulty
          for your next session. It runs on a normal laptop: no headset or special sensors needed.
        </p>
        <div className="row">
          <Link className="btn primary" to="/session">Try a session</Link>
          <Link className="btn" to="/exercises">See the exercises</Link>
          {!user && <Link className="btn" to="/account">Sign in / create account</Link>}
        </div>
        <p className="notice">
          <strong>Research prototype.</strong> Not a medical device and not clinically validated. It cannot tell whether an exercise is
          safe for you. Follow your qualified rehabilitation professional's guidance and stop if you feel discomfort.
        </p>
      </section>

      <section className="grid3">
        <article className="card"><h3>1. Pick an exercise</h3>
          <p>Choose from the exercise library. Targets shown are illustrative, not prescriptions.</p></article>
        <article className="card"><h3>2. Move in front of the camera</h3>
          <p>Pose tracking runs in your browser. Repetitions, phases and joint angles update live, with one short tip per repetition.</p></article>
        <article className="card"><h3>3. Review and adapt</h3>
          <p>After each session you get a plain-language summary and a conservative suggestion for the next level, with the reasons.</p></article>
      </section>

      <section className="card">
        <h2>What it does and does not do</h2>
        <ul>
          <li>Pose estimation, joint angles, repetition counting and rule-based movement checks: <strong>implemented and tested</strong> on synthetic and on public research recordings.</li>
          <li>Adaptive difficulty with safety limits and multi-session confirmation: <strong>implemented</strong>; its thresholds are illustrative and not yet clinically reviewed.</li>
          <li>Machine-learning movement classification: <strong>preliminary</strong>. On independent recordings it is only modestly better than chance (see the Research page).</li>
          <li>Single-camera angles are 2D estimates, not clinical measurements. Nothing here claims to improve recovery.</li>
          <li>Privacy: video is processed locally and never uploaded or stored. Only joint-angle numbers go to the backend running on your own computer.</li>
        </ul>
      </section>
    </>
  );
}
