"use client";

import { useEffect, useState } from "react";
import { Check, Download, HeartPulse, RefreshCw } from "lucide-react";
import { formatIST, getCheckins, markReviewed, pvpiCsvUrl, type CheckinItem } from "@/lib/api";

const BADGE = {
  urgent: "bg-danger text-paper",
  review: "bg-sand text-brown",
  ok: "bg-safe/15 text-safe",
} as const;

const LABEL: Record<string, string> = {
  dizziness: "Dizziness", headache: "Headache", nausea: "Nausea", no_effect: "Not working", fever: "Fever",
  rash_swelling: "Rash / swelling", breathlessness: "Breathlessness", chest_pain: "Chest pain", fainting: "Fainting",
  confusion: "Confusion", bleeding: "Bleeding",
};

export function CheckinQueue() {
  const [data, setData] = useState<{ items: CheckinItem[]; responded: number; urgent: number } | null>(null);

  const load = () => getCheckins().then(setData).catch(() => {});
  useEffect(() => {
    load();
    const t = setInterval(load, 10000); // new answers appear without a refresh
    return () => clearInterval(t);
  }, []);

  if (!data || data.items.length === 0) return null;

  return (
    <section className="card mt-8 rounded-[2rem] p-5 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="flex items-center gap-2 font-medium"><HeartPulse className="size-4 text-danger" /> Patient check-ins after recall</p>
          <p className="text-xs text-muted">{data.responded} of {data.items.length} patients answered · {data.urgent} urgent. Call urgent patients first.</p>
        </div>
        <div className="flex gap-2">
          <button onClick={load} className="grid size-9 place-items-center rounded-full border border-line hover:border-brown" aria-label="Refresh"><RefreshCw className="size-4" /></button>
          <a href={pvpiCsvUrl()} className="inline-flex items-center gap-1.5 rounded-full border border-line px-3.5 py-2 text-xs font-medium hover:border-brown hover:text-brown">
            <Download className="size-3.5" /> Export for PvPI
          </a>
        </div>
      </div>
      <div className="mt-4 divide-y divide-line">
        {data.items.map((c) => (
          <div key={c.id} className={`grid gap-2 py-3 sm:grid-cols-[auto_1.2fr_1.6fr_auto] sm:items-center ${c.reviewed ? "opacity-50" : ""}`}>
            <span className={`w-fit rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase ${c.triage ? BADGE[c.triage] : "bg-cream text-muted"}`}>
              {c.triage ?? "awaiting"}
            </span>
            <div className="min-w-0">
              <p className="text-sm font-medium">{c.name ?? "Patient"} <span className="font-normal text-muted">{c.phone}</span></p>
              <p className="truncate font-mono text-xs text-muted">{c.brand || c.product_name} · {c.batch}</p>
            </div>
            <div className="text-xs text-muted">
              {c.responded_at ? (
                <>
                  <p className="text-espresso">
                    {c.feeling === "ok" ? "Feels fine" : "Feels unwell"}
                    {c.symptoms && ": " + c.symptoms.split(",").map((s) => LABEL[s] ?? s).join(", ")}
                    {c.bp_sys && ` · BP ${c.bp_sys}/${c.bp_dia ?? "?"}`}
                  </p>
                  {c.note && <p className="truncate">“{c.note}”</p>}
                  <p>{formatIST(c.responded_at)}</p>
                </>
              ) : (
                <p>Link sent {formatIST(c.created_at)}</p>
              )}
            </div>
            {c.responded_at && !c.reviewed && (
              <button onClick={() => markReviewed(c.id).then(load)} className="inline-flex w-fit items-center gap-1 rounded-full border border-line px-3 py-1.5 text-xs hover:border-safe hover:text-safe">
                <Check className="size-3.5" /> Called
              </button>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
