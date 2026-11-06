"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { PackageOpen } from "lucide-react";
import { getRefills, type Refill } from "@/lib/api";

/** Tablets left of every bought medicine; flags the ones to refill in the next few days. */
export function Refills({ version }: { version: number }) {
  const [items, setItems] = useState<Refill[]>([]);
  useEffect(() => { getRefills().then(setItems).catch(() => {}); }, [version]);

  if (!items.length) return null;
  const low = items.filter((r) => r.low).length;

  return (
    <div className={`rounded-3xl p-5 text-sm ${low ? "bg-warn-soft" : "card"}`}>
      <p className="flex items-center gap-2 font-medium"><PackageOpen className={`size-4 ${low ? "text-warn" : "text-brown"}`} /> Tablets at home</p>
      <p className="mt-1 text-muted">{low ? `${low} running low. Refill before it runs out.` : "Counted from what you bought and the doses you ticked."}</p>
      <div className="mt-3 space-y-2.5">
        {items.map((r) => {
          const days = Math.floor(r.days_left);
          return (
            <div key={r.med_id}>
              <div className="flex items-baseline justify-between gap-2">
                <p className="truncate font-medium">{r.name} <span className="font-normal text-muted">{r.member}</span></p>
                <p className={`shrink-0 font-mono text-xs ${r.low ? "font-semibold text-warn" : "text-muted"}`}>{r.left} left · {days} day{days === 1 ? "" : "s"}</p>
              </div>
              <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-paper">
                <div className={`h-full rounded-full ${r.low ? "bg-warn" : "bg-safe"}`} style={{ width: `${Math.min(100, (r.days_left / 30) * 100)}%` }} />
              </div>
              {r.low && (
                <p className="mt-1 text-xs text-muted">
                  {r.reminded_at ? "Reminder sent. " : ""}
                  <Link href={`/save?q=${encodeURIComponent(r.name)}`} className="font-medium text-teal hover:underline">Same salt for less</Link>
                  {" · "}after buying, tap <b>Bought more</b> below.
                </p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
