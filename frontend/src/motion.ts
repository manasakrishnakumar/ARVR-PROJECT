/** True when animations are fine to run: a real browser (matchMedia exists) and the user has not asked for reduced motion. */
export function motionOk(): boolean {
  try {
    return typeof matchMedia === "function" && !matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch { return false; }
}

export type ThemeChoice = "auto" | "light" | "dark";
const KEY = "arvr.theme";

export function loadTheme(): ThemeChoice {
  try {
    const v = localStorage.getItem(KEY);
    return v === "light" || v === "dark" ? v : "auto";
  } catch { return "auto"; }
}

export function saveTheme(t: ThemeChoice): void {
  try { localStorage.setItem(KEY, t); } catch { /* storage blocked: the choice lasts for this visit only */ }
}

export function applyTheme(t: ThemeChoice, root: HTMLElement = document.documentElement): void {
  if (t === "auto") delete root.dataset.theme; else root.dataset.theme = t;
}

export const nextTheme = (t: ThemeChoice): ThemeChoice => (t === "auto" ? "light" : t === "light" ? "dark" : "auto");

/** The pages, shared by the top bar and the command palette. */
export const NAV_LINKS: [string, string][] = [
  ["/", "Home"], ["/exercises", "Exercises"], ["/session", "Live session"], ["/analysis", "Pose analysis"], ["/room", "3D room"], ["/ar", "AR overlay"], ["/dashboard", "Dashboard"],
  ["/research", "Research"], ["/collect", "Record data"], ["/settings", "Settings & privacy"],
];
