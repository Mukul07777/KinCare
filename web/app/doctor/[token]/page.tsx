"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import {
  AlertTriangle, CheckCircle2, Gauge, HeartPulse, Loader2, MapPin, PhoneCall, Pill, Printer, Send, ShieldCheck, Siren, Stethoscope, Thermometer, Video, Wind,
} from "lucide-react";
import { LiveChart } from "@/components/LiveChart";
import {
  doctorSend, formatIST, getDoctorInteractions, getDoctorLive, getDoctorView, videoUrl,
  type DoctorMessage, type DoctorView, type Interaction, type LiveSample, type News2,
} from "@/lib/api";

const SOURCE_LABEL: Record<string, string> = {
  ble_hr: "Bluetooth heart-rate", ble_oximeter: "Bluetooth oximeter", camera: "Phone camera", replay: "Recorded ICU patient (BIDMC)", manual: "Typed in",
  health_connect: "Health Connect", healthkit: "Apple Health",
};
const RISK_STYLE: Record<News2["risk"], string> = {
  low: "bg-safe text-paper", "low-medium": "bg-warn text-paper", medium: "bg-danger/85 text-paper", high: "bg-danger text-paper",
};
const KINDS: { id: DoctorMessage["kind"]; label: string; hint: string }[] = [
  { id: "advice", label: "Advice", hint: "Added to the patient's daily reminders" },
  { id: "note", label: "Note", hint: "A message in the thread" },
  { id: "followup", label: "Follow-up", hint: "When to come back or test again" },
  { id: "urgent", label: "Urgent", hint: "Shown in red to the patient" },
];
const PART_LABEL: Record<string, string> = { spo2: "SpO₂", bp: "Systolic BP", pulse: "Pulse", temp: "Temperature" };

export default function DoctorConsole() {
  const { token } = useParams<{ token: string }>();
  const [view, setView] = useState<DoctorView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [samples, setSamples] = useState<LiveSample[]>([]);
  const [online, setOnline] = useState(false);
  const [source, setSource] = useState<string | null>(null);
  const [msgs, setMsgs] = useState<DoctorMessage[]>([]);
  const [inter, setInter] = useState<{ interactions: Interaction[]; no_label: string[] } | null>(null);
  const [kind, setKind] = useState<DoctorMessage["kind"]>("advice");
  const [text, setText] = useState("");
  const [name, setName] = useState("");
  const [sent, setSent] = useState<string | null>(null);
  const since = useRef(0);
  const msgSince = useRef(0);

  const loadView = useCallback(async () => {
    try {
      const v = await getDoctorView(token);
      setView(v);
      setMsgs(v.messages);
      msgSince.current = v.messages.at(-1)?.id ?? 0;
    } catch (e) { setError((e as Error).message); }
  }, [token]);

  useEffect(() => {
    loadView();
    getDoctorInteractions(token).then(setInter).catch(() => setInter({ interactions: [], no_label: [] }));
    const t = setInterval(loadView, 30000);
    return () => clearInterval(t);
  }, [loadView, token]);

  // Live: new samples + messages every 2 s.
  useEffect(() => {
    if (error) return;
    const poll = async () => {
      try {
        const r = await getDoctorLive(token, since.current, msgSince.current);
        if (r.samples.length) {
          since.current = r.samples.at(-1)!.id;
          setSamples((s) => [...s, ...r.samples].slice(-300));
        }
        if (r.messages.length) {
          msgSince.current = r.messages.at(-1)!.id;
          setMsgs((m) => [...m, ...r.messages.filter((x) => !m.some((y) => y.id === x.id))]);
        }
        setOnline(r.online);
        setSource(r.source);
        setView((v) => (v ? { ...v, latest: r.latest, news2: r.news2 } : v));
      } catch { /* keep last data on screen */ }
    };
    poll();
    const t = setInterval(poll, 2000);
    return () => clearInterval(t);
  }, [token, error]);

  const send = async () => {
    if (!text.trim()) return;
    try {
      const r = await doctorSend(token, { kind, text, doctor: name || undefined });
      setSent(r.added_to_plan ? "Sent and added to the patient's daily reminders." : "Sent to the patient.");
      setText("");
      setTimeout(() => setSent(null), 3000);
    } catch (e) { setSent((e as Error).message); }
  };

  if (error) return (
    <main className="mx-auto max-w-xl px-4 py-24 text-center">
      <ShieldCheck className="mx-auto size-10 text-brown" />
      <h1 className="mt-4 text-2xl font-semibold">Link not available</h1>
      <p className="mt-2 text-muted">{error}. Ask the patient to send a new link from KinCare.</p>
    </main>
  );
  if (!view) return <main className="flex min-h-[60vh] items-center justify-center text-muted"><Loader2 className="mr-2 size-5 animate-spin" /> Opening patient record…</main>;

  const L = view.latest;
  const pulses = samples.map((s) => s.pulse);
  const oxy = samples.map((s) => s.spo2);
  const openSos = view.sos.filter((s) => !s.resolved_at);
  const lastCall = [...msgs].reverse().find((m) => m.author === "patient" && m.kind === "call");
  const answered = lastCall && msgs.some((m) => m.author === "doctor" && m.id > lastCall.id);
  const meds = view.plans.flatMap((p) => p.medicines.map((m) => ({ ...m, doctor: p.doctor })));
  const adh = (n: string) => view.adherence.find((a) => a.name === n);
  const totals = view.adherence.reduce((a, x) => ({ due: a.due + x.due, taken: a.taken + x.taken }), { due: 0, taken: 0 });
  const advice = [...new Set(view.plans.flatMap((p) => p.advice))];

  return (
    <main className="mx-auto max-w-6xl px-4 pb-20 pt-8 sm:px-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-teal"><Stethoscope className="size-4" /> Doctor console</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-5xl">{view.member}</h1>
          <p className="mt-1 text-sm text-muted">
            {view.doctor ? `Shared with ${view.doctor}` : "Shared by the patient"} · link expires {formatIST(view.expires_at)}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 print:hidden">
          <span className={`inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-semibold ${online ? "bg-danger/10 text-danger" : "bg-sand text-muted"}`}>
            <span className={`size-2 rounded-full ${online ? "animate-pulse bg-danger" : "bg-clay"}`} />
            {online ? `LIVE · ${SOURCE_LABEL[source ?? ""] ?? source}` : "Not streaming now"}
          </span>
          <a href={videoUrl(view.room)} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 rounded-full bg-espresso px-4 py-2 text-sm font-medium text-paper"><Video className="size-4" /> Video consult</a>
          <button onClick={() => window.print()} className="inline-flex items-center gap-1.5 rounded-full border border-line px-4 py-2 text-sm font-medium"><Printer className="size-4" /> Print</button>
        </div>
      </div>

      {source === "replay" && online && <p className="mt-4 rounded-2xl bg-sand px-4 py-2 text-xs text-brown">Demo: this stream replays a real, de-identified ICU recording (PhysioNet BIDMC), not this patient&apos;s own reading.</p>}

      {/* Alerts */}
      <div className="mt-6 space-y-3">
        {openSos.map((s) => (
          <div key={s.id} className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-danger p-4 text-paper">
            <p className="flex items-center gap-2 font-semibold"><Siren className="size-5" /> SOS sent {formatIST(s.at)}</p>
            {s.lat !== null && <a href={`https://maps.google.com/?q=${s.lat},${s.lng}`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 rounded-full bg-paper px-4 py-1.5 text-sm font-semibold text-danger"><MapPin className="size-4" /> Location</a>}
          </div>
        ))}
        {view.assessment.level === "urgent" && (
          <div className="flex items-center gap-2 rounded-2xl border border-danger/40 bg-danger/10 p-4 text-sm font-medium text-danger">
            <AlertTriangle className="size-5" /> Red flag: {view.assessment.reasons.join(" · ")}
          </div>
        )}
        {lastCall && !answered && (
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-sand p-4 text-sm">
            <p className="flex items-center gap-2 font-medium"><PhoneCall className="size-4 text-brown" /> Patient asked for a video consult · {formatIST(lastCall.at)}</p>
            <a href={videoUrl(view.room)} target="_blank" rel="noreferrer" className="rounded-full bg-brown px-4 py-1.5 font-semibold text-paper">Join now</a>
          </div>
        )}
      </div>

      {/* Vitals row */}
      <div className="mt-6 grid gap-4 lg:grid-cols-[0.9fr_1.2fr_1.2fr]">
        <div className={`rounded-[2rem] p-6 ${RISK_STYLE[view.news2.risk]}`}>
          <p className="flex items-center gap-2 text-sm font-medium opacity-85"><Gauge className="size-4" /> NEWS2 early-warning</p>
          <p className="mt-2 font-mono text-6xl font-semibold">{view.news2.score}</p>
          <p className="mt-1 text-lg font-semibold capitalize">{view.news2.risk} risk</p>
          <p className="text-sm opacity-90">{view.news2.action}</p>
          <div className="mt-4 space-y-1 text-xs">
            {Object.entries(view.news2.parts).map(([k, v]) => (
              <div key={k} className="flex justify-between border-b border-paper/20 pb-1"><span>{PART_LABEL[k] ?? k}</span><span className="font-mono">+{v}</span></div>
            ))}
          </div>
          <p className="mt-3 text-[11px] opacity-75">Partial score: {view.news2.missing.join(" and ")} not measured at home.</p>
        </div>

        <Tile icon={HeartPulse} label="Pulse" value={L.pulse} unit="bpm" at={L.at.pulse} red={L.pulse !== null && (L.pulse > 100 || L.pulse < 55)}>
          <LiveChart values={pulses} min={40} max={160} flag={100} color="var(--danger)" height={100} />
          <p className="mt-1 text-[11px] text-muted">{samples.length ? `Last ${samples.length} live samples` : "No live stream yet"}</p>
        </Tile>
        <Tile icon={Wind} label="Oxygen (SpO₂)" value={L.spo2} unit="%" at={L.at.spo2} red={L.spo2 !== null && L.spo2 < 95}>
          <LiveChart values={oxy} min={85} max={100} flag={95} height={100} />
          <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
            <p className="rounded-xl bg-cream/70 px-3 py-2"><Thermometer className="mr-1 inline size-3.5 text-brown" />{L.temp_c ?? "--"} °C</p>
            <p className="rounded-xl bg-cream/70 px-3 py-2">BP {L.bp_sys ?? "--"}/{L.bp_dia ?? "--"}</p>
          </div>
        </Tile>
      </div>

      {/* 24 h + history */}
      <div className="mt-4 grid gap-4 lg:grid-cols-[0.9fr_2.4fr]">
        <div className="card rounded-[2rem] p-6 text-sm">
          <p className="font-medium">Last 24 hours (live)</p>
          {view.stats_24h.n ? (
            <dl className="mt-3 space-y-2">
              <Row k="Samples" v={view.stats_24h.n} />
              <Row k="Pulse min / avg / max" v={`${view.stats_24h.pmin ?? "-"} / ${view.stats_24h.pavg ?? "-"} / ${view.stats_24h.pmax ?? "-"}`} />
              <Row k="SpO₂ lowest / avg" v={`${view.stats_24h.smin ?? "-"} / ${view.stats_24h.savg ?? "-"}`} />
              <Row k="Seconds with SpO₂ < 92%" v={view.stats_24h.dips ?? 0} red={!!view.stats_24h.dips} />
              <Row k="Seconds with pulse > 120" v={view.stats_24h.tachy ?? 0} red={!!view.stats_24h.tachy} />
            </dl>
          ) : <p className="mt-3 text-muted">No live data in the last day.</p>}
        </div>
        <div className="card rounded-[2rem] p-6">
          <p className="text-sm font-medium">Reading history</p>
          <div className="mt-3 max-h-64 divide-y divide-line overflow-y-auto text-sm">
            {view.vitals.length === 0 && <p className="py-4 text-muted">No readings yet.</p>}
            {view.vitals.slice(0, 30).map((h) => (
              <div key={h.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                <span className="text-xs text-muted">{formatIST(h.at)} · {SOURCE_LABEL[h.source ?? "manual"] ?? h.source}</span>
                <span className="font-mono text-xs">{[h.temp_c && `${h.temp_c}°C`, h.bp_sys && `BP ${h.bp_sys}/${h.bp_dia ?? "?"}`, h.pulse && `♥ ${h.pulse}`, h.spo2 && `SpO₂ ${h.spo2}%`].filter(Boolean).join(" · ")}</span>
                <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${h.level === "urgent" ? "bg-danger text-paper" : h.level === "doctor" ? "bg-warn-soft text-warn" : "bg-safe/15 text-safe"}`}>{h.level}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Medicines + messages */}
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <div className="space-y-4">
          <div className="card rounded-[2rem] p-6">
            <div className="flex items-center justify-between">
              <p className="flex items-center gap-2 font-medium"><Pill className="size-4 text-brown" /> Medicines</p>
              {totals.due > 0 && <span className="text-xs text-muted">Adherence {Math.round((totals.taken / totals.due) * 100)}% ({totals.taken}/{totals.due} doses)</span>}
            </div>
            <div className="mt-3 space-y-3">
              {meds.length === 0 && <p className="text-sm text-muted">No prescription saved.</p>}
              {meds.map((m) => {
                const a = adh(m.name);
                const pct = a && a.due ? Math.round((a.taken / a.due) * 100) : null;
                return (
                  <div key={m.id} className="text-sm">
                    <div className="flex justify-between gap-2">
                      <span className="font-medium">{m.name} {m.strength}</span>
                      <span className="font-mono text-xs text-muted">{m.morning}-{m.noon}-{m.night}{m.as_needed ? " SOS" : ""}</span>
                    </div>
                    <p className="text-xs text-muted">{[m.food && `${m.food} food`, m.days && `${m.days} days`, m.doctor && `by ${m.doctor}`, m.batch && `batch ${m.batch}`].filter(Boolean).join(" · ")}</p>
                    {pct !== null && (
                      <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-sand">
                        <div className={`h-full rounded-full ${pct < 70 ? "bg-danger" : pct < 90 ? "bg-warn" : "bg-safe"}`} style={{ width: `${pct}%` }} />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
            {advice.length > 0 && (
              <div className="mt-4 rounded-2xl bg-cream/70 p-3 text-xs">
                <p className="font-medium">Advice the patient is following</p>
                <ul className="mt-1 list-disc pl-4 text-muted">{advice.map((a) => <li key={a}>{a}</li>)}</ul>
              </div>
            )}
          </div>
          <div className="card rounded-[2rem] p-6 text-sm">
            <p className="font-medium">Label interactions (openFDA)</p>
            {!inter ? <p className="mt-2 text-muted"><Loader2 className="inline size-4 animate-spin" /> Checking…</p>
              : inter.interactions.length === 0 ? <p className="mt-2 flex items-center gap-1.5 text-safe"><CheckCircle2 className="size-4" /> No pair mentions the other on its label.</p>
              : inter.interactions.map((i, n) => (
                <div key={n} className={`mt-2 rounded-xl p-3 ${i.severity === "high" ? "bg-danger/10" : "bg-sand"}`}>
                  <p className="font-medium">{i.a} + {i.b} <span className="text-xs text-muted">({i.section})</span></p>
                  <p className="mt-1 text-xs text-muted">{i.evidence}</p>
                </div>
              ))}
          </div>
        </div>

        <div className="card flex flex-col rounded-[2rem] p-6 print:hidden">
          <p className="font-medium">Messages with {view.member}</p>
          <div className="mt-3 flex-1 space-y-3 overflow-y-auto" style={{ maxHeight: 380 }}>
            {msgs.length === 0 && <p className="rounded-2xl bg-cream/60 p-6 text-center text-sm text-muted">No messages yet.</p>}
            {msgs.map((m) => (
              <div key={m.id} className={`max-w-[85%] rounded-2xl p-3 text-sm ${m.author === "doctor" ? "ml-auto bg-brown text-paper" : "bg-sand"}`}>
                <p className="text-[10px] font-semibold uppercase tracking-wider opacity-70">{m.author === "doctor" ? `You · ${m.kind}` : m.kind === "call" ? "Patient · call request" : "Patient"}</p>
                <p className="mt-1 whitespace-pre-wrap">{m.text}</p>
                <p className="mt-1 text-[10px] opacity-60">{formatIST(m.at)}</p>
              </div>
            ))}
          </div>
          <div className="mt-4 flex flex-wrap gap-1.5">
            {KINDS.map((k) => (
              <button key={k.id} onClick={() => setKind(k.id)} title={k.hint}
                className={`rounded-full px-3 py-1.5 text-xs font-medium ${kind === k.id ? (k.id === "urgent" ? "bg-danger text-paper" : "bg-espresso text-paper") : "bg-sand text-brown"}`}>{k.label}</button>
            ))}
          </div>
          <p className="mt-1 text-[11px] text-muted">{KINDS.find((k) => k.id === kind)?.hint}</p>
          {!view.doctor && <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name (shown to the patient)" className="mt-3 rounded-full border border-line bg-cream/60 px-4 py-2.5 text-sm outline-none" />}
          <div className="mt-2 flex gap-2">
            <textarea value={text} onChange={(e) => setText(e.target.value)} rows={2} placeholder={kind === "advice" ? "e.g. Check oxygen every 2 hours; come in if below 94%" : "Write to the patient…"}
              className="flex-1 resize-none rounded-2xl border border-line bg-cream/60 px-4 py-2.5 text-sm outline-none" />
            <button onClick={send} className="self-end rounded-full bg-brown p-3 text-paper"><Send className="size-4" /></button>
          </div>
          {sent && <p className="mt-2 text-xs text-safe">{sent}</p>}
        </div>
      </div>

      <p className="mt-8 text-center text-[11px] text-muted">
        Shared by the patient through KinCare. Home readings and camera pulse are estimates; confirm clinically. KinCare never suggests medicines.
      </p>
    </main>
  );
}

function Tile({ icon: Icon, label, value, unit, at, red, children }: {
  icon: typeof HeartPulse; label: string; value: number | null; unit: string; at?: string; red: boolean; children: React.ReactNode;
}) {
  return (
    <div className="card rounded-[2rem] p-6">
      <p className="flex items-center gap-2 text-sm font-medium text-muted"><Icon className="size-4 text-brown" /> {label}</p>
      <p className={`mt-1 font-mono text-5xl font-semibold tabular-nums ${red ? "text-danger" : ""}`}>{value ?? "--"}<span className="ml-1 text-base font-normal text-muted">{unit}</span></p>
      {at && <p className="text-[11px] text-muted">{formatIST(at)}</p>}
      <div className="mt-3">{children}</div>
    </div>
  );
}

function Row({ k, v, red }: { k: string; v: string | number; red?: boolean }) {
  return <div className="flex justify-between gap-2"><dt className="text-muted">{k}</dt><dd className={`font-mono ${red ? "font-semibold text-danger" : ""}`}>{v}</dd></div>;
}
