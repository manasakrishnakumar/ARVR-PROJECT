import { useEffect, useState } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { api } from "../services/api";
import { applyPrefs, loadPrefs, savePrefs, type DisplayPrefs } from "../a11y";
import { applyTheme, loadTheme, NAV_LINKS, nextTheme, saveTheme, type ThemeChoice } from "../motion";
import CommandPalette from "./CommandPalette";

const LINKS = NAV_LINKS;
const THEME_ICON = { auto: "◐", light: "☀", dark: "☾" } as const;

export default function Layout() {
  const { user } = useAuth();
  const [disclaimer, setDisclaimer] = useState("Research prototype. Not a medical device and not clinically validated.");
  const [backendDown, setBackendDown] = useState(false);
  const [prefs, setPrefs] = useState<DisplayPrefs>(loadPrefs);
  useEffect(() => { applyPrefs(prefs); savePrefs(prefs); }, [prefs]);
  const [theme, setTheme] = useState<ThemeChoice>(loadTheme);
  useEffect(() => { applyTheme(theme); saveTheme(theme); }, [theme]);
  const [palette, setPalette] = useState(false);

  useEffect(() => {
    api.health().then((h) => setDisclaimer(h.disclaimer)).catch(() => setBackendDown(true));
  }, []);

  return (
    <>
      <a className="skip" href="#main">Skip to content</a>
      <CommandPalette open={palette} onOpen={() => setPalette(true)} onClose={() => setPalette(false)} />
      <header className="topbar">
        <Link to="/" className="brand">ARVR <span className="muted">Adaptive Rehabilitation</span></Link>
        <nav aria-label="Main">
          {LINKS.map(([to, label]) => (
            <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => (isActive ? "active" : "")}>{label}</NavLink>
          ))}
        </nav>
        <div className="a11y" role="group" aria-label="Display options">
          <button type="button" aria-pressed={prefs.largeText} onClick={() => setPrefs((p) => ({ ...p, largeText: !p.largeText }))} title="Larger text">A+</button>
          <button type="button" aria-pressed={prefs.highContrast} onClick={() => setPrefs((p) => ({ ...p, highContrast: !p.highContrast }))} title="High contrast">Contrast</button>
          <button type="button" className="theme-btn" onClick={() => setTheme(nextTheme)} aria-label={`Theme: ${theme}. Click to change`} title={`Theme: ${theme}`}>{THEME_ICON[theme]}</button>
          <button type="button" className="hint-btn" onClick={() => setPalette(true)} aria-label="Jump to a page (Ctrl+K)" title="Jump to a page"><kbd>Ctrl</kbd> <kbd>K</kbd></button>
        </div>
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
