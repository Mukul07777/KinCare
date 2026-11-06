"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useRouter } from "next/navigation";
import { ArrowRight, CornerDownLeft, Search } from "lucide-react";
import { GROUPS, type Route } from "@/lib/routes";

// ⌘K / Ctrl+K (or "/") from anywhere: type a few letters, Enter to go. 25+ pages, one keystroke away.
export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [i, setI] = useState(0);
  const input = useRef<HTMLInputElement>(null);

  const results = useMemo(() => {
    const words = q.toLowerCase().split(/\s+/).filter(Boolean);
    return GROUPS.flatMap((g) => g.routes.map((r) => ({ ...r, group: g.label })))
      .filter((r) => words.every((w) => `${r.label} ${r.hint} ${r.keywords ?? ""} ${r.group}`.toLowerCase().includes(w)));
  }, [q]);

  useEffect(() => { if (open) { setQ(""); setI(0); setTimeout(() => input.current?.focus(), 0); } }, [open]);
  useEffect(() => setI(0), [q]);

  if (!open) return null;
  const go = (r?: Route) => { if (r) { onClose(); router.push(r.href); } };

  // Portal to <body>: the header's backdrop-blur makes it the containing block for fixed children,
  // which clipped the dimmed backdrop to the header strip.
  return createPortal(
    <div className="fixed inset-0 z-[90] flex items-start justify-center bg-espresso/40 px-4 pt-[12vh] backdrop-blur-sm" onMouseDown={onClose}>
      <div role="dialog" aria-label="Go to a page" onMouseDown={(e) => e.stopPropagation()}
        className="w-full max-w-xl overflow-hidden rounded-3xl border border-line bg-paper shadow-[0_40px_100px_-30px_rgba(42,28,21,0.6)]">
        <div className="flex items-center gap-3 border-b border-line px-5">
          <Search className="size-5 text-muted" />
          <input
            ref={input} value={q} onChange={(e) => setQ(e.target.value)} placeholder="Where to? Try “fake”, “hindi”, “price”…"
            className="h-14 flex-1 bg-transparent text-base outline-none placeholder:text-muted"
            onKeyDown={(e) => {
              if (e.key === "ArrowDown") { e.preventDefault(); setI((x) => Math.min(results.length - 1, x + 1)); }
              if (e.key === "ArrowUp") { e.preventDefault(); setI((x) => Math.max(0, x - 1)); }
              if (e.key === "Enter") go(results[i]);
              if (e.key === "Escape") onClose();
            }}
          />
          <kbd className="rounded-md border border-line px-1.5 py-0.5 font-mono text-[11px] text-muted">esc</kbd>
        </div>
        <ul className="max-h-[55vh] overflow-y-auto p-2">
          {results.map((r, k) => {
            const Icon = r.icon;
            return (
              <li key={r.href}>
                <button onMouseEnter={() => setI(k)} onClick={() => go(r)}
                  className={`flex w-full items-center gap-3 rounded-2xl px-3 py-2.5 text-left transition ${k === i ? "bg-sand" : ""}`}>
                  <span className={`grid size-9 shrink-0 place-items-center rounded-xl ${k === i ? "bg-brown text-paper" : "bg-cream text-brown"}`}><Icon className="size-4" /></span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-medium">{r.label}</span>
                    <span className="block truncate text-xs text-muted">{r.hint}</span>
                  </span>
                  <span className="text-[11px] text-muted">{r.group}</span>
                  {k === i ? <CornerDownLeft className="size-4 text-brown" /> : <ArrowRight className="size-4 text-clay" />}
                </button>
              </li>
            );
          })}
          {!results.length && <li className="px-4 py-8 text-center text-sm text-muted">Nothing called “{q}”. Try a feature, like “recall” or “price”.</li>}
        </ul>
      </div>
    </div>,
    document.body,
  );
}

export function useCommandPalette() {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const typing = ["INPUT", "TEXTAREA", "SELECT"].includes((e.target as HTMLElement)?.tagName);
      if ((e.key.toLowerCase() === "k" && (e.metaKey || e.ctrlKey)) || (e.key === "/" && !typing)) { e.preventDefault(); setOpen((o) => !o); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  return { open, setOpen };
}
