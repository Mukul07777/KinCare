"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import { AlertTriangle, ArrowRight, BadgeCheck, Ban, BookOpen, Baby, Clock, Info, Loader2, Pill, ScanLine, ShieldAlert, Stethoscope } from "lucide-react";
import { Eyebrow, Heading } from "@/components/Heading";
import { JanAushadhi } from "@/components/JanAushadhi";
import { MakerBadge } from "@/components/MakerBadge";
import { formatMonth, getMedicineInfo, perUnit, type LabelText, type MedInfo } from "@/lib/api";

const SECTIONS: { key: keyof LabelText; title: string; icon: typeof Info; tone?: "warn" | "danger" }[] = [
  { key: "uses", title: "What it is used for", icon: Stethoscope },
  { key: "how_to_take", title: "How it is taken", icon: Clock },
  { key: "side_effects", title: "Side effects", icon: Info },
  { key: "warnings", title: "Warnings", icon: AlertTriangle, tone: "warn" },
  { key: "do_not_take", title: "Do not take if", icon: Ban, tone: "danger" },
  { key: "pregnancy", title: "Pregnancy & breastfeeding", icon: Baby },
];

export default function MedicinePage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<MedInfo | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getMedicineInfo(Number(id)).then(setData).catch((e) => setError((e as Error).message));
  }, [id]);

  if (error) return <main className="mx-auto max-w-6xl px-4 pt-16 sm:px-6"><p className="text-danger">{error}</p></main>;
  if (!data) return <main className="mx-auto max-w-6xl px-4 pt-16 sm:px-6"><p className="text-muted"><Loader2 className="inline size-4 animate-spin" /> Reading the official label…</p></main>;

  const m = data.medicine;
  const best = data.price.cheapest_clean;
  const cheaper = best && m.unit_price != null && best.unit_price != null && best.unit_price < m.unit_price;

  return (
    <main className="blush mx-auto max-w-6xl px-4 pb-20 pt-12 sm:px-6 sm:pt-16">
      <Eyebrow>Medicine</Eyebrow>
      <Heading as="h1" lead={m.name} tail="" className="mt-4 text-4xl sm:text-5xl" />
      <p className="mt-3 text-muted">{m.salts} · {m.pack}</p>
      <p className="text-sm text-muted">{m.maker} <MakerBadge r={m.maker_record} /></p>

      <div className="mt-8 grid gap-5 lg:grid-cols-[1.4fr_1fr]">
        <div className="space-y-4">
          {data.salts.map((s) => (
            <motion.div key={s.name} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="card rounded-[2rem] p-6">
              <p className="flex items-center gap-2 text-lg font-medium capitalize tracking-tight"><Pill className="size-5 text-teal" /> {s.name}</p>
              {s.label === null && <p className="mt-2 text-sm text-muted">Couldn&apos;t reach the FDA label service. Try again in a moment.</p>}
              {s.label && !Object.keys(s.label).some((k) => k !== "label_name") && (
                <p className="mt-2 text-sm text-muted">No US FDA label found for this salt. Ask your pharmacist for the leaflet in the box.</p>
              )}
              <div className="mt-3 space-y-4">
                {s.label && SECTIONS.filter((x) => s.label?.[x.key]).map(({ key, title, icon: Icon, tone }) => (
                  <details key={key} open={key === "uses" || key === "do_not_take"} className={`group rounded-2xl border p-4 ${tone === "danger" ? "border-danger/20 bg-danger/5" : tone === "warn" ? "border-warn/20 bg-warn-soft/50" : "border-line bg-cream/40"}`}>
                    <summary className="flex cursor-pointer list-none items-center gap-2 font-medium">
                      <Icon className={`size-4 ${tone === "danger" ? "text-danger" : tone === "warn" ? "text-warn" : "text-brown"}`} /> {title}
                      <span className="ml-auto text-xs text-muted group-open:hidden">Show</span>
                    </summary>
                    <p className="mt-2 text-sm leading-relaxed text-espresso/85">{s.label?.[key]}</p>
                  </details>
                ))}
              </div>
              {s.label && Object.keys(s.label).length > 1 && (
                <p className="mt-3 text-[11px] text-muted">From the US FDA label for {s.label.label_name?.toLowerCase() ?? s.label_name}. Indian brands share the salt, not always the label text.</p>
              )}
            </motion.div>
          ))}
          <div className="card flex items-start gap-3 rounded-3xl p-5 text-sm text-muted">
            <BookOpen className="mt-0.5 size-4 shrink-0 text-brown" />
            Information only, not advice. Take it the way your doctor prescribed. Never start, stop or change a dose without them.
          </div>
        </div>

        <div className="space-y-4">
          <div className={`rounded-[2rem] p-6 ${data.alerts.total ? "bg-warn-soft" : "card"}`}>
            <p className="flex items-center gap-2 font-medium">
              {data.alerts.total ? <ShieldAlert className="size-4 text-warn" /> : <BadgeCheck className="size-4 text-safe" />}
              Batch alerts for {data.alerts.salt ?? "this salt"}
            </p>
            <p className="mt-1 text-sm text-muted">
              {data.alerts.total
                ? <>{data.alerts.total} batches of {data.alerts.salt} from different makers failed regulator tests{data.alerts.spurious ? `, ${data.alerts.spurious} found spurious` : ""}. Check yours.</>
                : "No CDSCO or state alerts mention this salt."}
            </p>
            {data.alerts.recent.length > 0 && (
              <div className="mt-3 space-y-2">
                {data.alerts.recent.slice(0, 5).map((a) => (
                  <div key={a.id} className="rounded-xl bg-paper/70 px-3 py-2 text-xs">
                    <p className="font-medium">{a.product_name}</p>
                    <p className="text-muted">Batch <span className="font-mono">{a.batch_no}</span> · {a.manufacturer ?? "maker not listed"} · {formatMonth(a.alert_month)}</p>
                  </div>
                ))}
              </div>
            )}
            <Link href="/scan" className="mt-4 inline-flex items-center gap-2 rounded-full bg-brown px-4 py-2 text-sm font-medium text-paper hover:bg-brown-2">
              <ScanLine className="size-4" /> Scan your strip&apos;s batch
            </Link>
          </div>

          <div className="card rounded-[2rem] p-6">
            <p className="text-xs font-medium uppercase tracking-wider text-muted">Price</p>
            <p className="mt-1 font-mono text-3xl font-semibold">₹{m.price}</p>
            <p className="text-sm text-muted">{perUnit(m)} · #{data.price.rank} cheapest of {data.price.brands} brands with this exact salt and form</p>
            {cheaper ? (
              <div className="mt-4 rounded-2xl bg-safe/10 p-4 text-sm">
                <p className="font-medium text-safe">Cheapest with no CDSCO alerts: {best.name}</p>
                <p className="text-muted">{best.maker} · {perUnit(best)} ({best.saving_pct}% less)</p>
              </div>
            ) : <p className="mt-3 text-sm text-safe">Already among the cheapest brands with a clean record.</p>}
            <Link href={`/save?q=${encodeURIComponent(m.name)}`} className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-teal hover:underline">
              Compare all {data.price.brands} brands <ArrowRight className="size-3.5" />
            </Link>
          </div>

          <JanAushadhi salt={m.salts} />
        </div>
      </div>
    </main>
  );
}
