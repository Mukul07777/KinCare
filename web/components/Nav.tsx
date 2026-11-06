"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ArrowRight, ChevronDown, CircleUser, Menu, Search, ShieldPlus, Siren, X } from "lucide-react";
import { authMe } from "@/lib/api";
import { GROUPS, MORE_GROUPS, PRIMARY_ROUTES } from "@/lib/routes";
import { CommandPalette, useCommandPalette } from "@/components/CommandPalette";

// The top bar tells one story (lib/routes.ts PRIMARY); everything else is under More, in the footer and one ⌘K away.

export function Logo() {
  return (
    <Link href="/" className="flex items-center gap-2">
      <ShieldPlus className="size-6 text-teal" strokeWidth={2.2} />
      <span className="text-xl font-semibold tracking-tight">kincare<span className="text-teal">.</span></span>
    </Link>
  );
}

export function Nav() {
  const path = usePathname();
  const [open, setOpen] = useState(false);
  const [menu, setMenu] = useState(false);
  const [me, setMe] = useState<string | null>(null);
  const palette = useCommandPalette();
  const bar = useRef<HTMLDivElement>(null);

  useEffect(() => { authMe().then((m) => setMe(m.masked)).catch(() => setMe(null)); }, [path]);
  useEffect(() => { setMenu(false); setOpen(false); }, [path]);
  useEffect(() => {
    const away = (e: MouseEvent) => { if (!bar.current?.contains(e.target as Node)) setMenu(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") setMenu(false); };
    document.addEventListener("mousedown", away);
    document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("mousedown", away); document.removeEventListener("keydown", esc); };
  }, []);

  const active = (href: string) => path === href || path.startsWith(href + "/");
  const moreActive = MORE_GROUPS.some((g) => g.routes.some((r) => active(r.href)));

  return (
    <header className="sticky top-0 z-50 print:hidden border-b border-line bg-cream/80 backdrop-blur-xl">
      <div ref={bar} className="relative mx-auto flex h-16 max-w-6xl items-center justify-between gap-3 px-4 sm:px-6">
        <Logo />
        <nav className="hidden items-center gap-1 rounded-full border border-line bg-paper p-1 text-sm lg:flex" aria-label="Main">
          {PRIMARY_ROUTES.map((r) => (
            <Link key={r.href} href={r.href} aria-current={active(r.href) ? "page" : undefined}
              className={`whitespace-nowrap rounded-full px-4 py-1.5 transition ${active(r.href) ? "bg-brown text-paper shadow-sm" : "text-muted hover:text-espresso"}`}>
              {r.label}
            </Link>
          ))}
          <button onClick={() => setMenu(!menu)} aria-expanded={menu}
            className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full px-4 py-1.5 transition ${
              menu ? "bg-sand text-espresso" : moreActive ? "bg-brown text-paper shadow-sm" : "text-muted hover:text-espresso"
            }`}>
            More <ChevronDown className={`size-3.5 transition ${menu ? "rotate-180" : ""}`} />
          </button>
        </nav>
        <div className="flex items-center gap-2 whitespace-nowrap">
          <button onClick={() => palette.setOpen(true)} aria-label="Search pages"
            className="hidden items-center gap-2 rounded-full border border-line bg-paper py-2 pl-3 pr-2 text-sm text-muted transition hover:border-brown hover:text-espresso md:inline-flex">
            <Search className="size-4" /> <span className="hidden xl:inline">Search</span>
            <kbd className="rounded-md bg-cream px-1.5 font-mono text-[11px]">⌘K</kbd>
          </button>
          <Link href={me ? "/account" : "/login"} aria-label={me ? "Account" : "Sign in"}
            className={`hidden items-center gap-1.5 rounded-full px-3 py-2 text-sm transition sm:inline-flex ${me ? "bg-mint font-medium text-teal" : "text-muted hover:text-espresso"}`}>
            <CircleUser className="size-4" /> {me ? <span className="font-mono text-xs">{me}</span> : "Sign in"}
          </Link>
          <Link href="/scan" className="hidden items-center gap-1.5 rounded-full bg-espresso px-5 py-2.5 text-sm font-medium text-paper shadow-[0_8px_20px_-10px_rgba(42,28,21,0.6)] transition hover:bg-brown sm:inline-flex">
            Check a batch <ArrowRight className="size-3.5" />
          </Link>
          <button onClick={() => setOpen(!open)} className="grid size-10 place-items-center rounded-full border border-line lg:hidden" aria-label="Menu" aria-expanded={open}>
            {open ? <X className="size-5" /> : <Menu className="size-5" />}
          </button>
        </div>

        {/* More: every other page, grouped by who it is for */}
        {menu && (
          <div className="absolute left-1/2 top-[calc(100%+8px)] hidden max-h-[calc(100dvh-6rem)] w-[min(980px,calc(100vw-2rem))] -translate-x-1/2 overflow-y-auto rounded-3xl border border-line bg-paper p-4 shadow-[0_30px_80px_-30px_rgba(42,28,21,0.45)] lg:block">
            <div className="grid grid-cols-4 gap-3">
              {MORE_GROUPS.map((g) => (
                <div key={g.id}>
                  <p className="px-2 pb-1 text-xs font-medium uppercase tracking-wider text-muted">{g.label}</p>
                  {g.routes.map((r) => {
                    const Icon = r.icon;
                    return (
                      <Link key={r.href} href={r.href} className={`group flex items-start gap-2.5 rounded-2xl p-2 transition hover:bg-cream ${active(r.href) ? "bg-cream" : ""}`}>
                        <span className="grid size-8 shrink-0 place-items-center rounded-xl bg-sand text-brown transition group-hover:bg-brown group-hover:text-paper"><Icon className="size-4" /></span>
                        <span>
                          <span className="block text-sm font-medium">{r.label}</span>
                          <span className="block text-xs leading-snug text-muted">{r.hint}</span>
                        </span>
                      </Link>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {open && (
        <nav className="max-h-[calc(100dvh-4rem)] overflow-y-auto border-t border-line bg-paper px-4 py-3 lg:hidden" aria-label="Mobile">
          <button onClick={() => { setOpen(false); palette.setOpen(true); }} className="mb-3 flex w-full items-center gap-2 rounded-2xl border border-line px-4 py-3 text-sm text-muted">
            <Search className="size-4" /> Search every page
          </button>
          <div className="mb-3">
            {PRIMARY_ROUTES.map((r) => (
              <Link key={r.href} href={r.href} className={`block rounded-xl px-3 py-3 text-base font-medium ${active(r.href) ? "bg-sand text-brown" : "text-espresso"}`}>{r.label}</Link>
            ))}
          </div>
          {MORE_GROUPS.map((g) => (
            <div key={g.id} className="mb-3">
              <p className="px-3 pb-1 text-xs font-medium uppercase tracking-wider text-muted">{g.label}</p>
              {g.routes.map((r) => (
                <Link key={r.href} href={r.href} className={`block rounded-xl px-3 py-2.5 ${active(r.href) ? "bg-sand font-medium text-brown" : "text-espresso"}`}>{r.label}</Link>
              ))}
            </div>
          ))}
          <Link href={me ? "/account" : "/login"} className="block rounded-xl px-3 py-2.5 text-espresso">{me ? `Account · ${me}` : "Sign in"}</Link>
        </nav>
      )}
      <CommandPalette open={palette.open} onClose={() => palette.setOpen(false)} />
    </header>
  );
}

export function Footer() {
  return (
    <footer className="mt-24 border-t border-line print:hidden">
      <div className="mx-auto grid max-w-6xl gap-8 px-4 py-12 sm:px-6 md:grid-cols-[1.3fr_repeat(4,1fr)]">
        <div>
          <Logo />
          <p className="mt-3 max-w-xs text-sm text-muted">Know the batch, not just the brand. A drug-alert monitor for India.</p>
          <p className="mt-6 text-sm font-medium">Team Avengers</p>
          <p className="text-sm text-muted">Mukul · Ashpreet Singh Saini · Flip the Switch 2026</p>
          <p className="mt-4 text-xs text-muted">Not medical advice. Always consult your pharmacist or doctor.</p>
        </div>
        {GROUPS.map((g) => (
          <div key={g.id} className="text-sm">
            <p className="font-medium">{g.label}</p>
            <div className="mt-3 space-y-2 text-muted">
              {g.routes.map((r) => <Link key={r.href} href={r.href} className="block hover:text-brown">{r.label}</Link>)}
            </div>
          </div>
        ))}
      </div>
    </footer>
  );
}

// Always-reachable emergency button on phones.
export function SosFab() {
  const path = usePathname();
  if (path.startsWith("/sos") || path.startsWith("/admin")) return null;
  return (
    <Link href="/sos" aria-label="SOS emergency" className="fixed bottom-5 right-5 z-50 grid size-14 place-items-center rounded-full bg-danger text-paper shadow-[0_12px_30px_-8px_rgba(190,40,40,0.8)] sm:hidden print:hidden">
      <Siren className="size-6" />
    </Link>
  );
}
