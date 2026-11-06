"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Sparkles } from "lucide-react";
import { getEntitlement, type Entitlement } from "@/lib/api";

const NAMES: Record<Entitlement["tier"], string> = { free: "Free", basic: "Basic", family: "Family", pharmacy: "Pharmacy", pharmacy_pro: "Pharmacy Pro" };

/** Which plan this device is on: trial days left, or what upgrading adds. Never shown as a blocker for safety features. */
export function PlanBadge() {
  const [e, setE] = useState<Entitlement | null>(null);
  useEffect(() => { getEntitlement().then(setE).catch(() => {}); }, []);
  if (!e || e.plan === "all_access") return null;

  const text = e.plan === "trial"
    ? `Family trial · ${e.trial_days_left} day${e.trial_days_left === 1 ? "" : "s"} left · all features on`
    : e.tier === "free"
      ? "Free plan · batch checks and recall alerts are always free"
      : `${NAMES[e.tier]} plan`;
  const cta = e.tier === "free" ? "Get WhatsApp reminders from ₹29" : e.plan === "trial" ? "See plans" : null;

  return (
    <div className="inline-flex flex-wrap items-center gap-2 rounded-full border border-teal/20 bg-mint px-4 py-1.5 text-xs text-teal">
      <Sparkles className="size-3.5" /> {text}
      {cta && <Link href="/account" className="font-semibold underline-offset-2 hover:underline">{cta}</Link>}
    </div>
  );
}
