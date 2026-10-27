import { useEffect, useState } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { api } from "../services/api";

const LINKS: [string, string][] = [
  ["/", "Home"], ["/exercises", "Exercises"], ["/session", "Live session"], ["/analysis", "Pose analysis"], ["/dashboard", "Dashboard"],
  ["/research", "Research"], ["/collect", "Record data"], ["/settings", "Settings & privacy"],
];

export default function Layout() {
  const { user } = useAuth();
  const [disclaimer, setDisclaimer] = useState("Research prototype. Not a medical device and not clinically validated.");
  const [backendDown, setBackendDown] = useState(false);

  useEffect(() => {
    api.health().then((h) => setDisclaimer(h.disclaimer)).catch(() => setBackendDown(true));
  }, []);

  return (
    <>
      <a className="skip" href="#main">Skip to content</a>
      <header className="topbar">
        <Link to="/" className="brand">ARVR <span className="muted">Adaptive Rehabilitation</span></Link>
        <nav aria-label="Main">
          {LINKS.map(([to, label]) => (
            <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => (isActive ? "active" : "")}>{label}</NavLink>
          ))}
        </nav>
        <Link className="chip user" to={user ? "/settings" : "/account"}>{user ? user.username : "Guest · sign in"}</Link>
      </header>
      <div className="notice banner" role="note">{disclaimer}</div>
      {backendDown && <div className="notice error-banner" role="alert">Cannot reach the backend. Start it (see README) and reload.</div>}
      <main id="main" className="page"><Outlet /></main>
      <footer className="footer muted">
        Camera processing happens locally in your browser. No video is uploaded or stored. Scores are experimental system
        metrics, not validated medical outcomes. Follow your qualified rehabilitation professional's guidance.
      </footer>
    </>
  );
}
