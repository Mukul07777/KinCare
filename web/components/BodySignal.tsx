"use client";

import { useEffect, useState } from "react";
import { Activity, HeartPulse } from "lucide-react";
import { getBatchEffects, type BatchEffect } from "@/lib/api";

/** "Since starting this batch, your pulse is up 15 bpm": the patient's own vitals before vs after a bought batch. */
export function BodySignal({ version }: { version: number }) {
  const [items, setItems] = useState<BatchEffect[]>([]);
  useEffect(() => { getBatchEffects().then(setItems).catch(() => {}); }, [version]);
  if (!items.length) return null;

  const flagged = items.filter((i) => i.enough && i.flagged?.length);
  const steady = items.filter((i) => i.enough && !i.flagged?.length);
  const waiting = items.filter((i) => !i.enough);

  return (
    <div className={`rounded-3xl p-5 text-sm ${flagged.length ? "bg-warn-soft" : "card"}`}>
      <p className="flex items-center gap-2 font-medium">
        {flagged.length ? <HeartPulse className="size-4 text-warn" /> : <Activity className="size-4 text-teal" />} Since starting each batch
      </p>
      <div className="mt-3 space-y-3">
        {flagged.map((i) => (
          <div key={i.med_id}>
            <p className="font-medium">{i.name} <span className="font-normal text-muted">· {i.member} · batch {i.batch}</span></p>
            {i.flagged!.map((c) => (
              <p key={c.key} className="text-warn">
                {c.label}: {c.before} → <b>{c.after}</b> {c.unit} ({c.delta > 0 ? "+" : ""}{c.delta})
              </p>
            ))}
          </div>
        ))}
        {steady.map((i) => <p key={i.med_id} className="text-muted"><b className="text-espresso">{i.name}</b>: no unusual change in vitals since starting.</p>)}
        {waiting.length > 0 && (
          <p className="text-xs text-muted">Log a few readings in Vitals and KinCare compares them with before you started {waiting.map((w) => w.name).join(", ")}.</p>
        )}
      </div>
      {flagged.length > 0 && <p className="mt-3 text-xs text-warn">Show this to your doctor. A change is a reason to check, not proof the medicine caused it. Don&apos;t stop a medicine on your own.</p>}
    </div>
  );
}
