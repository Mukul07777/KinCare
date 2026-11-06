"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Bell, BellRing, Check, ClipboardList, FileText, HeartPulse, Stethoscope, Loader2, Moon, Pill, Plus, Printer, ScanLine, Sun, SunMedium, Thermometer, Trash2, Watch,
} from "lucide-react";
import { BuyMeds } from "@/components/BuyMeds";
import { DoctorConnect } from "@/components/DoctorConnect";
import { LiveVitals } from "@/components/LiveVitals";
import { Refills } from "@/components/Refills";
import { WhatsAppJoin } from "@/components/WhatsAppJoin";
import { PlanBadge } from "@/components/PlanBadge";
import { BodySignal } from "@/components/BodySignal";
import { SavingsCard } from "@/components/SavingsCard";
import { enableNotifications, notifyNow } from "@/lib/push";
import { Interactions } from "@/components/Interactions";
import { Eyebrow, Heading } from "@/components/Heading";
import {
  addVitals, deletePlan, formatIST, getCareMessages, getDoctorLinks, getPlans, getReport, getToday, getVitals, markDose, savePlan, scanPrescription,
  type Assessment, type Dose, type Plan, type RxMed, type Vital,
} from "@/lib/api";

const MEMBERS = ["Me", "Maa", "Papa", "Dadi", "Dada", "Child"];
const SLOT_ICON = { morning: Sun, noon: SunMedium, night: Moon } as const;
const SLOT_LABEL = { morning: "Morning", noon: "Afternoon", night: "Night" } as const;
type Tab = "today" | "vitals" | "doctor" | "rx" | "report";

export default function CarePage() {
  const [tab, setTab] = useState<Tab>("today");
  const [member, setMember] = useState("Me");
  const [linked, setLinked] = useState<string[]>([]);
  const [unread, setUnread] = useState(0);

  // Which members have a doctor watching, and new doctor messages, for the tab badge.
  useEffect(() => {
    const load = () => {
      getDoctorLinks().then((l) => setLinked(l.map((x) => x.member))).catch(() => {});
      getCareMessages().then((m) => setUnread(m.unread)).catch(() => {});
    };
    load();
    const t = setInterval(load, 10000);
    return () => clearInterval(t);
  }, [tab]);

  return (
    <main className="blush mx-auto max-w-6xl px-4 pt-12 sm:px-6 sm:pt-16 print:pt-0">
      <div className="print:hidden">
        <div className="flex flex-wrap items-center gap-3"><Eyebrow>Care</Eyebrow><PlanBadge /></div>
        <Heading as="h1" lead="Vitals, the doctor’s plan," tail="daily reminders." className="mt-4 text-4xl sm:text-6xl" />
        <p className="mt-4 max-w-2xl text-muted">
          Log readings. If something looks off, KinCare tells you to see a doctor. Scan the doctor’s prescription and KinCare reminds you of every dose and every piece of advice.
          <b className="text-espresso"> KinCare never suggests medicines; only your doctor does.</b>
        </p>

        <div className="mt-8 flex flex-wrap items-center justify-between gap-3">
          <div className="flex gap-1 overflow-x-auto rounded-full border border-line bg-paper p-1 text-sm">
            {([["today", "Today", ClipboardList], ["vitals", "Vitals", HeartPulse], ["doctor", "Doctor", Stethoscope], ["rx", "Prescription", ScanLine], ["report", "Report", FileText]] as const).map(([id, label, Icon]) => (
              <button key={id} onClick={() => setTab(id)} className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-4 py-2 font-medium transition ${tab === id ? "bg-brown text-paper" : "text-muted hover:text-espresso"}`}>
                <Icon className="size-4" /> {label}
                {id === "doctor" && unread > 0 && tab !== "doctor" && <span className="rounded-full bg-danger px-1.5 text-[10px] font-semibold text-paper">{unread}</span>}
              </button>
            ))}
          </div>
          <div className="flex flex-wrap gap-1.5">
            {MEMBERS.map((m) => (
              <button key={m} onClick={() => setMember(m)} className={`rounded-full px-3 py-1.5 text-xs font-medium ${member === m ? "bg-espresso text-paper" : "bg-sand text-brown"}`}>{m}</button>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-6">
        {tab === "today" && <Today />}
        {tab === "vitals" && <Vitals member={member} shared={linked.includes(member)} />}
        {tab === "doctor" && <DoctorConnect member={member} />}
        {tab === "rx" && <Prescription member={member} onSaved={() => setTab("today")} />}
        {tab === "report" && <Report member={member} />}
      </div>
    </main>
  );
}

/* ---------------- Today: doses + advice + reminders ---------------- */

function Today() {
  const [data, setData] = useState<{ doses: Dose[]; advice: string[] } | null>(null);
  const [notifyOn, setNotifyOn] = useState(false);
  const [notifyMode, setNotifyMode] = useState<"push" | "local" | "denied" | null>(null);
  const [version, setVersion] = useState(0);
  const fired = useRef(new Set<string>());

  const load = useCallback(() => { setVersion((v) => v + 1); return getToday().then(setData).catch(() => setData({ doses: [], advice: [] })); }, []);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { try { setNotifyOn(Notification.permission === "granted"); } catch {} }, []);

  // While the app is open, fire a reminder when a dose time arrives.
  useEffect(() => {
    if (!notifyOn || !data) return;
    const tick = () => {
      const now = new Date();
      const hm = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
      data.doses.filter((d) => !d.taken_at && d.time <= hm).forEach((d) => {
        const key = `${d.med_id}-${d.slot}`;
        if (fired.current.has(key)) return;
        fired.current.add(key);
        // Same tag as the server push, so the phone never shows the dose twice.
        notifyNow(`Time for ${d.name}`, `${d.member}: ${d.strength} ${d.food ? "· " + d.food : ""}`.trim(), `dose-${d.med_id}-${d.slot}-${now.toLocaleDateString("en-CA")}`);
      });
    };
    tick();
    const t = setInterval(tick, 60000);
    return () => clearInterval(t);
  }, [notifyOn, data]);

  const enable = async () => {
    const mode = await enableNotifications();
    setNotifyMode(mode);
    setNotifyOn(mode !== "denied");
  };

  const toggle = async (d: Dose) => {
    await markDose(d.med_id, d.slot, !d.taken_at);
    load();
  };

  if (!data) return <p className="text-muted"><Loader2 className="inline size-4 animate-spin" /> Loading…</p>;
  const taken = data.doses.filter((d) => d.taken_at).length;

  return (
    <div className="grid gap-5 lg:grid-cols-[1.5fr_1fr]">
      <div className="card rounded-[2rem] p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-lg font-medium tracking-tight">Today’s doses</p>
            <p className="text-sm text-muted">{data.doses.length ? `${taken} of ${data.doses.length} taken` : "No prescription added yet"}</p>
          </div>
          <button onClick={enable} disabled={notifyOn} className={`inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-sm font-medium ${notifyOn ? "bg-safe/15 text-safe" : "bg-brown text-paper hover:bg-brown-2"}`}>
            {notifyOn ? <BellRing className="size-4" /> : <Bell className="size-4" />} {notifyOn ? "Reminders on" : "Turn on reminders"}
          </button>
        </div>
        {data.doses.length > 0 && (
          <div className="mt-4 h-2 overflow-hidden rounded-full bg-sand">
            <motion.div animate={{ width: `${(taken / data.doses.length) * 100}%` }} className="h-full rounded-full bg-safe" />
          </div>
        )}
        <div className="mt-5 space-y-5">
          {(["morning", "noon", "night"] as const).map((slot) => {
            const ds = data.doses.filter((d) => d.slot === slot);
            if (!ds.length) return null;
            const Icon = SLOT_ICON[slot];
            return (
              <div key={slot}>
                <p className="flex items-center gap-2 text-sm font-medium text-muted"><Icon className="size-4 text-brown" /> {SLOT_LABEL[slot]} · {ds[0].time}</p>
                <div className="mt-2 space-y-2">
                  {ds.map((d) => (
                    <button key={`${d.med_id}-${d.slot}`} onClick={() => toggle(d)}
                      className={`flex w-full items-center gap-3 rounded-2xl border px-4 py-3 text-left transition ${d.taken_at ? "border-safe/30 bg-safe/5" : "border-line bg-cream/50 hover:border-brown/30"}`}>
                      <span className={`grid size-7 shrink-0 place-items-center rounded-full border-2 ${d.taken_at ? "border-safe bg-safe text-paper" : "border-clay"}`}>
                        {d.taken_at && <Check className="size-4" strokeWidth={3} />}
                      </span>
                      <div className="flex-1">
                        <p className={`font-medium ${d.taken_at ? "text-muted line-through" : ""}`}>{d.name} <span className="font-normal text-muted">{d.strength}</span></p>
                        <p className="text-xs text-muted">{d.member}{d.food && ` · ${d.food}`}</p>
                      </div>
                      <Pill className="size-4 text-clay" />
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
          {data.doses.length === 0 && <p className="rounded-2xl bg-cream/60 p-6 text-center text-sm text-muted">Scan the doctor’s prescription in the Prescription tab to get a dose schedule.</p>}
        </div>
        <p className="mt-5 text-xs text-muted">
          {notifyMode === "push" ? "Phone notifications are on: doses, refills and recalls arrive even when KinCare is closed. "
            : notifyMode === "denied" ? "Notifications are blocked in this browser’s site settings. "
            : "Turn on reminders to get phone notifications, even when KinCare is closed. "}
          Once you record a purchase, WhatsApp reminders arrive at every dose too.
        </p>
      </div>

      <div className="space-y-4">
        <WhatsAppJoin />
        <BodySignal version={version} />
        <Refills version={version} />
        <BuyMeds onBought={load} />
        {data.doses.length > 0 && <Interactions />}
        <div className="rounded-[2rem] bg-brown p-6 text-paper">
          <p className="font-medium">Doctor’s advice</p>
          {data.advice.length ? (
            <ul className="mt-3 space-y-2">
              {data.advice.map((a) => <li key={a} className="flex items-center gap-2 text-sm"><Check className="size-4 text-paper/70" /> {a}</li>)}
            </ul>
          ) : <p className="mt-2 text-sm text-paper/70">Advice from the prescription (rest, fluids, follow-up…) will appear here.</p>}
        </div>
        <SavingsCard />
        <div className="card rounded-3xl p-5 text-sm">
          <p className="flex items-center gap-2 font-medium"><Watch className="size-4 text-brown" /> Live from a watch or oximeter</p>
          <p className="mt-1 text-muted">Open Vitals and connect a Bluetooth heart-rate watch, a pulse oximeter, or just use the phone camera. Share it with your doctor from the Doctor tab.</p>
        </div>
      </div>
    </div>
  );
}

/* ---------------- Vitals ---------------- */

function Vitals({ member, shared }: { member: string; shared: boolean }) {
  const [f, setF] = useState({ temp_c: "", bp_sys: "", bp_dia: "", pulse: "", spo2: "" });
  const [res, setRes] = useState<Assessment | null>(null);
  const [hist, setHist] = useState<Vital[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => getVitals(member).then(setHist).catch(() => {}), [member]);
  useEffect(() => { load(); setRes(null); }, [load]);
  useEffect(() => { const t = setInterval(load, 15000); return () => clearInterval(t); }, [load]); // live stream adds rows

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      const num = (s: string) => (s ? Number(s) : undefined);
      setRes(await addVitals({ member, temp_c: num(f.temp_c), bp_sys: num(f.bp_sys), bp_dia: num(f.bp_dia), pulse: num(f.pulse), spo2: num(f.spo2) }));
      load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const input = (k: keyof typeof f, label: string, ph: string, unit: string) => (
    <label className="block">
      <span className="text-xs font-medium text-muted">{label}</span>
      <div className="mt-1 flex items-center rounded-2xl border border-line bg-cream/60 pr-3 focus-within:border-brown/40">
        <input value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value.replace(/[^\d.]/g, "") })} inputMode="decimal" placeholder={ph} className="w-full bg-transparent px-4 py-3 outline-none placeholder:text-clay" />
        <span className="text-xs text-muted">{unit}</span>
      </div>
    </label>
  );

  return (
    <div className="grid gap-5 lg:grid-cols-[1fr_1.1fr]">
      <div className="lg:col-span-2"><LiveVitals member={member} sharedWithDoctor={shared} /></div>
      <div className="card rounded-[2rem] p-6">
        <p className="flex items-center gap-2 text-lg font-medium tracking-tight"><Thermometer className="size-5 text-brown" /> New reading for {member}</p>
        <div className="mt-5 grid grid-cols-2 gap-3">
          {input("temp_c", "Temperature", "37.0", "°C")}
          {input("spo2", "Oxygen (SpO₂)", "98", "%")}
          {input("bp_sys", "BP upper", "120", "mmHg")}
          {input("bp_dia", "BP lower", "80", "mmHg")}
          {input("pulse", "Pulse", "76", "bpm")}
        </div>
        <button onClick={submit} disabled={busy} className="mt-5 w-full rounded-full bg-brown py-3.5 font-medium text-paper hover:bg-brown-2 disabled:opacity-50">
          {busy ? <Loader2 className="mx-auto size-5 animate-spin" /> : "Check reading"}
        </button>
        {error && <p className="mt-3 text-sm text-danger">{error}</p>}
        <AnimatePresence>
          {res && (
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
              className={`mt-4 rounded-2xl p-5 text-paper ${res.level === "urgent" ? "bg-danger" : res.level === "doctor" ? "bg-warn" : "bg-safe"}`}>
              <p className="text-lg font-semibold">{res.level === "urgent" ? "Get help now" : res.level === "doctor" ? "See a doctor today" : "Looks okay"}</p>
              {res.reasons.length > 0 && <p className="mt-1 text-sm text-paper/90">{res.reasons.join(" · ")}</p>}
              <p className="mt-2 text-sm">{res.en}</p>
              <p className="mt-1 text-sm text-paper/85">{res.hi}</p>
              {res.level === "urgent" && (
                <div className="mt-3 flex flex-wrap gap-2">
                  <a href="tel:108" className="rounded-full bg-paper px-5 py-2 text-sm font-semibold text-danger">Call 108</a>
                  <a href="/sos" className="rounded-full border border-paper/60 px-5 py-2 text-sm font-semibold text-paper">Send SOS to family</a>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
        <p className="mt-4 text-[11px] text-muted">Thresholds are general adult red flags, not a diagnosis. KinCare will never tell you which medicine to take.</p>
      </div>

      <div className="card rounded-[2rem] p-6">
        <p className="text-lg font-medium tracking-tight">History</p>
        <Trend hist={hist} />
        <div className="mt-4 divide-y divide-line">
          {hist.length === 0 && <p className="py-6 text-center text-sm text-muted">No readings yet for {member}.</p>}
          {hist.slice(0, 12).map((h) => (
            <div key={h.id} className="flex flex-wrap items-center justify-between gap-2 py-2.5 text-sm">
              <span className="text-xs text-muted">{formatIST(h.at)}</span>
              <span className="font-mono text-xs">
                {[h.temp_c && `${h.temp_c}°C`, h.bp_sys && `BP ${h.bp_sys}/${h.bp_dia ?? "?"}`, h.pulse && `♥ ${h.pulse}`, h.spo2 && `SpO₂ ${h.spo2}%`].filter(Boolean).join(" · ")}
              </span>
              <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${h.level === "urgent" ? "bg-danger text-paper" : h.level === "doctor" ? "bg-warn-soft text-warn" : "bg-safe/15 text-safe"}`}>{h.level}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// Trend for one vital at a time, with the red-flag line drawn in. Same thresholds as the API's rules.
const METRICS = [
  { key: "temp_c", label: "Temperature", unit: "°C", min: 35, max: 41, flag: 38, above: true },
  { key: "spo2", label: "Oxygen", unit: "%", min: 85, max: 100, flag: 95, above: false },
  { key: "pulse", label: "Pulse", unit: "bpm", min: 40, max: 160, flag: 100, above: true },
  { key: "bp_sys", label: "BP upper", unit: "mmHg", min: 80, max: 200, flag: 140, above: true },
] as const;

function Trend({ hist }: { hist: Vital[] }) {
  const [k, setK] = useState<(typeof METRICS)[number]["key"]>("temp_c");
  const m = METRICS.find((x) => x.key === k)!;
  const pts = hist.filter((h) => h[k] != null).slice(0, 20).reverse();
  const y = (v: number) => 100 - ((Math.min(Math.max(v, m.min), m.max) - m.min) / (m.max - m.min)) * 100;
  const bad = (v: number) => (m.above ? v >= m.flag : v < m.flag);
  const x = (i: number) => (pts.length === 1 ? 50 : (i / (pts.length - 1)) * 100);
  return (
    <div className="mt-4">
      <div className="flex flex-wrap gap-1.5">
        {METRICS.map((x) => (
          <button key={x.key} onClick={() => setK(x.key)} className={`rounded-full px-3 py-1 text-xs ${k === x.key ? "bg-brown text-paper" : "border border-line text-muted"}`}>{x.label}</button>
        ))}
      </div>
      {pts.length === 0 ? <p className="mt-4 text-xs text-muted">No {m.label.toLowerCase()} readings yet.</p> : (
        <div className="relative mt-3 h-36">
          <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="absolute inset-0 size-full overflow-visible">
            <line x1="0" x2="100" y1={y(m.flag)} y2={y(m.flag)} stroke="currentColor" strokeDasharray="2 2" vectorEffect="non-scaling-stroke" className="text-danger/50" />
            <polyline fill="none" stroke="currentColor" strokeWidth="2" vectorEffect="non-scaling-stroke" className="text-brown"
              points={pts.map((p, i) => `${x(i)},${y(p[k] as number)}`).join(" ")} />
          </svg>
          {pts.map((p, i) => (
            <span key={p.id} title={`${p[k]} ${m.unit} · ${formatIST(p.at)}`} style={{ left: `${x(i)}%`, top: `${y(p[k] as number)}%` }}
              className={`absolute size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-paper ${bad(p[k] as number) ? "bg-danger" : "bg-brown"}`} />
          ))}
          <span className="absolute right-0 text-[10px] text-danger" style={{ top: `calc(${y(m.flag)}% - 14px)` }}>{m.flag}{m.unit}</span>
        </div>
      )}
      {pts.length > 0 && <p className="mt-2 text-xs text-muted">Last {pts.length} readings · latest {pts.at(-1)![k]} {m.unit}</p>}
    </div>
  );
}

/* ---------------- Prescription scan ---------------- */

const EMPTY_MED: RxMed = { name: "", strength: "", food: "", morning: 1, noon: 0, night: 0, days: 5, as_needed: false };

function Prescription({ member, onSaved }: { member: string; onSaved: () => void }) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [meds, setMeds] = useState<RxMed[]>([]);
  const [advice, setAdvice] = useState<string[]>([]);
  const [doctor, setDoctor] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [saved, setSaved] = useState<string | null>(null);

  const loadPlans = useCallback(() => getPlans().then(setPlans).catch(() => {}), []);
  useEffect(() => { loadPlans(); }, [loadPlans]);

  const onFile = async (file?: File) => {
    if (!file) return;
    setPreview(URL.createObjectURL(file));
    setBusy(true);
    setError(null);
    try {
      const r = await scanPrescription(file);
      setMeds(r.medicines.length ? r.medicines : [EMPTY_MED]);
      setAdvice(r.advice.map((a) => a.en));
      setDoctor(r.lines.find((l) => /^dr\.?\s/i.test(l)) ?? "");
      if (!r.medicines.length) setError("No medicines recognised. Add them by hand below, exactly as the doctor wrote.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const upd = (i: number, patch: Partial<RxMed>) => setMeds((m) => m.map((x, j) => (j === i ? { ...x, ...patch } : x)));

  const save = async () => {
    setError(null);
    try {
      const r = await savePlan({ member, doctor: doctor || undefined, advice, medicines: meds.filter((m) => m.name.trim()) });
      setSaved(r.flagged_batches.length ? `Saved. Warning: batch ${r.flagged_batches.join(", ")} appears in a regulator alert.` : "Saved. Reminders are ready in Today.");
      setMeds([]); setAdvice([]); setPreview(null);
      loadPlans();
      setTimeout(onSaved, 1200);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <div className="space-y-5">
      <div className="grid gap-5 lg:grid-cols-[1fr_1.4fr]">
        <div className="card rounded-[2rem] p-3">
          <input ref={fileRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={(e) => onFile(e.target.files?.[0])} />
          <button onClick={() => fileRef.current?.click()} className="group relative grid aspect-[4/3] w-full place-items-center overflow-hidden rounded-[1.6rem] bg-sand/60 hover:bg-sand">
            {preview ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={preview} alt="Prescription" className="size-full object-contain" />
            ) : (
              <div className="text-center">
                <span className="mx-auto grid size-16 place-items-center rounded-full bg-brown text-paper"><ScanLine className="size-7" /></span>
                <p className="mt-4 font-medium">Scan the doctor’s prescription</p>
                <p className="mt-1 text-sm text-muted">Printed prescriptions read best</p>
              </div>
            )}
            {busy && <div className="scan-line absolute inset-x-0 top-0 h-0.5 bg-brown shadow-[0_0_18px_4px_rgba(138,75,44,0.6)] [--scan-h:340px]" />}
          </button>
          <a href="/sample-prescription.png" download className="mt-3 block px-3 text-xs text-muted underline">Download a sample prescription to try</a>
        </div>

        <div className="card rounded-[2rem] p-6">
          <p className="text-lg font-medium tracking-tight">Confirm what the doctor prescribed for {member}</p>
          <p className="text-sm text-muted">Check every line against the paper. Only save what the doctor wrote.</p>
          {busy && <p className="mt-4 text-sm text-muted"><Loader2 className="inline size-4 animate-spin" /> Reading the prescription…</p>}
          {error && <p className="mt-3 text-sm text-danger">{error}</p>}
          {saved && <p className="mt-3 rounded-2xl bg-safe/10 px-4 py-2 text-sm text-safe">{saved}</p>}

          {meds.length > 0 && (
            <>
              <input value={doctor} onChange={(e) => setDoctor(e.target.value)} placeholder="Doctor" className="mt-4 w-full rounded-xl border border-line bg-cream/60 px-3 py-2 text-sm outline-none" />
              <div className="mt-3 space-y-2">
                {meds.map((m, i) => (
                  <div key={i} className="rounded-2xl border border-line bg-cream/40 p-3">
                    <div className="flex gap-2">
                      <input value={m.name} onChange={(e) => upd(i, { name: e.target.value })} placeholder="Medicine" className="min-w-0 flex-1 rounded-lg border border-line bg-paper px-2.5 py-1.5 text-sm font-medium outline-none" />
                      <input value={m.strength} onChange={(e) => upd(i, { strength: e.target.value })} placeholder="mg" className="w-20 rounded-lg border border-line bg-paper px-2.5 py-1.5 text-sm outline-none" />
                      <button onClick={() => setMeds(meds.filter((_, j) => j !== i))} className="grid size-8 place-items-center rounded-lg text-muted hover:text-danger" aria-label="Remove"><Trash2 className="size-4" /></button>
                    </div>
                    <div className="mt-2 flex flex-wrap items-center gap-1.5 text-xs">
                      {(["morning", "noon", "night"] as const).map((s) => (
                        <button key={s} onClick={() => upd(i, { [s]: m[s] ? 0 : 1 })} className={`rounded-full px-2.5 py-1 font-medium ${m[s] ? "bg-brown text-paper" : "bg-sand text-brown"}`}>{SLOT_LABEL[s]}</button>
                      ))}
                      <select value={m.food} onChange={(e) => upd(i, { food: e.target.value })} className="rounded-full border border-line bg-paper px-2 py-1 outline-none">
                        <option value="">any time</option><option>after food</option><option>before food</option>
                      </select>
                      <span className="flex items-center gap-1">
                        <input value={m.days ?? ""} onChange={(e) => upd(i, { days: e.target.value ? Number(e.target.value.replace(/\D/g, "")) : null })} className="w-10 rounded-md border border-line bg-paper px-1.5 py-1 text-center outline-none" /> days
                      </span>
                      <input value={m.batch ?? ""} onChange={(e) => upd(i, { batch: e.target.value })} placeholder="batch (optional)" className="w-32 rounded-md border border-line bg-paper px-2 py-1 font-mono outline-none" />
                    </div>
                  </div>
                ))}
              </div>
              <button onClick={() => setMeds([...meds, EMPTY_MED])} className="mt-2 inline-flex items-center gap-1 text-sm font-medium text-brown"><Plus className="size-4" /> Add a line</button>
              {advice.length > 0 && (
                <div className="mt-4">
                  <p className="text-sm font-medium">Doctor’s advice found</p>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {advice.map((a) => (
                      <button key={a} onClick={() => setAdvice(advice.filter((x) => x !== a))} className="rounded-full bg-brown/10 px-3 py-1 text-xs text-brown">{a} ×</button>
                    ))}
                  </div>
                </div>
              )}
              <button onClick={save} className="mt-5 w-full rounded-full bg-espresso py-3.5 font-medium text-paper hover:bg-brown-2">Save and set reminders</button>
            </>
          )}
          {!meds.length && !busy && (
            <button onClick={() => setMeds([EMPTY_MED])} className="mt-4 text-sm font-medium text-brown underline">Or type the prescription in by hand</button>
          )}
        </div>
      </div>

      {plans.length > 0 && (
        <div className="card rounded-[2rem] p-6">
          <p className="font-medium">Saved prescriptions</p>
          <div className="mt-3 divide-y divide-line">
            {plans.map((p) => (
              <div key={p.id} className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm">
                <div>
                  <p className="font-medium">{p.member} · {p.doctor ?? "Doctor"} <span className="font-normal text-muted">from {p.start_date}</span></p>
                  <p className="text-xs text-muted">{p.medicines.map((m) => m.name).join(", ")}</p>
                </div>
                <button onClick={() => deletePlan(p.id).then(loadPlans)} className="grid size-8 place-items-center rounded-full border border-line hover:border-danger hover:text-danger" aria-label="Delete"><Trash2 className="size-3.5" /></button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ---------------- Report for the doctor ---------------- */

function Report({ member }: { member: string }) {
  const [r, setR] = useState<Awaited<ReturnType<typeof getReport>> | null>(null);
  useEffect(() => { getReport(member).then(setR).catch(() => {}); }, [member]);
  if (!r) return <p className="text-muted"><Loader2 className="inline size-4 animate-spin" /> Building report…</p>;

  return (
    <div>
      <div className="mb-4 flex justify-end print:hidden">
        <button onClick={() => window.print()} className="inline-flex items-center gap-2 rounded-full bg-brown px-5 py-2.5 text-sm font-medium text-paper"><Printer className="size-4" /> Print / save PDF</button>
      </div>
      <article className="card rounded-3xl p-8 sm:p-10 print:border-0 print:shadow-none">
        <div className="flex items-start justify-between border-b border-line pb-5">
          <div>
            <p className="text-xl font-semibold tracking-tight">kincare.</p>
            <p className="text-xs text-muted">Care report for the doctor</p>
          </div>
          <div className="text-right text-xs text-muted">
            <p className="text-base font-medium text-espresso">{r.member}</p>
            <p>Generated {formatIST(r.generated_at)}</p>
          </div>
        </div>

        <h3 className="mt-6 font-medium">Prescriptions</h3>
        {r.plans.length === 0 && <p className="text-sm text-muted">None recorded.</p>}
        {r.plans.map((p) => (
          <div key={p.id} className="mt-2 text-sm">
            <p className="text-muted">{p.doctor ?? "Doctor"} · from {p.start_date}</p>
            <table className="mt-1 w-full">
              <tbody className="divide-y divide-line">
                {p.medicines.map((m) => {
                  const a = r.adherence.find((x) => x.name === m.name);
                  return (
                    <tr key={m.id}>
                      <td className="py-1.5 font-medium">{m.name} {m.strength}</td>
                      <td className="py-1.5 font-mono text-xs">{m.morning}-{m.noon}-{m.night}</td>
                      <td className="py-1.5 text-xs text-muted">{m.food}{m.days ? ` · ${m.days} days` : ""}</td>
                      <td className="py-1.5 text-right text-xs">{a && a.due ? `${a.taken}/${a.due} doses taken` : "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {p.advice.length > 0 && <p className="mt-1 text-xs text-muted">Advice: {p.advice.join(", ")}</p>}
          </div>
        ))}

        <h3 className="mt-6 font-medium">Readings</h3>
        <table className="mt-1 w-full text-sm">
          <thead className="text-left text-xs text-muted"><tr><th className="py-1 font-normal">When</th><th className="font-normal">Temp</th><th className="font-normal">BP</th><th className="font-normal">Pulse</th><th className="font-normal">SpO₂</th><th className="font-normal">Flag</th></tr></thead>
          <tbody className="divide-y divide-line">
            {r.vitals.slice(0, 20).map((v) => (
              <tr key={v.id}>
                <td className="py-1.5 text-xs">{formatIST(v.at)}</td>
                <td className={v.temp_c && v.temp_c >= 38 ? "font-medium text-danger" : ""}>{v.temp_c ?? "—"}</td>
                <td>{v.bp_sys ? `${v.bp_sys}/${v.bp_dia ?? "?"}` : "—"}</td>
                <td>{v.pulse ?? "—"}</td>
                <td>{v.spo2 ?? "—"}</td>
                <td className="text-xs uppercase">{v.level}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {r.vitals.length === 0 && <p className="text-sm text-muted">No readings recorded.</p>}
        <p className="mt-8 border-t border-line pt-3 text-[11px] text-muted">Patient-entered readings and doses. Not a diagnosis. Prepared with KinCare.</p>
      </article>
    </div>
  );
}
