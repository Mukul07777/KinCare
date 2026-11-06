"use client";

import { RoleGate } from "@/components/RoleGate";
import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, ArrowRight, BellRing, Check, FileText, IndianRupee, Loader2, MessageCircle, PackageOpen, Pill, Play, RotateCcw, ShieldAlert, ShoppingBag, Smartphone, Timer } from "lucide-react";
import Link from "next/link";
import { Eyebrow, Heading } from "@/components/Heading";
import {
  demoReset, getAlerts, getCareSavings, getInteractions, getNotifications, getPlans, getRefills, getStats, recordPurchase, savePlan,
  type Alert, type Interaction, type PurchaseResult, type Stats,
} from "@/lib/api";
import { enableNotifications } from "@/lib/push";
import { WhatsAppJoin } from "@/components/WhatsAppJoin";

type Step = { id: string; icon: typeof Pill; title: string; body?: React.ReactNode; tone?: "ok" | "bad"; at?: number };
type Msg = { id: number; message: string; status: string };

const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

/** One-click patient journey: prescription → interaction check → purchase → "take it now" → recall caught. All real API calls. */
function Demo() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [phone, setPhone] = useState("");
  const [steps, setSteps] = useState<Step[]>([]);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [alertDevice, setAlertDevice] = useState(false);
  const [resetMsg, setResetMsg] = useState<string | null>(null);
  const t0 = useRef(0);

  useEffect(() => {
    getStats().then(setStats).catch(() => {});
    try { setPhone(localStorage.getItem("kincare_phone") || ""); } catch {}
  }, []);
  useEffect(() => {
    if (!running) return;
    const t = setInterval(() => setElapsed((Date.now() - t0.current) / 1000), 100);
    return () => clearInterval(t);
  }, [running]);

  const push = (s: Step) => setSteps((x) => [...x, { ...s, at: (Date.now() - t0.current) / 1000 }]);
  const refreshMsgs = async (after: number) => setMsgs((await getNotifications(10)).filter((m) => m.id > after).reverse());

  const run = async () => {
    setSteps([]); setMsgs([]); setError(null); setRunning(true);
    t0.current = Date.now();
    try {
      try { if (phone) localStorage.setItem("kincare_phone", phone); } catch {}
      // Optional: the recall also arrives as a real notification on this phone / laptop.
      const pushMode = alertDevice ? await enableNotifications() : null;
      const before = (await getNotifications(1))[0]?.id ?? 0;
      // A recent real NSQ tablet whose brand reads like a brand ("Paracip 500"), not a code like "D5".
      const pool = (await getAlerts({ category: "nsq", q: "tablet", limit: 60 })).items;
      const flagged: Alert | undefined = pool.find((a) => /^[A-Za-z][A-Za-z-]{3,}(\s?[\d.]+)?$/.test(a.brand ?? "") && a.batch_no.length >= 4) ?? pool[0];
      const recalled = flagged ? (flagged.brand || flagged.product_name) : null;

      // 1. Doctor's prescription
      const meds = [
        { name: "Warf 5mg", strength: "5 mg", food: "after food", morning: 0, noon: 0, night: 1, days: 30, as_needed: false },
        { name: "Ecosprin 75", strength: "75 mg", food: "after food", morning: 0, noon: 1, night: 0, days: 30, as_needed: false },
        { name: "Crocin 500", strength: "500 mg", food: "after food", morning: 1, noon: 1, night: 1, days: 5, as_needed: false },
        ...(recalled ? [{ name: recalled, strength: "", food: "", morning: 1, noon: 0, night: 0, days: 10, as_needed: false }] : []),
      ];
      await savePlan({ member: "Dadi", doctor: "Dr. Mehta (demo)", diagnosis: "Fever, on blood thinner", advice: ["Drink plenty of fluids", "Follow up in 5 days"], medicines: meds });
      push({ id: "rx", icon: FileText, title: "Doctor’s prescription saved", body: <p>{meds.length} medicines for Dadi, with a dose schedule and the doctor’s advice. KinCare never adds medicines; only the doctor does.</p> });
      await wait(900);

      // 2. Interactions from openFDA
      const ix = await getInteractions(meds.map((m) => m.name));
      push({
        id: "ix", icon: AlertTriangle, tone: ix.interactions.length ? "bad" : "ok",
        title: ix.interactions.length ? `${ix.interactions.length} risky combination${ix.interactions.length > 1 ? "s" : ""} found on official labels` : "No risky combinations on official labels",
        body: ix.interactions.slice(0, 2).map((i: Interaction) => <p key={i.a + i.b} className="mt-1"><b>{i.a} + {i.b}</b>: “{i.evidence.slice(0, 140)}…”</p>),
      });
      await wait(900);

      const plan = (await getPlans()).find((p) => p.member === "Dadi" && p.doctor === "Dr. Mehta (demo)");
      const med = (n: string) => plan?.medicines.find((m) => m.name === n);

      // 3. Clean purchase → "take it now"
      const crocin = med("Crocin 500");
      if (crocin) {
        const r: PurchaseResult = await recordPurchase({ med_id: crocin.id, batch: `DEMO${Date.now() % 100000}`, pharmacy: "Apollo Pharmacy, Saket", phone: phone || undefined, language: "hi", qty: 15 });
        push({ id: "buy", icon: ShoppingBag, tone: "ok", title: "Crocin bought: batch checked against every alert", body: <p>No alert for this batch. {r.due_now ? "Dose is due, so WhatsApp says: take it now." : `WhatsApp says: next dose at ${r.next_time}.`}</p> });
        await refreshMsgs(before);
        const stock = (await getRefills()).find((x) => x.med_id === crocin.id);
        if (stock) {
          const remindOn = new Date(Date.now() + Math.max(stock.days_left - 3, 0) * 86400000).toLocaleDateString("en-IN", { day: "numeric", month: "short" });
          push({
            id: "stock", icon: PackageOpen, tone: "ok", title: `${stock.left} tablets counted at home`,
            body: <p>{stock.per_day} a day, so they last {Math.floor(stock.days_left)} days. {stock.course_days_left != null && stock.left >= stock.course_days_left * stock.per_day
              ? "Enough for the whole course, so no refill nag."
              : <>Refill reminder goes out on <b>{remindOn}</b>, with the cheapest clean-record brand.</>}</p>,
          });
        }
      }
      await wait(900);

      // 4. A batch from a real CDSCO list → caught at the counter
      const bad = recalled ? med(recalled) : undefined;
      if (bad && flagged) {
        const r = await recordPurchase({ med_id: bad.id, batch: flagged.batch_no, maker: flagged.manufacturer, pharmacy: "Local chemist", phone: phone || undefined, language: "hi" });
        push({
          id: "recall", icon: ShieldAlert, tone: r.verdict === "alert_found" ? "bad" : "ok",
          title: r.verdict === "alert_found" ? "Recalled batch caught before the first dose" : "Batch checked",
          body: <>
            <p><b>{flagged.product_name}</b>, batch <b>{flagged.batch_no}</b> by {flagged.manufacturer} is on the CDSCO {flagged.category === "spurious" ? "spurious" : "not-of-standard-quality"} list ({flagged.reason}). A real record, not demo data.</p>
            <Link href={`/blast?batch=${flagged.batch_no.replace(/[^A-Za-z0-9]/g, "").toUpperCase()}`} className="mt-2 inline-flex items-center gap-1 font-medium text-danger hover:underline">
              Who else holds this batch, and when is their next dose? <ArrowRight className="size-3.5" />
            </Link>
            {pushMode === "push" && <p className="mt-1 flex items-center gap-1.5 font-medium text-danger"><Smartphone className="size-4" /> Also sent as a notification to this device.</p>}
          </>,
        });
        await refreshMsgs(before);
      }
      await wait(900);

      // 5. Same salts for less, never from a maker with alerts
      const sv = await getCareSavings("Dadi").catch(() => null);
      const best = sv?.items.filter((i) => i.matched && i.cheapest && (i.monthly_now ?? 0) > (i.monthly_cheapest ?? 0))
        .sort((a, b) => ((b.monthly_now ?? 0) - (b.monthly_cheapest ?? 0)) - ((a.monthly_now ?? 0) - (a.monthly_cheapest ?? 0)))[0];
      if (sv && sv.monthly_now > 0) {
        push({
          id: "save", icon: IndianRupee, tone: "ok",
          title: sv.yearly_saving > 0 ? `Same medicines, ₹${sv.yearly_saving.toLocaleString("en-IN")} a year less` : "Already on low-priced brands",
          body: <p>Dadi&apos;s prescriptions cost about ₹{sv.monthly_now.toLocaleString("en-IN")} a month.{best && <> Biggest saving: <b>{best.matched!.name}</b> → <b>{best.cheapest!.name}</b>, same salt and strength, maker has no CDSCO alerts.</>} Shown to the doctor, never switched by KinCare.</p>,
        });
      }
      push({ id: "remind", icon: BellRing, tone: "ok", title: "Reminders scheduled", body: <p>A WhatsApp reminder goes out at every dose time. Dadi replies <b>1</b> and the dose is ticked, no app needed.</p> });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setElapsed((Date.now() - t0.current) / 1000);
      setRunning(false);
    }
  };

  return (
    <main className="blush mx-auto max-w-6xl px-4 pt-12 sm:px-6 sm:pt-16">
      <Eyebrow>Live demo</Eyebrow>
      <Heading as="h1" lead="One patient." tail="Under a minute." className="mt-4 text-4xl sm:text-6xl" />
      <p className="mt-4 max-w-2xl text-muted">
        From prescription to purchase to the first dose. Each step below is a real API call: real CDSCO alert data, real openFDA labels and real WhatsApp delivery.
      </p>

      {stats && (
        <div className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[[stats.total.toLocaleString("en-IN"), "regulator alerts indexed"], [stats.spurious.toLocaleString("en-IN"), "spurious batches"], [stats.manufacturers.toLocaleString("en-IN"), "manufacturers tracked"], [stats.documents.toLocaleString("en-IN"), "official documents read"]].map(([n, l]) => (
            <div key={l} className="card rounded-3xl p-5"><p className="text-3xl font-medium tracking-tight">{n}</p><p className="mt-1 text-xs text-muted">{l}</p></div>
          ))}
        </div>
      )}

      <div className="mt-8 flex flex-wrap items-end gap-3">
        <label className="block">
          <span className="text-xs font-medium text-muted">Judge’s WhatsApp number (optional)</span>
          <input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="98xxxxxxxx" className="mt-1 block w-60 rounded-full border border-line bg-paper px-4 py-2.5 text-sm outline-none focus:border-brown/40" />
        </label>
        <WhatsAppJoin compact />
        <label className="flex items-center gap-2 rounded-full border border-line bg-paper px-4 py-2.5 text-sm">
          <input type="checkbox" checked={alertDevice} onChange={(e) => setAlertDevice(e.target.checked)} className="accent-[var(--teal)]" />
          <Smartphone className="size-4 text-teal" /> Also alert this phone
        </label>
        <button onClick={run} disabled={running} className="inline-flex items-center gap-2 rounded-full bg-brown px-6 py-3 font-medium text-paper hover:bg-brown-2 disabled:opacity-70">
          {running ? <Loader2 className="size-4 animate-spin" /> : <Play className="size-4" />} {steps.length && !running ? "Run again" : "Start the demo"}
        </button>
        {(running || steps.length > 0) && (
          <span className="inline-flex items-center gap-2 rounded-full bg-espresso px-4 py-3 font-mono text-sm text-paper"><Timer className="size-4" /> {elapsed.toFixed(1)}s</span>
        )}
        <button onClick={async () => { setResetMsg("…"); try { const r = await demoReset(); setResetMsg(`Cleared ${r.copied_code_scans} radar scans, ${r.symptom_reports} reports and all simulated holders`); setSteps([]); setMsgs([]); } catch (e) { setResetMsg((e as Error).message); } }}
          disabled={running} className="inline-flex items-center gap-1.5 rounded-full border border-line bg-paper px-4 py-3 text-sm font-medium text-muted hover:text-espresso">
          <RotateCcw className="size-4" /> Reset demo data
        </button>
        {resetMsg && <span className="text-xs text-muted">{resetMsg}</span>}
      </div>
      {error && <p className="mt-3 text-sm text-danger">Couldn’t reach the KinCare server. Wait a moment and try again.</p>}

      <div className="mt-8 grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <ol className="space-y-3">
          <AnimatePresence>
            {steps.map((s) => (
              <motion.li key={s.id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
                className={`card flex gap-4 rounded-3xl p-5 ${s.tone === "bad" ? "border-danger/30 bg-danger/5" : ""}`}>
                <span className={`grid size-10 shrink-0 place-items-center rounded-2xl ${s.tone === "bad" ? "bg-danger text-paper" : "bg-brown text-paper"}`}><s.icon className="size-5" /></span>
                <div className="min-w-0 flex-1 text-sm text-muted">
                  <p className="flex flex-wrap items-center justify-between gap-2 text-base font-medium text-espresso">{s.title} <span className="font-mono text-xs text-muted">+{s.at?.toFixed(1)}s</span></p>
                  <div className="mt-1">{s.body}</div>
                </div>
              </motion.li>
            ))}
          </AnimatePresence>
          {!steps.length && !running && <li className="rounded-3xl border border-dashed border-line p-8 text-center text-sm text-muted">Press <b>Start the demo</b>. Steps appear here as they happen.</li>}
          {!running && steps.length > 0 && (
            <li className="flex flex-wrap gap-3 pt-2">
              <Link href="/care" className="inline-flex items-center gap-1.5 rounded-full bg-sand px-4 py-2 text-sm font-medium text-brown">See Dadi’s care plan <ArrowRight className="size-4" /></Link>
              <Link href="/save?q=Ecosprin 75" className="inline-flex items-center gap-1.5 rounded-full bg-sand px-4 py-2 text-sm font-medium text-brown">Compare Ecosprin brands <ArrowRight className="size-4" /></Link>
              <Link href="/live" className="inline-flex items-center gap-1.5 rounded-full bg-espresso px-4 py-2 text-sm font-medium text-paper">Next: the 60-second recall <ArrowRight className="size-4" /></Link>
            </li>
          )}
        </ol>

        {/* Phone mockup with the messages the patient actually receives */}
        <div className="mx-auto w-full max-w-[320px]">
          <div className="rounded-[2.5rem] border-[10px] border-espresso bg-[#e9dfd2] p-3 shadow-xl">
            <div className="flex items-center gap-2 rounded-2xl bg-[#075e54] px-3 py-2 text-paper">
              <MessageCircle className="size-4" /><p className="text-sm font-medium">KinCare</p>
              <span className="ml-auto text-[10px] opacity-70">WhatsApp</span>
            </div>
            <div className="mt-3 flex min-h-[380px] flex-col gap-2">
              <AnimatePresence>
                {msgs.map((m) => (
                  <motion.div key={m.id} initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
                    className="max-w-[92%] whitespace-pre-line rounded-2xl rounded-tl-sm bg-paper px-3 py-2 text-[12px] leading-snug text-espresso shadow-sm">
                    {m.message}
                    <span className="mt-1 flex items-center justify-end gap-1 text-[10px] text-muted">{m.status === "sent" ? <><Check className="size-3" /> delivered</> : "outbox"}</span>
                  </motion.div>
                ))}
              </AnimatePresence>
              {!msgs.length && <p className="m-auto text-center text-xs text-muted">Messages to the patient appear here.</p>}
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}

export default function DemoPage() {
  return <RoleGate perm="demo.seed" role="admin" what="Stage demo"><Demo /></RoleGate>;
}
