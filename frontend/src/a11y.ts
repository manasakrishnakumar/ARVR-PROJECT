/** Display preferences for older users and low vision: larger text and high contrast. Stored only in this browser. */
export interface DisplayPrefs { largeText: boolean; highContrast: boolean }

const KEY = "arvr.display";
export const DEFAULT_PREFS: DisplayPrefs = { largeText: false, highContrast: false };

export function loadPrefs(): DisplayPrefs {
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) ?? "{}");
    return { largeText: raw.largeText === true, highContrast: raw.highContrast === true };
  } catch { return { ...DEFAULT_PREFS }; }
}

export function savePrefs(p: DisplayPrefs): void {
  try { localStorage.setItem(KEY, JSON.stringify(p)); } catch { /* storage may be blocked: the setting then lasts for this visit only */ }
}

export function applyPrefs(p: DisplayPrefs, root: HTMLElement = document.documentElement): void {
  root.dataset.text = p.largeText ? "large" : "normal";
  root.dataset.contrast = p.highContrast ? "high" : "normal";
}
