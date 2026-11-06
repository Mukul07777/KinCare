"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { ArrowRight, BadgeCheck, IndianRupee, Loader2, Search, Store } from "lucide-react";
import { Eyebrow, Heading } from "@/components/Heading";
import Link from "next/link";
import { JanAushadhi } from "@/components/JanAushadhi";
import { MakerBadge } from "@/components/MakerBadge";
import { getAlternatives, perUnit, searchMedicines, type Alternatives, type Medicine } from "@/lib/api";

// Common long-term medicines people buy every month. These are search words, not data.
const TRY = ["Telma 40", "Glycomet 500", "Amlong 5", "Atorva 10", "Thyronorm 50", "Pan 40", "Ecosprin 75", "Dolo 650"];

export default function SavePage() {
  return <Suspense><Save /></Suspense>;
}

function Save() {
  const params = useSearchParams();
  const [q, setQ] = useState(params.get("q") ?? "");
  const [hits, setHits] = useState<Medicine[]>([]);
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<Alternatives | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [perDay, setPerDay] = useState(1);
  const pickedFromUrl = useRef(false);

  useEffect(() => {
    if (q.trim().length < 2) { setHits([]); return; }
    const t = setTimeout(() => searchMedicines(q).then((h) => {
      setHits(h);
      // ?q= from another page: open the best match straight away.
      if (!pickedFromUrl.current && params.get("q") && h[0]) { pickedFromUrl.current = true; pick(h[0]); }
    }).catch(() => setHits([])), 200);
    return () => clearTimeout(t);
  }, [q]); // eslint-disable-line react-hooks/exhaustive-deps

  const pick = async (m: Medicine) => {
    setOpen(false); setQ(m.name); setBusy(true); setError(null);
    try { setData(await getAlternatives(m.id)); } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };

  const me = data?.medicine;
  const best = data?.cheapest_clean;
  const monthly = (m?: Medicine | null) => (m?.unit_price != null ? m.unit_price * perDay * 30 : null);
  const saving = me && best && monthly(me)! > monthly(best)! ? monthly(me)! - monthly(best)! : 0;

  return (
    <main className="blush mx-auto max-w-6xl px-4 pb-20 pt-12 sm:px-6 sm:pt-16">
      <Eyebrow>Save</Eyebrow>
      <Heading as="h1" lead="Same medicine." tail="Lower price." className="mt-4 text-4xl sm:text-6xl" />
      <p className="mt-4 max-w-2xl text-muted">
        Search any brand. KinCare finds every brand with the <b className="text-espresso">exact same salts, strength and form</b>, compared per tablet,
        and shows each maker&apos;s record in the CDSCO alert database, so cheaper never quietly means riskier.
      </p>

      <div className="relative mt-8 max-w-2xl">
        <div className="flex items-center gap-3 rounded-full border border-line bg-paper px-5 py-3.5 shadow-sm focus-within:border-brown/40">
          <Search className="size-5 text-muted" />
          <input value={q} onChange={(e) => { setQ(e.target.value); setOpen(true); }} onFocus={() => setOpen(true)}
            placeholder="Brand or salt, e.g. Telma 40 or atorvastatin" className="w-full bg-transparent text-lg outline-none placeholder:text-clay" />
          {busy && <Loader2 className="size-5 animate-spin text-muted" />}
        </div>
        {open && hits.length > 0 && (
          <div className="absolute z-20 mt-2 w-full overflow-hidden rounded-3xl border border-line bg-paper shadow-xl">
            {hits.map((h) => (
              <button key={h.id} onClick={() => pick(h)} className="flex w-full items-center justify-between gap-3 px-5 py-3 text-left hover:bg-cream">
                <span>
                  <span className="block font-medium">{h.name}</span>
                  <span className="block text-xs text-muted">{h.salts} · {h.maker}</span>
                </span>
                <span className="shrink-0 text-right text-sm"><span className="font-mono">₹{h.price}</span><span className="block text-[11px] text-muted">{h.pack}</span></span>
              </button>
            ))}
          </div>
        )}
      </div>
      {!data && (
        <div className="mt-4 flex flex-wrap gap-2">
          {TRY.map((t) => <button key={t} onClick={() => { setQ(t); setOpen(true); }} className="rounded-full bg-sand px-3 py-1.5 text-xs font-medium text-brown">{t}</button>)}
        </div>
      )}
      {error && <p className="mt-4 text-sm text-danger">{error}</p>}

      {data && me && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mt-10 grid gap-5 lg:grid-cols-[1fr_1.25fr]">
          <div className="space-y-5">
            <div className="card rounded-[2rem] p-6">
              <p className="text-xs font-medium uppercase tracking-wider text-muted">You buy</p>
              <p className="mt-1 text-2xl font-semibold tracking-tight">{me.name}</p>
              <p className="text-sm text-muted">{me.salts} · {me.pack}</p>
              <p className="text-sm text-muted">{me.maker} <MakerBadge r={me.maker_record} /></p>
              <Link href={`/medicine/${me.id}`} className="mt-2 inline-flex items-center gap-1 text-sm font-medium text-teal hover:underline">
                Uses, side effects, warnings <ArrowRight className="size-3.5" />
              </Link>
              <div className="mt-4 flex items-end gap-4">
                <p className="font-mono text-3xl font-semibold">₹{me.price}</p>
                <p className="pb-1 text-sm text-muted">{perUnit(me)}</p>
              </div>
              <PriceStrip data={data} />
              <p className="mt-2 text-xs text-muted">
                {data.brands} brands sell this exact salt and form. Yours is #{data.rank} cheapest.
              </p>
            </div>

            {best && saving > 0 ? (
              <div className="rounded-[2rem] bg-safe p-6 text-paper">
                <p className="flex items-center gap-2 text-sm font-medium text-paper/85"><BadgeCheck className="size-4" /> Cheapest with no CDSCO alerts on record</p>
                <p className="mt-2 text-2xl font-semibold">{best.name}</p>
                <p className="text-sm text-paper/85">{best.maker} · ₹{best.price} for {best.pack} · {perUnit(best)}</p>
                <div className="mt-4 flex flex-wrap items-center gap-2 text-sm">
                  <span>At</span>
                  {[1, 2, 3].map((n) => (
                    <button key={n} onClick={() => setPerDay(n)} className={`rounded-full px-3 py-1 font-semibold ${perDay === n ? "bg-paper text-safe" : "border border-paper/50"}`}>{n}</button>
                  ))}
                  <span>a day you save</span>
                </div>
                <p className="mt-2 font-mono text-4xl font-semibold">₹{Math.round(saving).toLocaleString("en-IN")}<span className="text-base font-normal">/month</span></p>
                <p className="text-sm text-paper/85">₹{Math.round(saving * 12).toLocaleString("en-IN")} a year · {best.saving_pct}% less per tablet</p>
              </div>
            ) : (
              <div className="card rounded-[2rem] p-6 text-sm"><BadgeCheck className="mb-2 size-5 text-safe" />You already buy one of the cheapest brands with a clean record.</div>
            )}

            <div className="card rounded-3xl p-5 text-sm">
              <p className="flex items-center gap-2 font-medium"><Store className="size-4 text-brown" /> Before you switch</p>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-muted">
                <li>Show this to your doctor or pharmacist. Some patients are kept on one brand for a reason.</li>
                <li>Same salt, strength and form only. Release type (SR, ER, MD) is matched too.</li>
                <li>Still scan the batch on the strip. A clean maker record is not a clean batch.</li>
              </ul>
            </div>
            <JanAushadhi salt={me.salts} />
          </div>

          <div className="card rounded-[2rem] p-6">
            <p className="text-lg font-medium tracking-tight">Same salt, same form · cheapest first</p>
            <div className="mt-4 divide-y divide-line">
              {data.alternatives.map((a) => (
                <div key={a.id} className="flex items-start justify-between gap-4 py-3">
                  <div className="min-w-0 flex-1">
                    <Link href={`/medicine/${a.id}`} className="font-medium hover:text-teal hover:underline">{a.name}</Link>
                    <p className="text-xs text-muted">{a.maker} <MakerBadge r={a.maker_record} /></p>
                  </div>
                  <div className="shrink-0 text-right">
                    <p className="font-mono text-sm font-semibold">{perUnit(a)}</p>
                    <p className="text-[11px] text-muted">₹{a.price} · {a.pack.replace(/^\w+ of /, "")}</p>
                    {a.saving_pct != null && (
                      <p className={`text-xs font-semibold ${a.saving_pct > 0 ? "text-safe" : "text-muted"}`}>{a.saving_pct > 0 ? `${a.saving_pct}% cheaper` : `${-a.saving_pct}% dearer`}</p>
                    )}
                  </div>
                </div>
              ))}
              {data.alternatives.length === 0 && <p className="py-6 text-center text-sm text-muted">No other brand sells this exact salt and form.</p>}
            </div>
          </div>
        </motion.div>
      )}

      <p className="mt-10 text-[11px] text-muted">
        Prices: Indian Medicine Dataset (246,068 brands on sale, MIT licence), MRPs as listed; shop prices can differ.
        Maker records: CDSCO and state NSQ / spurious alerts 2019–2026, exact maker-name match only. KinCare never tells you to change a medicine.
      </p>
    </main>
  );
}

// Where this brand sits between the cheapest and the dearest of the same medicine (log scale: prices span 50x+).
function PriceStrip({ data }: { data: Alternatives }) {
  const { min, median, max } = data.unit_price;
  const me = data.medicine.unit_price;
  if (min == null || max == null || me == null || max <= min) return null;
  const pos = (v: number) => `${(Math.log(v / min) / Math.log(max / min)) * 100}%`;
  return (
    <div className="mt-5">
      <div className="relative h-2 rounded-full bg-gradient-to-r from-safe via-[#c07a2c] to-danger">
        {median != null && <span className="absolute -top-1 h-4 w-0.5 bg-espresso/40" style={{ left: pos(median) }} title="median" />}
        <span className="absolute -top-1.5 size-5 -translate-x-1/2 rounded-full border-4 border-paper bg-espresso shadow" style={{ left: pos(me) }} />
      </div>
      <div className="mt-2 flex justify-between text-[11px] text-muted">
        <span><IndianRupee className="inline size-3" />{min.toFixed(2)} cheapest</span>
        <span>median {median?.toFixed(2)}</span>
        <span>{max.toFixed(2)} dearest</span>
      </div>
    </div>
  );
}
