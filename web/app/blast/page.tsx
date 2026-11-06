"use client";

import { RoleGate } from "@/components/RoleGate";
import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import {
  Activity, AlertTriangle, ArrowRight, BellRing, Check, Clock, FlaskConical, HeartPulse, Loader2, Pill, Radar, RotateCcw, Send, ShoppingBag, Stethoscope, Users, Eye,
} from "lucide-react";
import { Eyebrow, Heading } from "@/components/Heading";
import {
  blastAlert, blastDemo, clearBlastDemo, formatMonth, getAlerts, getBlast, getBlastInbox,
  type Alert, type BlastInboxItem, type BlastView, type Holder, type VitalChange,
} from "@/lib/api";

const norm = (b: string) => b.replace(/[^A-Za-z0-9]/g, "").toUpperCase();

function BlastGated() {
  return <Suspense><Blast /></Suspense>;
}

function Blast() {
  const params = useSearchParams();
  const router = useRouter();
  const [inbox, setInbox] = useState<BlastInboxItem[]>([]);
  const [fallback, setFallback] = useState<Alert | null>(null);
  const [batch, setBatch] = useState<string | null>(params.get("batch"));
  const [view, setView] = useState<BlastView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<"load" | "seed" | "alert" | "clear" | null>(null);
  const [revealed, setRevealed] = useState<Set<string>>(new Set());
  const [sending, setSending] = useState(false);

  // Inbox of flagged batches people hold; if empty, a recent real NSQ tablet to demo on.
  useEffect(() => {
    getBlastInbox().then((b) => {
      setInbox(b);
      if (!params.get("batch") && b[0]) setBatch(b[0].batch_norm);
    }).catch(() => {});
    getAlerts({ category: "nsq", q: "tablet", limit: 60 }).then((r) => {
      const a = r.items.find((x) => /^[A-Za-z][A-Za-z-]{3,}(\s?[\d.]+)?$/.test(x.brand ?? "") && x.batch_no.length >= 4) ?? r.items[0];
      setFallback(a ?? null);
      setBatch((cur) => cur ?? (a ? norm(a.batch_no) : null));
    }).catch(() => {});
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const load = useCallback(async (b: string) => {
    setError(null);
    try { setView(await getBlast(b)); } catch (e) { setView(null); setError((e as Error).message); }
  }, []);

  useEffect(() => {
    if (!batch) return;
    setRevealed(new Set());
    setBusy("load");
    load(batch).finally(() => setBusy(null));
    const t = setInterval(() => load(batch), 60000); // countdowns stay honest
    return () => clearInterval(t);
  }, [batch, load]);

  const pick = (b: string) => { setBatch(b); router.replace(`/blast?batch=${b}`, { scroll: false }); };

  const seed = async () => {
    if (!batch) return;
    setBusy("seed");
    try { await blastDemo(batch); await load(batch); getBlastInbox().then(setInbox).catch(() => {}); }
    catch (e) { setError((e as Error).message); } finally { setBusy(null); }
  };
  const clear = async () => {
    if (!batch) return;
    setBusy("clear");
    try { await clearBlastDemo(batch); await load(batch); getBlastInbox().then(setInbox).catch(() => {}); }
    catch (e) { setError((e as Error).message); } finally { setBusy(null); }
  };

  // Send, then light the holders up one by one in the order the server alerted them: soonest dose first.
  const alertAll = async () => {
    if (!batch) return;
    setBusy("alert"); setSending(true);
    try {
      const r = await blastAlert(batch);
      for (const a of r.alerted) {
        setRevealed((s) => new Set(s).add(a.key));
        await new Promise((res) => setTimeout(res, 110));
      }
      await load(batch);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null); setSending(false);
    }
  };

  const s = view?.summary;
  const pending = view ? view.holders.filter((h) => !h.alert && !revealed.has(h.key)).length : 0;
  const done = view ? view.holders.length - pending : 0;
  const a = view?.alert;

  return (
    <main className="blush mx-auto max-w-6xl px-4 pb-24 pt-12 sm:px-6 sm:pt-16">
      <Eyebrow>Recall blast radius</Eyebrow>
      <Heading as="h1" lead="Who has the bad batch." tail="Before the next dose." className="mt-4 text-4xl sm:text-6xl" />
      <p className="mt-4 max-w-2xl text-muted">
        A regulator list says which batch failed. KinCare knows <b className="text-espresso">who is holding it</b>, when each person&apos;s next tablet is due,
        and <b className="text-espresso">whether their vitals changed</b> since they started it. Then it alerts them, soonest dose first.
      </p>

      {/* Batch picker */}
      <div className="mt-8 flex flex-wrap items-center gap-2">
        {inbox.map((b) => (
          <button key={b.batch_norm} onClick={() => pick(b.batch_norm)}
            className={`inline-flex items-center gap-2 rounded-full border px-3.5 py-1.5 text-xs font-medium transition ${batch === b.batch_norm ? "border-espresso bg-espresso text-paper" : "border-line bg-paper text-espresso hover:border-brown/40"}`}>
            <span className={`size-1.5 rounded-full ${b.category === "spurious" ? "bg-danger" : "bg-warn"}`} />
            {b.medicine} <span className="font-mono opacity-60">{b.batch_no}</span>
          </button>
        ))}
        {fallback && !inbox.some((b) => b.batch_norm === norm(fallback.batch_no)) && (
          <button onClick={() => pick(norm(fallback.batch_no))}
            className={`inline-flex items-center gap-2 rounded-full border px-3.5 py-1.5 text-xs font-medium ${batch === norm(fallback.batch_no) ? "border-espresso bg-espresso text-paper" : "border-dashed border-brown/30 bg-paper text-brown"}`}>
            <span className="size-1.5 rounded-full bg-warn" /> {fallback.brand || fallback.product_name} <span className="font-mono opacity-60">{fallback.batch_no}</span>
          </button>
        )}
      </div>

      {error && <p className="mt-4 rounded-2xl bg-danger/10 px-4 py-3 text-sm text-danger">{error}</p>}

      {/* Command panel */}
      <section className="relative mt-6 overflow-hidden rounded-[2.5rem] bg-espresso text-paper shadow-[0_40px_80px_-30px_rgba(42,28,21,0.6)]">
        <div className="pointer-events-none absolute -right-32 -top-32 size-[28rem] rounded-full bg-teal/25 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-40 -left-24 size-[26rem] rounded-full bg-danger/20 blur-3xl" />
        <div className="relative grid gap-8 p-6 sm:p-10 lg:grid-cols-[1.05fr_1fr]">
          <RadarView view={view} revealed={revealed} sending={sending} loading={busy === "load" && !view} />

          <div className="flex flex-col">
            {a ? (
              <>
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <span className={`rounded-full px-2.5 py-1 font-semibold uppercase tracking-wider ${a.category === "spurious" ? "bg-danger text-paper" : "bg-warn/90 text-paper"}`}>
                    {a.category === "spurious" ? "Spurious" : "Not of standard quality"}
                  </span>
                  <span className="rounded-full bg-paper/10 px-2.5 py-1 text-paper/70">CDSCO · {formatMonth(a.alert_month)}</span>
                </div>
                <p className="mt-4 text-3xl font-medium tracking-tight sm:text-4xl">{a.brand || a.product_name}</p>
                <p className="mt-1 font-mono text-sm text-paper/60">Batch {a.batch_no} · {a.manufacturer}</p>
                {a.reason && <p className="mt-3 text-sm text-paper/75"><span className="text-paper/45">Failed: </span>{a.reason}</p>}
                {view?.explain?.[0] && <p className="mt-1 text-sm text-paper/60">{view.explain[0].en}</p>}

                <div className="mt-6 grid grid-cols-2 gap-3">
                  <Kpi icon={Users} label="People holding it" value={s?.holders ?? 0} />
                  <Kpi icon={Clock} label="Next dose within 1 hour" value={s?.due_1h ?? 0} tone={s?.due_1h ? "danger" : undefined} />
                  <Kpi icon={Pill} label="Doses already taken" value={s?.doses_taken ?? 0} />
                  <Kpi icon={HeartPulse} label="Vitals changed since" value={s ? `${s.reacting}/${s.with_vitals}` : "0"} tone={s?.reacting ? "warn" : undefined} />
                </div>

                <div className="mt-auto pt-6">
                  {view && view.holders.length > 0 && (
                    <div className="mb-3">
                      <div className="flex justify-between text-xs text-paper/60"><span>Alerted</span><span className="font-mono">{done} / {view.holders.length}</span></div>
                      <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-paper/10">
                        <motion.div className="h-full rounded-full bg-teal" initial={{ width: 0 }} animate={{ width: `${(done / view.holders.length) * 100}%` }} transition={{ ease: "easeOut" }} />
                      </div>
                    </div>
                  )}
                  {view && view.holders.length === 0 ? (
                    <button onClick={seed} disabled={!!busy} className="inline-flex w-full items-center justify-center gap-2 rounded-full bg-paper px-6 py-3.5 font-medium text-espresso hover:bg-sand">
                      {busy === "seed" ? <Loader2 className="size-4 animate-spin" /> : <FlaskConical className="size-4" />} Load simulated holders for this real batch
                    </button>
                  ) : (
                    <button onClick={alertAll} disabled={!!busy || pending === 0}
                      className="group inline-flex w-full items-center justify-center gap-2 rounded-full bg-danger px-6 py-3.5 font-semibold text-paper shadow-[0_12px_30px_-10px_rgba(196,69,47,0.9)] transition hover:brightness-110 disabled:bg-teal disabled:shadow-none">
                      {busy === "alert" ? <Loader2 className="size-4 animate-spin" /> : pending === 0 ? <Check className="size-4" /> : <Send className="size-4 transition group-hover:translate-x-0.5" />}
                      {pending === 0 ? "Everyone holding this batch has been alerted" : `Alert ${pending} ${pending === 1 ? "person" : "people"} · next dose first`}
                    </button>
                  )}
                  {s && s.simulated > 0 && (
                    <p className="mt-3 flex items-center justify-between gap-2 text-[11px] text-paper/50">
                      <span>{s.simulated} simulated holders (labelled) on a real CDSCO batch. Simulated people are never messaged.</span>
                      <button onClick={clear} disabled={!!busy} className="inline-flex shrink-0 items-center gap-1 underline-offset-2 hover:text-paper hover:underline"><RotateCcw className="size-3" /> Clear</button>
                    </p>
                  )}
                </div>
              </>
            ) : (
              <div className="m-auto text-center text-paper/60">{busy === "load" ? <Loader2 className="mx-auto size-6 animate-spin" /> : "Pick a flagged batch above."}</div>
            )}
          </div>
        </div>
      </section>

      {view && view.holders.length > 0 && (
        <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_1.35fr]">
          <BodyPanel view={view} />
          <Queue holders={view.holders} revealed={revealed} />
        </div>
      )}

      <div className="mt-10 grid gap-4 sm:grid-cols-3">
        {[
          [Radar, "Exposure, not a list", "Purchases, pharmacy sales and watchlists are matched to the flagged batch: these are the people actually holding it."],
          [Clock, "Next dose first", "Each prescription's schedule says who swallows the next tablet soonest. They hear first."],
          [Activity, "Body signal", "Vitals before vs after starting the batch. A change is a reason to see a doctor, never a diagnosis."],
        ].map(([Icon, t, d]) => {
          const I = Icon as typeof Radar;
          return (
            <div key={t as string} className="card rounded-3xl p-5 text-sm">
              <I className="size-5 text-teal" />
              <p className="mt-3 font-medium">{t as string}</p>
              <p className="mt-1 text-muted">{d as string}</p>
            </div>
          );
        })}
      </div>
      <p className="mt-6 text-[11px] text-muted">Alerts go by WhatsApp (and phone notification) to real holders only. Recall alerts are free on every plan. Not medical advice.</p>
    </main>
  );
}

function Kpi({ icon: Icon, label, value, tone }: { icon: typeof Users; label: string; value: number | string; tone?: "danger" | "warn" }) {
  return (
    <div className={`rounded-2xl border p-4 ${tone === "danger" ? "border-danger/40 bg-danger/15" : tone === "warn" ? "border-warn/40 bg-warn/15" : "border-paper/10 bg-paper/5"}`}>
      <Icon className={`size-4 ${tone === "danger" ? "text-[#ff8a73]" : tone === "warn" ? "text-[#f3b56b]" : "text-paper/50"}`} />
      <p className="mt-2 font-mono text-3xl font-semibold tracking-tight">{value}</p>
      <p className="text-[11px] text-paper/55">{label}</p>
    </div>
  );
}

/* ---------------- Radar: everyone holding the batch, placed by time to their next dose ---------------- */

const RINGS = [
  { max: 60, r: 78, label: "1 h" },
  { max: 360, r: 132, label: "6 h" },
  { max: 1440, r: 182, label: "24 h" },
];
const OUTER = 214;

function place(h: Holder, i: number) {
  const m = h.minutes;
  let r: number;
  if (m == null) r = OUTER - 6;
  else {
    const idx = RINGS.findIndex((x) => m <= x.max);
    if (idx === -1) r = RINGS[2].r + 14;
    else {
      const lo = idx === 0 ? 0 : RINGS[idx - 1].max, inner = idx === 0 ? 26 : RINGS[idx - 1].r;
      r = inner + ((m - lo) / (RINGS[idx].max - lo)) * (RINGS[idx].r - inner - 8) + 4;
    }
  }
  const ang = (i * 137.508 * Math.PI) / 180; // golden angle: an even spread with no overlap pattern
  return { x: 230 + r * Math.cos(ang), y: 230 + r * Math.sin(ang) };
}

function dotColor(h: Holder, alerted: boolean) {
  if (alerted) return "#2bb5a5";
  if (h.minutes == null) return "#b9a596";
  if (h.minutes <= 60) return "#ff6b52";
  if (h.minutes <= 360) return "#f3a34a";
  return "#d9c3b4";
}

function RadarView({ view, revealed, sending, loading }: { view: BlastView | null; revealed: Set<string>; sending: boolean; loading: boolean }) {
  const pts = useMemo(() => (view?.holders ?? []).map((h, i) => ({ h, ...place(h, i) })), [view]);
  const [hover, setHover] = useState<Holder | null>(null);
  return (
    <div className="relative mx-auto w-full max-w-[460px]">
      <svg viewBox="0 0 460 460" className="w-full">
        <defs>
          <radialGradient id="core" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#ff6b52" stopOpacity="0.55" />
            <stop offset="100%" stopColor="#ff6b52" stopOpacity="0" />
          </radialGradient>
          <linearGradient id="sweep" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor={sending ? "#2bb5a5" : "#fffcf9"} stopOpacity="0" />
            <stop offset="100%" stopColor={sending ? "#2bb5a5" : "#fffcf9"} stopOpacity={sending ? "0.35" : "0.12"} />
          </linearGradient>
        </defs>
        <circle cx="230" cy="230" r={OUTER} fill="none" stroke="#fffcf9" strokeOpacity="0.08" strokeDasharray="2 6" />
        {RINGS.map((r, i) => (
          <g key={r.label}>
            <circle cx="230" cy="230" r={r.r} fill={i === 0 ? "#ff6b52" : "none"} fillOpacity={i === 0 ? 0.06 : 0} stroke="#fffcf9" strokeOpacity={0.14 - i * 0.03} />
            <text x={230 + r.r * 0.71 + 4} y={230 - r.r * 0.71 - 4} fill="#fffcf9" fillOpacity="0.4" fontSize="10" fontFamily="var(--font-geist-mono)">{r.label}</text>
          </g>
        ))}
        <text x="230" y={230 - OUTER - 4} textAnchor="middle" fill="#fffcf9" fillOpacity="0.3" fontSize="10" fontFamily="var(--font-geist-mono)">no dose schedule</text>
        <line x1="230" y1="16" x2="230" y2="444" stroke="#fffcf9" strokeOpacity="0.05" />
        <line x1="16" y1="230" x2="444" y2="230" stroke="#fffcf9" strokeOpacity="0.05" />
        {/* sweep */}
        <motion.g style={{ originX: "230px", originY: "230px" }} animate={{ rotate: 360 }} transition={{ repeat: Infinity, ease: "linear", duration: sending ? 1.6 : 7 }}>
          <path d={`M230 230 L${230 + OUTER} 230 A${OUTER} ${OUTER} 0 0 0 ${230 + OUTER * Math.cos(-0.6)} ${230 + OUTER * Math.sin(-0.6)} Z`} fill="url(#sweep)" />
        </motion.g>
        <circle cx="230" cy="230" r="46" fill="url(#core)" />
        {pts.map(({ h, x, y }) => {
          const alerted = !!h.alert || revealed.has(h.key);
          const urgent = !alerted && h.minutes != null && h.minutes <= 60;
          const reacting = !!h.body?.flagged?.length;
          return (
            <g key={h.key} onMouseEnter={() => setHover(h)} onMouseLeave={() => setHover(null)} className="cursor-pointer">
              {urgent && (
                <motion.circle cx={x} cy={y} r="7" fill="none" stroke="#ff6b52" initial={{ r: 6, opacity: 0.9 }} animate={{ r: 16, opacity: 0 }}
                  transition={{ repeat: Infinity, duration: 1.6, ease: "easeOut" }} />
              )}
              {reacting && <circle cx={x} cy={y} r="10" fill="none" stroke="#f3a34a" strokeWidth="1.5" strokeDasharray="2 2" />}
              <circle cx={x} cy={y} r={alerted ? 6 : 5.5} fill={dotColor(h, alerted)} stroke="#2a1c15" strokeWidth="1.5" style={{ transition: "fill 0.35s, r 0.35s" }} />
              {alerted && <motion.circle cx={x} cy={y} r="6" fill="none" stroke="#2bb5a5" initial={{ r: 6, opacity: 0.8 }} animate={{ r: 18, opacity: 0 }} transition={{ duration: 0.7 }} />}
            </g>
          );
        })}
        <g>
          <circle cx="230" cy="230" r="22" fill="#2a1c15" stroke="#ff6b52" strokeOpacity="0.7" />
          <foreignObject x="218" y="218" width="24" height="24"><Pill className="size-6 text-[#ff8a73]" /></foreignObject>
        </g>
      </svg>
      {loading && <div className="absolute inset-0 grid place-items-center"><Loader2 className="size-6 animate-spin text-paper/60" /></div>}
      <AnimatePresence>
        {hover && (
          <motion.div initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="pointer-events-none absolute bottom-2 left-1/2 w-64 -translate-x-1/2 rounded-2xl bg-paper px-4 py-3 text-xs text-espresso shadow-xl">
            <p className="font-semibold">{hover.name}{hover.city ? ` · ${hover.city}` : ""}</p>
            <p className="text-muted">{SOURCE[hover.source].label}{hover.doses_taken != null ? ` · ${hover.doses_taken} doses taken` : ""}</p>
            <p className="mt-1 font-medium">{countdown(hover)}</p>
            {hover.body?.flagged?.map((c) => <p key={c.key} className="text-warn">{c.label} {c.before} → {c.after} {c.unit}</p>)}
          </motion.div>
        )}
      </AnimatePresence>
      <div className="mt-2 flex flex-wrap justify-center gap-x-4 gap-y-1 text-[11px] text-paper/55">
        {[["#ff6b52", "dose within 1 h"], ["#f3a34a", "within 6 h"], ["#d9c3b4", "later"], ["#2bb5a5", "alerted"]].map(([c, l]) => (
          <span key={l} className="inline-flex items-center gap-1.5"><span className="size-2 rounded-full" style={{ background: c }} />{l}</span>
        ))}
        <span className="inline-flex items-center gap-1.5"><span className="size-2.5 rounded-full border border-dashed border-[#f3a34a]" />vitals changed</span>
      </div>
    </div>
  );
}

const SOURCE = {
  care: { label: "Bought on prescription", icon: Stethoscope },
  pharmacy: { label: "Pharmacy sale", icon: ShoppingBag },
  watchlist: { label: "Watching this batch", icon: Eye },
} as const;

function countdown(h: Holder) {
  const m = h.minutes;
  if (m == null) return "No dose schedule on KinCare";
  if (m <= 0) return "Next dose due now";
  if (m < 60) return `Next dose in ${m} min`;
  if (m < 1440) return `Next dose in ${Math.floor(m / 60)} h${m % 60 ? ` ${m % 60} m` : ""}`;
  return `Next dose in ${Math.floor(m / 1440)} d`;
}

/* ---------------- Body signal: is the batch hurting people? ---------------- */

function BodyPanel({ view }: { view: BlastView }) {
  const s = view.summary;
  const reacting = view.holders.filter((h) => h.body?.flagged?.length);
  const share = s.with_vitals ? Math.round((s.reacting / s.with_vitals) * 100) : 0;
  return (
    <div className="card rounded-[2rem] p-6">
      <p className="flex items-center gap-2 text-lg font-medium tracking-tight"><HeartPulse className="size-5 text-warn" /> Is this batch hurting anyone?</p>
      {s.with_vitals === 0 ? (
        <p className="mt-2 text-sm text-muted">No holder has vitals logged both before and after starting this batch yet. When they do, KinCare compares them here.</p>
      ) : (
        <>
          <div className="mt-4 flex items-end gap-4">
            <p className="font-mono text-5xl font-semibold tracking-tight text-warn">{share}%</p>
            <p className="pb-1.5 text-sm text-muted">
              of holders with vitals ({s.reacting} of {s.with_vitals}) show {s.top_change ? <b className="text-espresso">{s.top_change.toLowerCase()}</b> : "a change"} beyond the usual range since starting it.
            </p>
          </div>
          <div className="mt-5 space-y-3">
            {reacting.slice(0, 6).map((h) => (
              <div key={h.key}>
                <div className="flex justify-between text-xs"><span className="font-medium">{h.name}</span><span className="text-muted">{h.city}</span></div>
                {h.body!.flagged!.slice(0, 2).map((c) => <Dumbbell key={c.key} c={c} />)}
              </div>
            ))}
          </div>
          <p className="mt-5 rounded-2xl bg-warn-soft/70 px-4 py-3 text-xs text-warn">
            Median of readings in the 2 weeks before starting vs since. A change is a reason to see a doctor, not proof the batch caused it.
            Clusters like this feed <Link href="/signals" className="font-semibold underline">Early Signal</Link>.
          </p>
        </>
      )}
    </div>
  );
}

// Before → after on one line: where the reading sat, where it moved.
function Dumbbell({ c }: { c: VitalChange }) {
  const range = c.key === "pulse" ? [50, 130] : c.key === "spo2" ? [85, 100] : c.key === "bp_sys" ? [90, 190] : [35, 40];
  const pos = (v: number) => `${Math.min(100, Math.max(0, ((v - range[0]) / (range[1] - range[0])) * 100))}%`;
  return (
    <div className="mt-1.5 flex items-center gap-3">
      <span className="w-24 shrink-0 text-[11px] text-muted">{c.label}</span>
      <div className="relative h-5 flex-1">
        <div className="absolute inset-x-0 top-1/2 h-px bg-line" />
        <div className="absolute top-1/2 h-1 -translate-y-1/2 rounded-full bg-gradient-to-r from-clay to-warn"
          style={{ left: c.after > c.before ? pos(c.before) : pos(c.after), width: `calc(${pos(Math.max(c.before, c.after))} - ${pos(Math.min(c.before, c.after))})` }} />
        <span className="absolute top-1/2 size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-clay ring-2 ring-paper" style={{ left: pos(c.before) }} />
        <span className="absolute top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rounded-full bg-warn ring-2 ring-paper" style={{ left: pos(c.after) }} />
      </div>
      <span className="w-28 shrink-0 text-right font-mono text-[11px]">{c.before} → <b className="text-warn">{c.after}</b> {c.unit}</span>
    </div>
  );
}

/* ---------------- Queue: who hears first ---------------- */

function Queue({ holders, revealed }: { holders: Holder[]; revealed: Set<string> }) {
  const [all, setAll] = useState(false);
  const list = all ? holders : holders.slice(0, 10);
  const ref = useRef<HTMLDivElement>(null);
  return (
    <div className="card rounded-[2rem] p-6" ref={ref}>
      <div className="flex items-center justify-between">
        <p className="flex items-center gap-2 text-lg font-medium tracking-tight"><BellRing className="size-5 text-brown" /> Alert order</p>
        <p className="text-xs text-muted">soonest next dose first</p>
      </div>
      <div className="mt-4 divide-y divide-line">
        {list.map((h, i) => {
          const alerted = !!h.alert || revealed.has(h.key);
          const S = SOURCE[h.source];
          const urgent = h.minutes != null && h.minutes <= 60;
          return (
            <motion.div key={h.key} layout className="flex items-center gap-3 py-3">
              <span className="w-5 shrink-0 text-right font-mono text-[11px] text-muted">{i + 1}</span>
              <span className={`grid size-9 shrink-0 place-items-center rounded-full text-sm font-semibold ${alerted ? "bg-teal text-paper" : urgent ? "bg-danger/15 text-danger" : "bg-sand text-brown"}`}>
                {alerted ? <Check className="size-4" /> : h.name.slice(0, 1)}
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{h.name}{h.city ? <span className="font-normal text-muted"> · {h.city}</span> : null}</p>
                <p className="flex items-center gap-1.5 truncate text-[11px] text-muted">
                  <S.icon className="size-3" /> {S.label}{h.doses_taken != null ? ` · ${h.doses_taken} doses taken` : ""}
                  {h.body?.flagged?.[0] && <span className="rounded-full bg-warn-soft px-1.5 font-medium text-warn">{h.body.flagged[0].label.split(" ").pop()} {h.body.flagged[0].delta > 0 ? "+" : ""}{h.body.flagged[0].delta}</span>}
                </p>
              </div>
              <div className="shrink-0 text-right">
                <p className={`text-xs font-medium ${urgent && !alerted ? "text-danger" : "text-espresso"}`}>{countdown(h).replace("Next dose ", "")}</p>
                <p className={`text-[10px] ${alerted ? "text-teal" : "text-muted"}`}>
                  {alerted ? (h.simulated ? "alerted · simulated" : `alerted · ${h.alert?.status ?? "sent"}`) : h.simulated ? "simulated" : "waiting"}
                </p>
              </div>
            </motion.div>
          );
        })}
      </div>
      {holders.length > 10 && (
        <button onClick={() => setAll(!all)} className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-teal hover:underline">
          {all ? "Show fewer" : `Show all ${holders.length}`} <ArrowRight className="size-3.5" />
        </button>
      )}
      {holders.some((h) => h.minutes != null && h.minutes <= 60) && (
        <p className="mt-3 flex items-center gap-1.5 text-xs text-danger"><AlertTriangle className="size-3.5" /> Someone&apos;s next dose is within the hour. They are first in line.</p>
      )}
    </div>
  );
}

export default function BlastPage() {
  return <RoleGate perm="holders.view" role="regulator" what="Recall blast radius"><BlastGated /></RoleGate>;
}
