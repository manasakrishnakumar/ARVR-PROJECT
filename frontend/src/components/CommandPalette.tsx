import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { NAV_LINKS } from "../motion";

/** Ctrl+K (or Cmd+K, or "/") opens a quick page switcher: type, arrow keys, Enter. */
export default function CommandPalette({ open, onClose, onOpen }: { open: boolean; onClose: () => void; onOpen: () => void }) {
  const nav = useNavigate();
  const [q, setQ] = useState("");
  const [sel, setSel] = useState(0);
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const typing = (e.target as HTMLElement | null)?.closest?.("input, textarea, select, [contenteditable]");
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); open ? onClose() : onOpen(); }
      else if (e.key === "/" && !typing && !open) { e.preventDefault(); onOpen(); }
    };
    addEventListener("keydown", onKey);
    return () => removeEventListener("keydown", onKey);
  }, [open, onClose, onOpen]);

  useEffect(() => { if (open) { setQ(""); setSel(0); setTimeout(() => input.current?.focus(), 0); } }, [open]);

  const items = useMemo(() => NAV_LINKS.filter(([, label]) => label.toLowerCase().includes(q.trim().toLowerCase())), [q]);
  if (!open) return null;
  const go = (to: string) => { onClose(); nav(to); };

  return (
    <div className="palette-bg" onMouseDown={onClose}>
      <div className="palette" role="dialog" aria-modal="true" aria-label="Jump to a page" onMouseDown={(e) => e.stopPropagation()}>
        <input ref={input} value={q} placeholder="Jump to a page..." aria-label="Search pages"
          onChange={(e) => { setQ(e.target.value); setSel(0); }}
          onKeyDown={(e) => {
            if (e.key === "Escape") onClose();
            else if (e.key === "ArrowDown") { e.preventDefault(); setSel((s) => Math.min(items.length - 1, s + 1)); }
            else if (e.key === "ArrowUp") { e.preventDefault(); setSel((s) => Math.max(0, s - 1)); }
            else if (e.key === "Enter" && items[sel]) go(items[sel][0]);
          }} />
        <ul>
          {items.map(([to, label], i) => (
            <li key={to} className={i === sel ? "sel" : ""}><button type="button" onClick={() => go(to)} onMouseEnter={() => setSel(i)}><span>{label}</span><span className="muted">{to}</span></button></li>
          ))}
          {items.length === 0 && <li className="muted" style={{ padding: 10 }}>No page matches.</li>}
        </ul>
      </div>
    </div>
  );
}
