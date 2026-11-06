"use client";

import { RoleGate } from "@/components/RoleGate";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Activity, ArrowRight, Download, Home, Loader2, Printer, QrCode, RotateCcw, ShieldAlert, Siren, Sparkles, Stethoscope } from "lucide-react";
import { Eyebrow, Heading } from "@/components/Heading";
import {
  blastDemo, clearBlastDemo, clearRadarDemo, formatMonth, getController, pvpiCsvUrl, seedRadarDemo, signalsCsvUrl,
  type Controller, type ControllerAction,
} from "@/lib/api";

const DEMO_BATCH = "AT25-0938A"; // Namik-MR, real state NSQ alert (Sep 2026)
const KIND = {
  recall: { icon: Home, label: "Batch in homes" },
  counterfeit: { icon: QrCode, label: "Copied pack code" },
  signal: { icon: Activity, label: "Patient signal" },
  checkin: { icon: Stethoscope, label: "Check-ins" },
} as const;

function Controller() {
  const [state, setState] = useState("");
  const [d, setD] = useState<Controller | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => getController(state || undefined).then(setD).catch((e) => setError((e as Error).message)), [state]);
  useEffect(() => { load(); }, [load]);

  const demo = async (on: boolean) => {
    setBusy(true); setError(null);
    try {
      if (on) { await blastDemo(DEMO_BATCH, 24); await seedRadarDemo(); }
      else { await clearBlastDemo(DEMO_BATCH); await clearRadarDemo(); }
      await load();
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };

  const k = d?.kpis;
  const change = k && k.alerts_prev_12m ? Math.round(((k.alerts_12m - k.alerts_prev_12m) / k.alerts_prev_12m) * 100) : null;

  return (
    <main className="mx-auto max-w-6xl px-4 pb-20 pt-10 sm:px-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <Eyebrow>State drug controller</Eyebrow>
          <Heading as="h1" lead="Every failed batch," tail="followed to the home." className="mt-4 text-4xl sm:text-5xl" />
          <p className="mt-3 max-w-2xl text-muted">The regulator&apos;s own alerts, joined with what KinCare sees on the ground: who still holds a flagged batch, copied pack codes, and patients reporting problems before any list does.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2 print:hidden">
          <select value={state} onChange={(e) => setState(e.target.value)} className="rounded-full border border-line bg-paper px-4 py-2.5 text-sm font-medium outline-none">
            <option value="">All India</option>
            {d?.states.map((s) => <option key={s.name} value={s.name}>{s.name} ({s.n.toLocaleString("en-IN")})</option>)}
          </select>
          <button onClick={() => window.print()} className="inline-flex items-center gap-1.5 rounded-full border border-line bg-paper px-4 py-2.5 text-sm font-medium"><Printer className="size-4" /> Print</button>
        </div>
      </div>

      {!d && error ? (
        <div className="mt-16 text-center">
          <p className="text-danger">{error}</p>
          <button onClick={() => { setError(null); load(); }} className="mt-4 rounded-full border border-line bg-paper px-5 py-2 text-sm font-medium">Retry</button>
        </div>
      ) : !d ? <p className="mt-16 flex items-center justify-center gap-2 text-muted"><Loader2 className="size-5 animate-spin" /> Loading…</p> : (
        <>
          <p className="mt-4 text-xs text-muted">{d.state ? `Testing labs in ${d.state}` : "All testing labs"} · alerts to {formatMonth(d.as_of)} · {d.scope_note}</p>

          {/* KPIs */}
          <div className="mt-5 grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-7">
            <Kpi v={k!.alerts_12m.toLocaleString("en-IN")} l="alerts, last 12 months" s={change == null ? "" : `${change > 0 ? "+" : ""}${change}% vs year before`} tone={change != null && change > 0 ? "bad" : undefined} />
            <Kpi v={k!.spurious_12m} l="declared fake (12 m)" tone={k!.spurious_12m ? "bad" : undefined} />
            <Kpi v={k!.critical_24m} l="critical findings (24 m)" s="contamination, toxic, fake" />
            <Kpi v={k!.median_lag_months == null ? "–" : `${k!.median_lag_months} mo`} l="made → listed (median)" s={`${k!.lag_sample.toLocaleString("en-IN")} alerts`} />
            <Kpi v={`${k!.people_alerted}/${k!.people_holding}`} l="holders alerted" s={`${k!.batches_in_homes} flagged batches in homes`} tone={k!.people_holding > k!.people_alerted ? "warn" : "ok"} />
            <Kpi v={k!.copied_codes} l="copied pack codes" tone={k!.copied_codes ? "bad" : undefined} />
            <Kpi v={k!.signals} l="patient signals" s={k!.urgent_checkins ? `${k!.urgent_checkins} urgent check-ins` : ""} tone={k!.signals ? "warn" : undefined} />
          </div>

          {/* Action queue + trend */}
          <div className="mt-5 grid gap-5 lg:grid-cols-[1.25fr_1fr]">
            <div className="card rounded-[2rem] p-6">
              <p className="flex items-center gap-2 text-lg font-medium"><Siren className="size-5 text-danger" /> Action queue</p>
              <p className="text-xs text-muted">Most urgent first: fakes and doses due within 24 h, then the rest.</p>
              <div className="mt-4 space-y-2">
                {d.actions.length === 0 && <p className="rounded-2xl bg-cream/70 p-5 text-sm text-muted">Nothing on the ground needs action. Load the demo below to see a live queue.</p>}
                {d.actions.map((a, i) => <Action key={i} a={a} />)}
              </div>
            </div>
            <div className="card rounded-[2rem] p-6">
              <p className="text-lg font-medium">Alerts per month</p>
              <p className="text-xs text-muted">Last 18 months, {d.state ?? "all India"}</p>
              <Bars data={d.trend.map((t) => ({ name: t.month.slice(2), n: t.n }))} />
            </div>
          </div>

          {/* What fails, groups, makers */}
          <div className="mt-5 grid gap-5 md:grid-cols-3">
            <ListCard title="What fails (24 m)" rows={d.failures} tone="#c4452f" />
            <ListCard title="Drug groups (24 m)" rows={d.groups} tone="#0f766e" />
            <ListCard title="Makers with most alerts (24 m)" rows={d.makers} tone="#8a4b2c" note="A count of published alerts, not a quality rating. Bigger makers are sampled more." />
          </div>

          {/* Batches in homes */}
          <div className="card mt-5 rounded-[2rem] p-6">
            <p className="text-lg font-medium">Flagged batches still in homes</p>
            <p className="text-xs text-muted">From KinCare purchases, pharmacy sales and watchlists, all India.</p>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[640px] text-sm">
                <thead><tr className="text-left text-xs text-muted"><th className="py-2">Medicine</th><th>Batch</th><th>List</th><th className="text-right">Holders</th><th className="text-right">Alerted</th><th className="text-right">Due 24 h</th><th /></tr></thead>
                <tbody className="divide-y divide-line">
                  {d.held.length === 0 && <tr><td colSpan={7} className="py-6 text-center text-muted">No flagged batch is held by anyone KinCare knows.</td></tr>}
                  {d.held.map((h) => (
                    <tr key={h.batch_norm}>
                      <td className="py-2.5 font-medium">{h.medicine}{h.simulated ? <span className="ml-2 rounded-full bg-sand px-2 py-0.5 text-[10px] font-semibold text-brown">SIMULATED</span> : null}</td>
                      <td className="font-mono">{h.batch_no}</td>
                      <td><span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${h.category === "spurious" ? "bg-danger text-paper" : "bg-warn-soft text-warn"}`}>{h.category}</span> <span className="text-xs text-muted">{h.month}</span></td>
                      <td className="text-right font-mono">{h.holders}</td>
                      <td className="text-right font-mono">{h.alerted}</td>
                      <td className={`text-right font-mono ${h.due_24h ? "font-semibold text-danger" : ""}`}>{h.due_24h}</td>
                      <td className="text-right"><Link href={`/blast?batch=${encodeURIComponent(h.batch_norm)}`} className="inline-flex items-center gap-1 text-xs font-semibold text-brown">Blast radius <ArrowRight className="size-3.5" /></Link></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Exports + demo */}
          <div className="mt-5 grid gap-5 md:grid-cols-2 print:hidden">
            <div className="card rounded-3xl p-5 text-sm">
              <p className="font-medium">Reports</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <a href={pvpiCsvUrl()} className="inline-flex items-center gap-1.5 rounded-full border border-line px-4 py-2 text-xs font-semibold"><Download className="size-3.5" /> Patient reactions (PvPI CSV)</a>
                <a href={signalsCsvUrl()} className="inline-flex items-center gap-1.5 rounded-full border border-line px-4 py-2 text-xs font-semibold"><Download className="size-3.5" /> Batch signals CSV</a>
                <Link href="/insights" className="inline-flex items-center gap-1.5 rounded-full border border-line px-4 py-2 text-xs font-semibold"><ShieldAlert className="size-3.5" /> National insights</Link>
              </div>
            </div>
            <div className="clinical rounded-3xl p-5 text-sm">
              <p className="flex items-center gap-2 font-medium text-teal-2"><Sparkles className="size-4" /> Stage demo</p>
              <p className="mt-1 text-muted">Adds labelled, simulated ground data: 24 holders of Namik-MR batch {DEMO_BATCH} (a real state NSQ alert) and a copied pack-code ring.</p>
              <div className="mt-3 flex gap-2">
                <button onClick={() => demo(true)} disabled={busy} className="inline-flex items-center gap-1.5 rounded-full bg-teal px-4 py-2 text-xs font-semibold text-paper disabled:opacity-50">{busy ? <Loader2 className="size-3.5 animate-spin" /> : <Sparkles className="size-3.5" />} Load demo</button>
                <button onClick={() => demo(false)} disabled={busy} className="inline-flex items-center gap-1.5 rounded-full border border-line bg-paper px-4 py-2 text-xs font-semibold"><RotateCcw className="size-3.5" /> Clear</button>
              </div>
              {error && <p className="mt-2 text-xs text-danger">{error}</p>}
            </div>
          </div>
        </>
      )}
    </main>
  );
}

function Kpi({ v, l, s, tone }: { v: string | number; l: string; s?: string; tone?: "bad" | "warn" | "ok" }) {
  const cls = tone === "bad" ? "bg-danger text-paper" : tone === "warn" ? "bg-warn-soft" : tone === "ok" ? "bg-mint" : "";
  return (
    <div className={`card rounded-3xl p-4 ${cls}`}>
      <p className="font-mono text-2xl font-semibold tracking-tight">{v}</p>
      <p className={`mt-1 text-xs ${tone === "bad" ? "text-paper/85" : "text-muted"}`}>{l}</p>
      {s && <p className={`mt-0.5 text-[11px] ${tone === "bad" ? "text-paper/70" : "text-muted"}`}>{s}</p>}
    </div>
  );
}

function Action({ a }: { a: ControllerAction }) {
  const K = KIND[a.kind];
  return (
    <Link href={a.href} className={`flex items-start gap-3 rounded-2xl p-3 transition hover:-translate-y-0.5 ${a.severity === 0 ? "bg-danger/10" : "bg-cream/70"}`}>
      <span className={`grid size-9 shrink-0 place-items-center rounded-xl ${a.severity === 0 ? "bg-danger text-paper" : "bg-sand text-brown"}`}><K.icon className="size-4" /></span>
      <span className="min-w-0 flex-1">
        <span className="block text-sm font-medium">{a.title}</span>
        <span className="block text-xs text-muted">{K.label} · {a.detail}{a.simulated ? " · simulated demo" : ""}</span>
      </span>
      <ArrowRight className="mt-2 size-4 shrink-0 text-muted" />
    </Link>
  );
}

function Bars({ data }: { data: { name: string; n: number }[] }) {
  const max = Math.max(1, ...data.map((x) => x.n));
  return (
    <div className="mt-4 flex h-48 items-end gap-1">
      {data.map((x, i) => (
        <div key={x.name} className="flex flex-1 flex-col items-center gap-1" title={`${x.name}: ${x.n}`}>
          <span className="text-[9px] text-muted">{i === data.length - 1 || x.n === max ? x.n : ""}</span>
          <div className={`w-full rounded-t-md ${i === data.length - 1 ? "bg-brown" : "bg-clay"}`} style={{ height: `${(x.n / max) * 150 + 2}px` }} />
          <span className="text-[9px] text-muted">{i % 3 === 0 || i === data.length - 1 ? x.name : ""}</span>
        </div>
      ))}
    </div>
  );
}

function ListCard({ title, rows, tone, note }: { title: string; rows: { name: string; n: number }[]; tone: string; note?: string }) {
  const max = Math.max(1, ...rows.map((r) => r.n));
  return (
    <div className="card rounded-[2rem] p-6">
      <p className="font-medium">{title}</p>
      <div className="mt-3 space-y-2.5">
        {rows.length === 0 && <p className="text-sm text-muted">No data.</p>}
        {rows.map((r) => (
          <div key={r.name}>
            <div className="flex justify-between gap-2 text-xs"><span className="truncate">{r.name}</span><span className="font-mono">{r.n}</span></div>
            <div className="mt-1 h-1.5 rounded-full bg-sand"><div className="h-full rounded-full" style={{ width: `${(r.n / max) * 100}%`, background: tone }} /></div>
          </div>
        ))}
      </div>
      {note && <p className="mt-3 text-[11px] text-muted">{note}</p>}
    </div>
  );
}

export default function ControllerPage() {
  return <RoleGate perm="controller.view" role="regulator" what="Drug controller dashboard"><Controller /></RoleGate>;
}
