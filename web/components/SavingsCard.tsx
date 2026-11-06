"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { IndianRupee } from "lucide-react";
import { getCareSavings, type Savings } from "@/lib/api";

/** What the family spends a month on prescribed medicines vs the same salts from makers with a clean record. */
export function SavingsCard() {
  const [s, setS] = useState<Savings | null>(null);
  useEffect(() => { getCareSavings().then(setS).catch(() => {}); }, []);

  const matched = s?.items.filter((i) => i.matched) ?? [];
  if (!s || !matched.length) return null;
  const save = s.monthly_now - s.monthly_cheapest;

  return (
    <div className="card rounded-3xl p-5 text-sm">
      <p className="flex items-center gap-2 font-medium"><IndianRupee className="size-4 text-brown" /> Medicine spend</p>
      <p className="mt-2 text-muted">These prescriptions cost about <b className="text-espresso">₹{s.monthly_now.toLocaleString("en-IN")}</b> a month.</p>
      {save > 0 ? (
        <>
          <p className="mt-1 text-muted">
            The same salts from makers with no CDSCO alerts: <b className="text-safe">₹{s.monthly_cheapest.toLocaleString("en-IN")}</b>.
          </p>
          <p className="mt-2 font-mono text-2xl font-semibold text-safe">Save ₹{s.yearly_saving.toLocaleString("en-IN")}/year</p>
        </>
      ) : <p className="mt-1 text-safe">Already close to the lowest price for these salts.</p>}
      <div className="mt-3 space-y-1">
        {matched.map((i) => (
          <Link key={i.name} href={`/save?q=${encodeURIComponent(i.matched!.name)}`} className="flex justify-between gap-2 text-xs hover:text-brown">
            <span className="truncate">{i.matched!.name}{i.estimated ? " (typical price)" : ""}</span>
            <span className="shrink-0 font-mono">₹{i.monthly_now} → ₹{i.monthly_cheapest}</span>
          </Link>
        ))}
      </div>
      <p className="mt-2 text-[11px] text-muted">Ask your doctor or pharmacist before switching brands.</p>
    </div>
  );
}
