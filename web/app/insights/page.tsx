"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { AlertTriangle, Info } from "lucide-react";
import { Eyebrow, Heading } from "@/components/Heading";
import { formatMonth, getInsights, type Insights } from "@/lib/api";

const SEV_COLOR = { critical: "bg-danger", high: "bg-[#d0703c]", medium: "bg-brown", low: "bg-clay" } as const;

function Bars({ items, max, color = "bg-brown", limit = 10 }: { items: { name: string; n: number }[]; max?: number; color?: string; limit?: number }) {
  const top = items.filter((i) => i.name !== "Other").slice(0, limit);
  const m = max ?? Math.max(1, ...top.map((i) => i.n));
  return (
    <div className="space-y-2.5">
      {top.map((i, k) => (
        <div key={i.name} className="grid grid-cols-[minmax(0,9rem)_1fr_3rem] items-center gap-3 text-sm">
          <span className="truncate">{i.name}</span>
          <div className="h-2.5 overflow-hidden rounded-full bg-sand">
            <motion.div initial={{ width: 0 }} whileInView={{ width: `${(i.n / m) * 100}%` }} viewport={{ once: true }} transition={{ duration: 0.7, delay: k * 0.03 }} className={`h-full rounded-full ${color}`} />
          </div>
          <span className="text-right font-mono text-xs text-muted">{i.n.toLocaleString("en-IN")}</span>
        </div>
      ))}
    </div>
  );
}

export default function InsightsPage() {
  const [d, setD] = useState<Insights | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    getInsights().then(setD).catch((e) => setError(e.message));
  }, []);

  const maxYear = Math.max(1, ...(d?.by_year.map((y) => y.n) ?? [1]));

  return (
    <main className="blush mx-auto max-w-6xl px-4 pt-12 sm:px-6 sm:pt-16">
      <div className="grid items-end gap-6 md:grid-cols-2">
        <div>
          <Eyebrow>National insights</Eyebrow>
          <Heading as="h1" lead="India’s medicine quality," tail="in one view." className="mt-4 text-4xl sm:text-6xl" />
        </div>
        <p className="max-w-sm text-muted md:ml-auto">
          Every NSQ and spurious finding CDSCO and state labs have published since 2019, categorised in plain language.
        </p>
      </div>

      {error && <p className="mt-6 text-danger">{error}</p>}
      {!d && !error && <p className="mt-10 text-muted">Loading national data…</p>}

      {d && (
        <>
          <div className="mt-10 grid grid-cols-2 gap-3 lg:grid-cols-4">
            {[
              { l: "Failed samples since 2019", v: d.total },
              { l: "Critical: toxic or likely fake", v: d.critical_total, hot: true },
              { l: "Injections that failed", v: d.by_form.find((f) => f.name === "Injection")?.n ?? 0 },
              { l: "Contamination / sterility", v: d.by_failure.find((f) => f.key === "sterility")?.n ?? 0 },
            ].map((c) => (
              <div key={c.l} className={`card rounded-3xl p-5 ${c.hot ? "bg-danger text-paper" : ""}`}>
                <p className={`text-sm ${c.hot ? "text-paper/80" : "text-muted"}`}>{c.l}</p>
                <p className="mt-2 text-4xl font-medium tracking-tight sm:text-5xl">{c.v.toLocaleString("en-IN")}</p>
              </div>
            ))}
          </div>

          <div className="card mt-4 rounded-3xl p-6">
            <p className="font-medium">Failed samples published per year</p>
            <div className="mt-5 flex h-40 items-end gap-3">
              {d.by_year.map((y, i) => (
                <div key={y.name} className="flex flex-1 flex-col items-center gap-1.5">
                  <span className="text-xs text-muted">{y.n.toLocaleString("en-IN")}</span>
                  <motion.div initial={{ height: 0 }} whileInView={{ height: `${(y.n / maxYear) * 120}px` }} viewport={{ once: true }} transition={{ duration: 0.7, delay: i * 0.05 }}
                    className={`w-full rounded-t-xl ${i === d.by_year.length - 1 ? "bg-brown" : "bg-clay"}`} />
                  <span className="text-xs text-muted">{y.name}</span>
                </div>
              ))}
            </div>
            <p className="mt-3 text-xs text-muted">The current year covers months published so far.</p>
          </div>

          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <div className="card rounded-3xl p-6">
              <p className="font-medium">Why samples failed</p>
              <p className="mb-5 text-xs text-muted">A sample can fail more than one test.</p>
              <div className="space-y-2.5">
                {d.by_failure.filter((f) => f.key !== "other").map((f) => (
                  <div key={f.key} className="grid grid-cols-[minmax(0,10rem)_1fr_3rem] items-center gap-3 text-sm">
                    <span className="flex items-center gap-2 truncate"><span className={`size-2 shrink-0 rounded-full ${SEV_COLOR[f.severity]}`} />{f.name}</span>
                    <div className="h-2.5 overflow-hidden rounded-full bg-sand">
                      <motion.div initial={{ width: 0 }} whileInView={{ width: `${(f.n / d.by_failure[0].n) * 100}%` }} viewport={{ once: true }} className={`h-full rounded-full ${SEV_COLOR[f.severity]}`} />
                    </div>
                    <span className="text-right font-mono text-xs text-muted">{f.n.toLocaleString("en-IN")}</span>
                  </div>
                ))}
              </div>
              <div className="mt-4 flex flex-wrap gap-3 text-[11px] text-muted">
                {Object.entries(SEV_COLOR).map(([k, c]) => <span key={k} className="flex items-center gap-1"><span className={`size-2 rounded-full ${c}`} />{k}</span>)}
              </div>
            </div>
            <div className="card rounded-3xl p-6">
              <p className="font-medium">Which medicine groups fail most</p>
              <p className="mb-5 text-xs text-muted">Grouped from the medicine name; unrecognised names are left out.</p>
              <Bars items={d.by_group} />
            </div>
            <div className="card rounded-3xl p-6">
              <p className="font-medium">Where failing samples were tested</p>
              <p className="mb-5 text-xs text-muted">State of the testing laboratory, not where the medicine was sold. Central labs test samples from many states.</p>
              <Bars items={d.by_state} limit={12} color="bg-mocha" />
            </div>
            <div className="card rounded-3xl p-6">
              <p className="font-medium">By dosage form</p>
              <p className="mb-5 text-xs text-muted">Failed injections and eye drops carry the highest infection risk.</p>
              <Bars items={d.by_form} color="bg-brown-2" />
            </div>
          </div>

          <div className="mt-4 overflow-hidden rounded-[2rem] bg-espresso p-6 text-paper sm:p-8">
            <p className="flex items-center gap-2 font-medium"><AlertTriangle className="size-5 text-[#ff8a6b]" /> Most recent critical findings</p>
            <p className="mt-1 text-sm text-paper/60">Toxic contaminants (DEG/EG) and samples declared spurious.</p>
            <div className="mt-5 divide-y divide-paper/10">
              {d.critical_recent.map((c, i) => (
                <div key={i} className="grid gap-1 py-3 sm:grid-cols-[1.3fr_2fr_auto] sm:items-center sm:gap-4">
                  <p className="font-medium">{c.product_name}</p>
                  <p className="truncate text-sm text-paper/60">{c.reason}</p>
                  <span className="text-xs text-paper/60">{c.type} · {formatMonth(c.month)}</span>
                </div>
              ))}
            </div>
          </div>

          <p className="mt-4 flex items-start gap-2 text-xs text-muted">
            <Info className="mt-0.5 size-3.5 shrink-0" />
            Counts of published findings only. More samples from a state, maker or drug group can mean more testing, not worse quality.
          </p>
        </>
      )}
    </main>
  );
}
