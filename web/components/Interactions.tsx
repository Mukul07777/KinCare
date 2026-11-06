"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, ShieldCheck, Loader2 } from "lucide-react";
import { getInteractions, type Interaction } from "@/lib/api";

/** Pairs of prescribed medicines that mention each other on their official FDA label. */
export function Interactions({ names }: { names?: string[] }) {
  const [data, setData] = useState<{ interactions: Interaction[]; no_label: string[] } | null>(null);
  const key = names?.join(",");

  useEffect(() => {
    setData(null);
    getInteractions(key ? key.split(",") : undefined).then(setData).catch(() => setData({ interactions: [], no_label: [] }));
  }, [key]);

  if (!data) return <div className="card rounded-3xl p-5 text-sm text-muted"><Loader2 className="inline size-4 animate-spin" /> Checking medicine combinations…</div>;

  return (
    <div className="card rounded-3xl p-5">
      <p className="flex items-center gap-2 font-medium">
        {data.interactions.length ? <AlertTriangle className="size-4 text-danger" /> : <ShieldCheck className="size-4 text-safe" />}
        Medicine combinations
      </p>
      {data.interactions.length ? (
        <div className="mt-3 space-y-3">
          {data.interactions.map((i) => (
            <div key={i.a + i.b} className="rounded-2xl border border-danger/20 bg-danger/5 p-3 text-sm">
              <p className="font-medium">{i.a} <span className="text-muted">+</span> {i.b}</p>
              <p className="mt-1 text-xs text-muted">“{i.evidence}”</p>
              <p className="mt-1 text-[11px] uppercase tracking-wide text-danger">From the label’s {i.section}</p>
            </div>
          ))}
          <p className="text-xs font-medium text-espresso">Don’t stop any medicine. Show this to your doctor or pharmacist.</p>
        </div>
      ) : (
        <p className="mt-1 text-sm text-muted">No combination of your prescribed medicines is flagged on their official labels.</p>
      )}
      {data.no_label.length > 0 && <p className="mt-2 text-xs text-muted">No label found for: {data.no_label.join(", ")}</p>}
      <p className="mt-3 text-[11px] text-muted">Source: openFDA drug labels (api.fda.gov), open data.</p>
    </div>
  );
}
