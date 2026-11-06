"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { BellRing, Loader2, Plus, RefreshCw, Trash2 } from "lucide-react";
import { Eyebrow, Heading } from "@/components/Heading";
import { formatIST, getWatchlist, recheckWatchlist, removeWatch, type WatchItem } from "@/lib/api";

const MON = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];

// Expiry as printed ("01/2027", "01/27", "JAN 2027", "Jan-27") -> days left until the end of that month.
function expiryInfo(raw: string | null) {
  if (!raw) return null;
  const s = raw.toUpperCase().replace(/\s+/g, " ").trim();
  let m: number | undefined, y: number | undefined;
  const num = s.match(/^(\d{1,2})\s*[/\-.]\s*(\d{2,4})$/);
  const txt = s.match(/^([A-Z]{3})[A-Z]*\.?\s*[/\-.]?\s*(\d{2,4})$/);
  if (num) [m, y] = [Number(num[1]), Number(num[2])];
  else if (txt && MON.includes(txt[1])) [m, y] = [MON.indexOf(txt[1]) + 1, Number(txt[2])];
  if (!m || !y || m > 12) return null;
  if (y < 100) y += 2000;
  const days = Math.ceil((new Date(y, m, 0, 23, 59).getTime() - Date.now()) / 86400000);
  return { days, label: days < 0 ? "Expired" : days <= 60 ? `Expires in ${days} days` : `Exp ${String(m).padStart(2, "0")}/${y}`, tone: days < 0 ? "danger" : days <= 60 ? "warn" : "ok" };
}

export default function WatchlistPage() {
  const [items, setItems] = useState<WatchItem[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getWatchlist().then(setItems).catch((e) => setError(e.message));
  }, []);

  const recheckAll = async () => {
    setBusy(true);
    try {
      const r = await recheckWatchlist();
      setItems(r.items);
      setNotice(r.changed.length ? `Status changed for ${r.changed.join(", ")}` : "Re-checked every batch. No changes.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (batch: string) => {
    await removeWatch(batch);
    setItems((prev) => prev?.filter((i) => i.batch !== batch) ?? null);
  };

  const flagged = items?.filter((i) => i.last_verdict === "alert_found").length ?? 0;

  return (
    <main className="blush mx-auto max-w-6xl px-4 pt-12 sm:px-6 sm:pt-16">
      <div className="flex flex-wrap items-end justify-between gap-6">
        <div>
          <Eyebrow>Watchlist</Eyebrow>
          <Heading as="h1" lead="Batches we’re" tail="watching for you." className="mt-4 text-4xl sm:text-6xl" />
          <p className="mt-4 max-w-md text-muted">Every saved batch is re-checked when new alert lists are loaded. Re-check now any time.</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={recheckAll}
            disabled={busy || !items?.length}
            className="inline-flex items-center gap-2 rounded-full border border-espresso/15 bg-paper px-5 py-3 text-sm font-medium transition hover:border-brown hover:text-brown disabled:opacity-40"
          >
            {busy ? <Loader2 className="size-4 animate-spin" /> : <RefreshCw className="size-4" />} Re-check all
          </button>
          <Link href="/scan" className="inline-flex items-center gap-2 rounded-full bg-brown px-5 py-3 text-sm font-medium text-paper transition hover:bg-brown-2">
            <Plus className="size-4" /> Add batch
          </Link>
        </div>
      </div>

      {error && <p className="mt-6 rounded-2xl border border-danger/20 bg-danger/5 px-5 py-4 text-sm text-danger">Could not reach the KinCare service: {error}</p>}
      {notice && <p className="mt-6 rounded-2xl bg-sand/70 px-5 py-3 text-sm">{notice}</p>}

      {items && items.length > 0 && (
        <div className="mt-8 grid grid-cols-2 gap-3 sm:max-w-md">
          <div className="card rounded-3xl p-5">
            <p className="text-sm text-muted">Watching</p>
            <p className="mt-1 text-4xl font-medium tracking-tight">{items.length}</p>
          </div>
          <div className={`card rounded-3xl p-5 ${flagged ? "bg-danger text-paper" : ""}`}>
            <p className={`text-sm ${flagged ? "text-paper/80" : "text-muted"}`}>Flagged</p>
            <p className="mt-1 text-4xl font-medium tracking-tight">{flagged}</p>
          </div>
        </div>
      )}

      <div className="mt-6">
        {items === null ? null : items.length === 0 ? (
          <div className="card flex flex-col items-center rounded-[2rem] px-6 py-16 text-center">
            <span className="grid size-16 place-items-center rounded-full bg-sand text-brown">
              <BellRing className="size-7" />
            </span>
            <p className="mt-5 text-xl font-medium tracking-tight">Nothing watched yet</p>
            <p className="mt-2 max-w-sm text-sm text-muted">Scan a medicine and tap “Watch this batch”. We will keep checking it against every new alert.</p>
            <Link href="/scan" className="mt-6 rounded-full bg-brown px-6 py-3 text-sm font-medium text-paper transition hover:bg-brown-2">Scan your first strip</Link>
          </div>
        ) : (
          <div className="space-y-8">
          {Object.entries(items.reduce<Record<string, WatchItem[]>>((g, w) => ((g[w.member || "Unassigned"] ??= []).push(w), g), {})).map(([member, group]) => (
          <section key={member}>
            <div className="mb-3 flex items-center gap-3">
              <span className="grid size-9 place-items-center rounded-full bg-brown text-sm font-semibold text-paper">{member[0]}</span>
              <p className="text-lg font-medium tracking-tight">{member}</p>
              <span className="text-sm text-muted">{group.length} medicine{group.length > 1 ? "s" : ""}</span>
            </div>
          <div className="grid gap-3 md:grid-cols-2">
            {group.map((w) => {
              const hit = w.last_verdict === "alert_found";
              const exp = expiryInfo(w.expiry);
              return (
                <div key={w.batch} className="card relative overflow-hidden rounded-3xl p-6">
                  <span className={`absolute inset-y-0 left-0 w-1.5 ${hit ? "bg-danger" : "bg-safe"}`} />
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-xl font-medium tracking-tight">{w.brand ?? "Unknown brand"}</p>
                      <p className="mt-0.5 font-mono text-sm text-muted">Batch {w.batch}{w.maker && ` · ${w.maker}`}</p>
                    </div>
                    <span className={`shrink-0 rounded-full px-3 py-1 text-xs font-semibold ${hit ? "bg-danger/10 text-danger" : "bg-safe/10 text-safe"}`}>
                      {hit ? "Alert found" : "No alert"}
                    </span>
                  </div>
                  {(exp || w.phone) && (
                    <div className="mt-3 flex flex-wrap gap-2 text-xs">
                      {exp && (
                        <span className={`rounded-full px-2.5 py-1 font-medium ${exp.tone === "danger" ? "bg-danger text-paper" : exp.tone === "warn" ? "bg-warn-soft text-warn" : "bg-cream text-muted"}`}>{exp.label}</span>
                      )}
                      {w.phone && <span className="rounded-full bg-safe/10 px-2.5 py-1 font-medium text-safe">WhatsApp + call alerts on</span>}
                    </div>
                  )}
                  <div className="mt-4 flex items-center justify-between text-xs text-muted">
                    <span>Checked {formatIST(w.last_checked_at)}</span>
                    <div className="flex gap-2">
                      <Link
                        href={`/result?${new URLSearchParams(Object.entries({ batch: w.batch, brand: w.brand ?? "", maker: w.maker ?? "" }).filter(([, v]) => v))}`}
                        className="rounded-full border border-line px-3 py-1.5 font-medium text-espresso transition hover:border-brown hover:text-brown"
                      >
                        Details
                      </Link>
                      <button onClick={() => remove(w.batch)} className="grid size-8 place-items-center rounded-full border border-line transition hover:border-danger hover:text-danger" aria-label="Remove">
                        <Trash2 className="size-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
          </section>
          ))}
          </div>
        )}
      </div>
    </main>
  );
}
