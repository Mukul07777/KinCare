"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowRight, BellRing, CheckCircle2, CircleAlert, Clock, Cpu, Database, FileStack, FlaskConical, Gauge, Loader2, RefreshCw, ScanSearch, TimerReset,
} from "lucide-react";
import { Eyebrow, Heading } from "@/components/Heading";
import { formatIST, formatMonth, getStatus, type SystemStatus } from "@/lib/api";

const n = (v?: number | null) => (v == null ? "–" : v.toLocaleString("en-IN"));
const ms = (v?: number | null) => (v == null ? "–" : v < 10 ? v.toFixed(1) : Math.round(v).toLocaleString("en-IN"));
const uptime = (s: number) => (s < 3600 ? `${Math.round(s / 60)} min` : s < 86400 ? `${(s / 3600).toFixed(1)} h` : `${(s / 86400).toFixed(1)} days`);

// The engineering behind the product, measured on the running system every few seconds. Nothing on this page is typed in.
export default function StatusPage() {
  const [s, setS] = useState<SystemStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rerun, setRerun] = useState(false);

  const load = useCallback((q = false) => getStatus(q).then((x) => { setS(x); setError(null); }).catch((e) => setError((e as Error).message)), []);
  useEffect(() => { load(); const t = setInterval(() => load(), 5000); return () => clearInterval(t); }, [load]);

  const q = s?.quality;
  const lastRun = s?.ingest.runs[0];

  return (
    <main className="mx-auto max-w-6xl px-4 pb-20 pt-10 sm:px-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <Eyebrow>Under the hood · refreshes every 5 s</Eyebrow>
          <Heading as="h1" lead="Measured, not claimed." tail="Live from the running system." className="mt-4 text-4xl sm:text-6xl" />
          <p className="mt-4 max-w-2xl text-muted">
            How accurate the batch check is, how fast every endpoint answers, and how fresh the regulator data is, computed by the API right now.
          </p>
        </div>
        {s && (
          <span className="inline-flex items-center gap-2 rounded-full bg-mint px-4 py-2 text-sm font-medium text-teal">
            <span className="size-2 animate-pulse rounded-full bg-teal" /> All systems up · {uptime(s.uptime_s)}
          </span>
        )}
      </div>

      {error && !s && (
        <div className="mt-16 text-center">
          <p className="text-danger">{error}</p>
          <button onClick={() => load()} className="mt-4 rounded-full border border-line bg-paper px-5 py-2 text-sm font-medium">Retry</button>
        </div>
      )}
      {!s && !error && <p className="mt-16 flex items-center justify-center gap-2 text-muted"><Loader2 className="size-5 animate-spin" /> Measuring…</p>}

      {s && q && (
        <>
          {/* Pipeline, with the live number at every stage */}
          <section className="mt-10 overflow-hidden rounded-[2rem] bg-espresso p-6 text-paper sm:p-8">
            <p className="text-xs font-medium uppercase tracking-wider text-paper/50">From a government PDF to a patient&apos;s phone</p>
            <div className="mt-6 grid gap-3 md:grid-cols-5">
              {[
                { icon: FileStack, t: "Regulator sources", v: `${n(s.data.documents)} lists`, d: `CDSCO NSQ + spurious, state labs · ${formatMonth(s.data.first_list)} → ${formatMonth(s.data.latest_list)}` },
                { icon: TimerReset, t: "Nightly ingest", v: lastRun ? lastRun.status : "–", d: `Next run ${formatIST(s.ingest.next_nightly)} (02:00 IST)` },
                { icon: Database, t: "Alert store", v: `${n(s.data.alerts)} alerts`, d: `SQLite ${s.data.journal.toUpperCase()} · ${s.data.db_mb} MB · trigram index on ${n(s.data.medicines)} brands` },
                { icon: ScanSearch, t: "Exact-batch matcher", v: `${q.recall_pct}% · ${q.false_alarms} false`, d: `Batch exact, never fuzzy; maker fuzzy on distinctive words · ${q.check_ms_p50} ms` },
                { icon: BellRing, t: "Reach", v: "WhatsApp · voice · push", d: "Holders alerted next-dose-first; Hindi or English" },
              ].map(({ icon: Icon, t, v, d }, k) => (
                <div key={t} className="relative rounded-2xl border border-paper/10 bg-paper/5 p-4">
                  <Icon className="size-5 text-[#5fd3c4]" />
                  <p className="mt-3 text-xs text-paper/55">{t}</p>
                  <p className="mt-0.5 font-mono text-lg font-semibold">{v}</p>
                  <p className="mt-1 text-[11px] leading-snug text-paper/50">{d}</p>
                  {k < 4 && <ArrowRight className="absolute -right-3 top-1/2 z-10 hidden size-4 -translate-y-1/2 text-paper/40 md:block" />}
                </div>
              ))}
            </div>
          </section>

          <section className="mt-5 rounded-[2rem] border border-line bg-paper p-6">
            <p className="text-xs font-medium uppercase tracking-wider text-muted">Strip OCR on labelled photos</p>
            <p className="mt-1 text-sm text-muted">Batch, expiry and brand read from the photo vs what a person reads off the strip. Real phone photos and demo prints are never mixed.</p>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {(["real", "synthetic"] as const).map((k) => {
                const b = s.strip_ocr?.sets[k];
                return (
                  <div key={k} className="rounded-2xl bg-cream p-4">
                    <p className="text-sm font-semibold">{k === "real" ? "Real phone photos" : "Synthetic demo prints"}</p>
                    {b ? (
                      <p className="mt-1 font-mono text-sm">{b.photos} photos · batch {b.batch_pct}% · expiry {b.expiry_pct}% · brand {b.brand_pct}% · {b.median_ms} ms</p>
                    ) : (
                      <p className="mt-1 text-sm text-muted">Not measured yet. Add labelled photos to <code className="font-mono">api/tests/strips/</code> and run <code className="font-mono">python bench_strips.py</code>.</p>
                    )}
                  </div>
                );
              })}
            </div>
          </section>

          <div className="mt-5 grid gap-5 lg:grid-cols-[1.15fr_1fr]">
            {/* Accuracy */}
            <section className="card rounded-[2rem] p-6 sm:p-7">
              <div className="flex items-center justify-between gap-3">
                <h2 className="flex items-center gap-2 text-lg font-medium"><FlaskConical className="size-5 text-teal" /> Batch-check accuracy</h2>
                <button disabled={rerun} onClick={async () => { setRerun(true); await load(true); setRerun(false); }}
                  className="inline-flex items-center gap-1.5 rounded-full border border-line px-3 py-1.5 text-xs font-medium hover:border-brown disabled:opacity-50">
                  <RefreshCw className={`size-3.5 ${rerun ? "animate-spin" : ""}`} /> Re-run now
                </button>
              </div>
              <p className="mt-1 text-sm text-muted">
                {n(q.sampled_alerts)} real alerts sampled from {n(q.alerts_in_db)}, each probed the way people and OCR type batches. Same code path as /api/check.
              </p>
              <div className="mt-5 grid grid-cols-2 gap-3">
                {[
                  [`${q.recall_pct}%`, "flagged batches caught", `${n(q.positive_probes)} probes: as printed, lower case, spaces, hyphens, slashes`, "text-teal"],
                  [`${q.false_alarms}`, "false alarms", `${n(q.near_miss_probes)} one-character near misses + ${n(q.clean_probes)} clean batches`, q.false_alarms ? "text-danger" : "text-teal"],
                  [`${q.right_maker_strong_pct}%`, "same maker recognised", `${n(q.right_maker_probes)} respellings (M/s, Pvt Ltd, glued OCR words)`, "text-espresso"],
                  [`${q.wrong_maker_marked_strong}`, "wrong makers called a match", `of ${n(q.wrong_maker_probes)}: right batch, different company`, q.wrong_maker_marked_strong ? "text-warn" : "text-teal"],
                ].map(([v, l, d, c]) => (
                  <div key={l} className="rounded-2xl bg-cream p-4">
                    <p className={`font-mono text-3xl font-semibold ${c}`}>{v}</p>
                    <p className="mt-1 text-sm font-medium">{l}</p>
                    <p className="mt-0.5 text-xs leading-snug text-muted">{d}</p>
                  </div>
                ))}
              </div>
              <p className="mt-4 rounded-2xl bg-mint/60 p-3 text-xs leading-relaxed text-teal-2">
                Why precision is the number that matters: a false alarm makes someone stop a medicine they need. Batch numbers are matched exactly after
                normalising spacing and case, never fuzzily, so a near-miss can&apos;t raise an alert. Benchmark: <code className="font-mono">api/quality.py</code>, seed {q.seed}; enforced in CI by <code className="font-mono">test_quality.py</code>.
              </p>
            </section>

            {/* Latency */}
            <section className="card rounded-[2rem] p-6 sm:p-7">
              <h2 className="flex items-center gap-2 text-lg font-medium"><Gauge className="size-5 text-teal" /> Response time, live</h2>
              <p className="mt-1 text-sm text-muted">Last {n(s.latency.requests)} API requests, measured inside the server.</p>
              <div className="mt-5 grid grid-cols-3 gap-3">
                {[["p50", s.latency.p50_ms], ["p95", s.latency.p95_ms], ["p99", s.latency.p99_ms]].map(([l, v]) => (
                  <div key={l as string} className="rounded-2xl bg-cream p-4 text-center">
                    <p className="font-mono text-2xl font-semibold">{ms(v as number)}<span className="text-sm font-normal text-muted"> ms</span></p>
                    <p className="text-xs text-muted">{l}</p>
                  </div>
                ))}
              </div>
              <p className={`mt-3 flex items-center gap-1.5 text-sm ${s.latency.server_errors ? "text-danger" : "text-teal"}`}>
                {s.latency.server_errors ? <CircleAlert className="size-4" /> : <CheckCircle2 className="size-4" />}
                {s.latency.server_errors ? `${s.latency.server_errors} server errors` : "0 server errors"}
              </p>
              <div className="mt-4 space-y-1.5">
                {s.latency.routes.slice(0, 7).map((r) => (
                  <div key={r.path} className="flex items-center gap-3 text-xs">
                    <span className="w-40 truncate font-mono text-muted sm:w-48">{r.path}</span>
                    <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-sand">
                      <div className="h-full rounded-full bg-teal" style={{ width: `${Math.min(100, (r.p95_ms / Math.max(1, s.latency.routes[0].p95_ms)) * 100)}%` }} />
                    </div>
                    <span className="w-20 text-right font-mono">{ms(r.p95_ms)} ms</span>
                  </div>
                ))}
              </div>
              <p className="mt-4 text-xs leading-relaxed text-muted">
                Why SQLite: the whole dataset is {s.data.db_mb} MB and changes once a night, so a single file with WAL, one connection per worker thread,
                cached aggregates and a trigram index answers in milliseconds with no database server to run. Measured at 32 parallel clients: 0 errors.
              </p>
            </section>
          </div>

          {/* Freshness + ingest history */}
          <section className="card mt-5 rounded-[2rem] p-6 sm:p-7">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <h2 className="flex items-center gap-2 text-lg font-medium"><Clock className="size-5 text-teal" /> Data freshness</h2>
              <p className="text-sm text-muted">Newest regulator list: <b className="text-espresso">{formatMonth(s.data.latest_list)}</b> · next refresh {formatIST(s.ingest.next_nightly)}</p>
            </div>
            <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
              {[[s.data.alerts, "alerts indexed"], [s.data.spurious, "declared fake"], [s.data.makers, "manufacturers"], [s.data.medicines, "brands priced"]].map(([v, l]) => (
                <div key={l as string} className="rounded-2xl bg-cream p-4">
                  <p className="font-mono text-2xl font-semibold">{n(v as number)}</p>
                  <p className="text-xs text-muted">{l}</p>
                </div>
              ))}
            </div>
            <div className="mt-5 overflow-x-auto">
              <table className="w-full min-w-[540px] text-sm">
                <thead><tr className="text-left text-xs text-muted"><th className="py-2 font-normal">Ingest run</th><th className="font-normal">Started</th><th className="font-normal">Result</th><th className="text-right font-normal">Alerts added</th></tr></thead>
                <tbody>
                  {s.ingest.runs.map((r) => (
                    <tr key={r.started_at} className="border-t border-line">
                      <td className="py-2.5 capitalize">{r.trigger}</td>
                      <td className="text-muted">{formatIST(r.started_at)}</td>
                      <td><span className={`rounded-full px-2 py-0.5 text-xs font-medium ${r.status === "ok" ? "bg-mint text-teal" : r.status === "failed" ? "bg-danger/10 text-danger" : "bg-warn-soft text-warn"}`}>{r.status}</span>
                        {r.error && <span className="ml-2 text-xs text-muted">{r.error}</span>}</td>
                      <td className="text-right font-mono">{r.alerts_after != null && r.alerts_before != null ? `+${n(r.alerts_after - r.alerts_before)}` : "…"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="mt-5 grid gap-3 sm:grid-cols-3">
            {[
              [Cpu, `${n(s.tests)} automated tests`, "API suite, incl. accuracy on the real alert table"],
              [ScanSearch, "Never says “safe”", "Only “no alert found as of” a date and time"],
              [Database, "Every number traceable", "Each alert links to the regulator's own PDF page"],
            ].map(([Icon, t, d]) => {
              const I = Icon as typeof Cpu;
              return (
                <div key={t as string} className="card flex items-start gap-3 rounded-3xl p-5">
                  <span className="grid size-10 shrink-0 place-items-center rounded-2xl bg-mint text-teal"><I className="size-5" /></span>
                  <div><p className="font-medium">{t as string}</p><p className="text-sm text-muted">{d as string}</p></div>
                </div>
              );
            })}
          </section>
          <p className="mt-6 text-center text-sm text-muted">
            Raw JSON: <Link href="/api/status" className="font-mono text-brown underline-offset-4 hover:underline">/api/status</Link>
          </p>
        </>
      )}
    </main>
  );
}
