"use client";

import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Activity, Download, FlaskConical, MapPin, RefreshCw, Siren } from "lucide-react";
import { Eyebrow, Heading } from "@/components/Heading";
import { ReportForm } from "@/components/ReportForm";
import { formatIST, formatMonth, getSignals, signalsCsvUrl, type Signal, type Signals } from "@/lib/api";

const LEVEL = {
  urgent: { label: "Urgent: serious symptoms", cls: "bg-danger text-paper" },
  signal: { label: "Signal: test this batch", cls: "bg-brown text-paper" },
  watch: { label: "Watching", cls: "bg-sand text-brown" },
} as const;

function SignalCard({ s }: { s: Signal }) {
  const max = Math.max(1, ...s.symptoms.map((x) => x.n));
  return (
    <motion.div layout initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="card rounded-3xl p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-mono text-2xl font-medium tracking-tight">{s.batch}</p>
          <p className="text-sm text-muted">{[s.brand, s.maker].filter(Boolean).join(" · ") || "Brand not given"}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {s.simulated && <span className="rounded-full border border-line px-3 py-1 text-xs text-muted">Simulated data</span>}
          <span className={`rounded-full px-3 py-1 text-xs font-medium ${LEVEL[s.level].cls}`}>{LEVEL[s.level].label}</span>
        </div>
      </div>

      <div className="mt-5 space-y-2">
        {s.symptoms.slice(0, 5).map((x) => (
          <div key={x.key} className="grid grid-cols-[minmax(0,10rem)_1fr_auto] items-center gap-3 text-sm">
            <span className={`truncate ${x.red_flag ? "text-danger" : ""}`}>{x.en}</span>
            <div className="h-2 overflow-hidden rounded-full bg-sand">
              <motion.div initial={{ width: 0 }} animate={{ width: `${(x.n / max) * 100}%` }} className={`h-full rounded-full ${x.flagged ? "bg-danger" : "bg-clay"}`} />
            </div>
            <span className="font-mono text-xs text-muted">
              {x.n}{x.prr !== null && <> · PRR <b className={x.flagged ? "text-danger" : ""}>{x.prr}</b></>}
            </span>
          </div>
        ))}
      </div>

      <div className="mt-5 grid gap-2 text-xs text-muted sm:grid-cols-3">
        <span className="flex items-center gap-1.5"><Activity className="size-3.5" /> {s.reports} reporters{s.red_flag_reports ? `, ${s.red_flag_reports} serious` : ""}</span>
        <span className="flex items-center gap-1.5"><MapPin className="size-3.5" /> {s.cities.join(", ") || "City not given"}</span>
        <span>First report {formatIST(s.first_report)}</span>
      </div>

      <div className={`mt-4 rounded-2xl px-4 py-3 text-sm ${s.regulator ? "bg-sand" : "bg-danger/10"}`}>
        {s.regulator ? (
          <>Regulator listed this batch as {s.regulator.category === "spurious" ? "spurious" : "NSQ"} in {formatMonth(s.regulator.alert_month)}.
            {s.ahead_of_regulator && <b> Patients reported it first.</b>}</>
        ) : (
          <><b>Not on any regulator list yet.</b> This pattern is a reason for a lab to test the batch, not proof it is bad.</>
        )}
      </div>
      {s.method === "cluster" && <p className="mt-2 text-xs text-muted">Too few other reports to compare against yet, so this uses a simple cluster rule instead of PRR.</p>}
    </motion.div>
  );
}

export default function SignalsPage() {
  const [d, setD] = useState<Signals | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => getSignals().then(setD).catch((e) => setError(e.message)), []);
  useEffect(() => {
    load();
    const t = setInterval(load, 10000);
    return () => clearInterval(t);
  }, [load]);

  return (
    <main className="blush mx-auto max-w-6xl px-4 pt-12 sm:px-6 sm:pt-16">
      <div className="grid items-end gap-6 md:grid-cols-2">
        <div>
          <Eyebrow>Early Signal</Eyebrow>
          <Heading as="h1" lead="Catch a bad batch" tail="before the list does." className="mt-4 text-4xl sm:text-6xl" />
        </div>
        <p className="max-w-sm text-muted md:ml-auto">
          Regulator lists arrive months after a batch is sold. Patients notice sooner. We pool anonymous symptom reports by batch and run the same disproportionality test drug-safety agencies use.
        </p>
      </div>

      {error && <p className="mt-6 text-danger">{error}</p>}

      <div className="mt-10 grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[
          { l: "Reports pooled", v: d?.reports },
          { l: "Batches reported", v: d?.batches },
          { l: "Cities", v: d?.cities },
          { l: "Batches flagged", v: d?.signals.filter((s) => s.level !== "watch").length, hot: true },
        ].map((k) => (
          <div key={k.l} className={`card rounded-3xl p-5 ${k.hot ? "bg-brown text-paper" : ""}`}>
            <p className={`text-xs ${k.hot ? "text-paper/70" : "text-muted"}`}>{k.l}</p>
            <p className="mt-2 text-4xl font-medium tracking-tight">{k.v ?? "–"}</p>
          </div>
        ))}
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="font-medium">Batches with {d?.min_reports ?? 3}+ reporters</p>
            <div className="flex gap-2">
              <button onClick={load} className="grid size-9 place-items-center rounded-full border border-line hover:border-brown" aria-label="Refresh"><RefreshCw className="size-4" /></button>
              <a href={signalsCsvUrl()} className="inline-flex items-center gap-1.5 rounded-full border border-line px-4 py-2 text-xs font-medium hover:border-brown"><Download className="size-3.5" /> PvPI draft CSV</a>
            </div>
          </div>
          {d && d.signals.length === 0 && (
            <div className="card rounded-3xl p-8 text-sm text-muted">
              No batch has {d.min_reports} or more independent reporters yet. Each phone counts once per batch, so one person cannot create a signal.
            </div>
          )}
          {d?.signals.map((s) => <SignalCard key={s.batch_norm} s={s} />)}
        </div>

        <div className="space-y-4">
          <ReportForm onSent={load} />
          <div className="card rounded-3xl p-6 text-sm">
            <p className="flex items-center gap-2 font-medium"><FlaskConical className="size-4 text-brown" /> How a signal is raised</p>
            <ul className="mt-3 space-y-2 text-muted">
              <li><b className="text-espresso">PRR</b>: how much more often a symptom shows up for this batch than for all other batches.</li>
              <li><b className="text-espresso">Signal</b> when at least 3 reporters share a symptom, PRR ≥ 2 and χ² ≥ 4 (the Evans criteria used by drug-safety agencies).</li>
              <li><b className="text-espresso">Urgent</b> when 2 or more people report chest pain, fainting, breathlessness, swelling, confusion or bleeding.</li>
              <li>Many people saying the medicine is <b className="text-espresso">not working</b> is the typical pattern of a substandard batch.</li>
            </ul>
          </div>
          <div className="flex gap-3 rounded-3xl bg-danger/10 p-5 text-sm">
            <Siren className="size-5 shrink-0 text-danger" />
            <p>KinCare never tells anyone to stop or change a medicine. Show your pharmacist or doctor.</p>
          </div>
        </div>
      </div>
    </main>
  );
}
