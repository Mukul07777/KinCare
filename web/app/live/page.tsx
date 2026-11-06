"use client";

import { RoleGate } from "@/components/RoleGate";
import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Bot, Check, FileSearch, Loader2, MessageCircle, Phone, PhoneCall, Play, Radar, Send, Users, Volume2 } from "lucide-react";
import { getRecallConfig, recallStreamUrl, speak, startRecall, type RecallConfig } from "@/lib/api";

type EvData = {
  t?: number;
  source?: string;
  step?: string;
  error?: string;
  rows?: number;
  streaming_url?: string;
  month?: string;
  alerts?: number;
  who?: string;
  where?: string;
  city?: string;
  batch?: string;
  medicine?: string;
  category?: string;
  channel?: string;
  language?: string;
  status?: string;
  message?: string;
  seconds?: number;
  affected?: number;
  notifications?: number;
  checkin?: string;
};
type Ev = { type: string; data: EvData };
type AgentState = { name: string; status: "idle" | "running" | "done" | "failed"; step?: string; rows?: number; stream?: string };

const STEPS = [
  { id: "agents", label: "Agents read sources", icon: Bot },
  { id: "list", label: "New list parsed", icon: FileSearch },
  { id: "match", label: "Holders matched", icon: Users },
  { id: "notify", label: "Patients notified", icon: Send },
];

function loadPrefs() {
  try {
    return JSON.parse(localStorage.getItem("kincare.live") ?? "{}");
  } catch {
    return {};
  }
}

function Live() {
  const [cfg, setCfg] = useState<RecallConfig | null>(null);
  const [form, setForm] = useState({ name: "", phone: "", language: "hi", city: "New Delhi", scope: "latest" });
  const [events, setEvents] = useState<Ev[]>([]);
  const [agents, setAgents] = useState<Record<string, AgentState>>({});
  const [running, setRunning] = useState(false);
  const [t, setT] = useState(0);
  const [autoSpeak, setAutoSpeak] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const t0 = useRef(0);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const es = useRef<EventSource | null>(null);
  const spoke = useRef(false);

  useEffect(() => {
    getRecallConfig().then((c) => {
      setCfg(c);
      setAgents(Object.fromEntries(c.sources.map((s) => [s.id, { name: s.name, status: "idle" }])));
    }).catch((e) => setError(e.message));
    setForm((f) => ({ ...f, ...loadPrefs() }));
    return () => { es.current?.close(); if (timer.current) clearInterval(timer.current); };
  }, []);

  const has = (type: string) => events.some((e) => e.type === type);
  const done = events.find((e) => e.type === "run_complete");
  const list = events.find((e) => e.type === "list_ready");
  const matches = events.filter((e) => e.type === "match");
  const notes = events.filter((e) => e.type === "notified");
  const whatsapp = notes.find((n) => n.data.channel === "whatsapp");
  const voice = notes.find((n) => n.data.channel === "voice");
  const stream = Object.values(agents).find((a) => a.stream)?.stream;

  const stepState = (id: string) => {
    const reached = { agents: has("run_started"), list: !!list, match: has("matching_done"), notify: notes.length > 0 }[id];
    const finished = { agents: !!list, list: has("matching_done"), match: notes.length > 0 || (has("matching_done") && !matches.length), notify: !!done }[id];
    return finished ? "done" : reached ? "active" : "idle";
  };

  const start = async () => {
    setError(null);
    setEvents([]);
    spoke.current = false;
    setAgents((a) => Object.fromEntries(Object.entries(a).map(([k, v]) => [k, { name: v.name, status: "idle" }])));
    try { localStorage.setItem("kincare.live", JSON.stringify({ name: form.name, phone: form.phone, language: form.language, city: form.city })); } catch {}
    try {
      const { run_id } = await startRecall({ scope: form.scope, demo_phone: form.phone || undefined, demo_name: form.name || undefined, demo_language: form.language, demo_city: form.city || undefined });
      setRunning(true);
      t0.current = performance.now();
      timer.current = setInterval(() => setT((performance.now() - t0.current) / 1000), 50);
      const src = new EventSource(recallStreamUrl(run_id));
      es.current = src;
      const types = ["run_started", "agent_started", "agent_stream", "agent_progress", "agent_done", "agent_failed", "sync_failed", "list_ready", "match", "matching_done", "notified", "run_complete"];
      types.forEach((type) =>
        src.addEventListener(type, (m) => {
          const data = JSON.parse((m as MessageEvent).data);
          setEvents((prev) => [...prev, { type, data }]);
          if (data.source) {
            setAgents((prev) => {
              const a = { ...(prev[data.source] ?? { name: data.source, status: "idle" }) };
              if (type === "agent_started") a.status = "running";
              if (type === "agent_progress") a.step = data.step;
              if (type === "agent_stream") a.stream = data.streaming_url;
              if (type === "agent_done") { a.status = "done"; a.rows = data.rows; }
              if (type === "agent_failed") { a.status = "failed"; a.step = data.error; }
              return { ...prev, [data.source]: a };
            });
          }
          if (type === "run_complete") {
            src.close();
            if (timer.current) clearInterval(timer.current);
            setT(data.seconds ?? 0);
            setRunning(false);
          }
        }),
      );
      src.onerror = () => { if (src.readyState === EventSource.CLOSED) setRunning(false); };
    } catch (e) {
      setError((e as Error).message);
    }
  };

  // Ring the "phone" once the voice notification arrives.
  useEffect(() => {
    if (voice && autoSpeak && !spoke.current) {
      spoke.current = true;
      setTimeout(() => speak(voice.data.message ?? "", voice.data.language ?? "hi"), 900);
    }
  }, [voice, autoSpeak]);

  return (
    <main className="mx-auto max-w-7xl px-4 pt-8 sm:px-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="inline-flex items-center gap-2 rounded-full border border-line bg-paper px-3 py-1 text-xs font-medium text-brown">
            <span className="relative flex size-2"><span className="absolute inline-flex size-full animate-ping rounded-full bg-danger opacity-60" /><span className="relative inline-flex size-2 rounded-full bg-danger" /></span>
            Live recall
          </p>
          <h1 className="mt-3 text-4xl font-medium tracking-[-0.03em] sm:text-6xl">
            From regulator list <span className="text-mocha">to patient’s phone.</span>
          </h1>
        </div>
        {cfg && (
          <div className="flex gap-2 text-xs">
            <span className={`rounded-full px-3 py-1.5 font-medium ${cfg.agents === "tinyfish" ? "bg-brown text-paper" : "bg-sand text-brown"}`}>
              Agents: {cfg.agents === "tinyfish" ? "TinyFish live browsers" : "direct readers"}
            </span>
            <span className={`rounded-full px-3 py-1.5 font-medium ${cfg.twilio ? "bg-safe text-paper" : "bg-sand text-brown"}`}>
              Delivery: {cfg.twilio ? "Twilio (real phones)" : "outbox + browser voice"}
            </span>
          </div>
        )}
      </div>

      {error && <p className="mt-4 rounded-2xl border border-danger/20 bg-danger/5 px-5 py-3 text-sm text-danger">{error}</p>}

      <div className="mt-8 grid gap-5 lg:grid-cols-[1.35fr_1fr]">
        {/* Left column */}
        <div className="space-y-5">
          {/* Control + timer */}
          <div className="grid gap-5 rounded-[2rem] bg-espresso p-6 text-paper sm:grid-cols-[1fr_auto] sm:items-center sm:p-8">
            <div className="grid gap-3 sm:grid-cols-2">
              {([["name", "Patient name", "e.g. Ravi"], ["phone", "Phone (gets the alert)", "98xxxxxxxx"]] as const).map(([k, label, ph]) => (
                <label key={k} className="block text-xs text-paper/60">
                  {label}
                  <input value={form[k]} onChange={(e) => setForm({ ...form, [k]: e.target.value })} placeholder={ph} disabled={running}
                    className="mt-1 w-full rounded-xl border border-paper/15 bg-paper/10 px-3 py-2.5 text-sm text-paper outline-none placeholder:text-paper/30 focus:border-paper/40" />
                </label>
              ))}
              <div className="flex gap-2 text-xs">
                {[["hi", "हिन्दी"], ["en", "English"]].map(([v, l]) => (
                  <button key={v} onClick={() => setForm({ ...form, language: v })} disabled={running}
                    className={`flex-1 rounded-xl px-3 py-2.5 font-medium transition ${form.language === v ? "bg-paper text-espresso" : "bg-paper/10 text-paper/70"}`}>{l}</button>
                ))}
              </div>
              <div className="flex gap-2 text-xs">
                {[["latest", "Newest list"], ["all", "All alerts"]].map(([v, l]) => (
                  <button key={v} onClick={() => setForm({ ...form, scope: v })} disabled={running}
                    className={`flex-1 rounded-xl px-3 py-2.5 font-medium transition ${form.scope === v ? "bg-paper text-espresso" : "bg-paper/10 text-paper/70"}`}>{l}</button>
                ))}
              </div>
            </div>
            <div className="text-center">
              <p className="font-mono text-6xl font-medium tabular-nums tracking-tight sm:text-7xl">{t.toFixed(1)}<span className="text-2xl text-paper/50">s</span></p>
              <button onClick={start} disabled={running || !cfg}
                className="mt-4 inline-flex items-center gap-2 rounded-full bg-danger px-7 py-3.5 font-medium text-paper shadow-[0_10px_30px_-8px_rgba(196,69,47,0.8)] transition hover:brightness-110 disabled:opacity-50">
                {running ? <Loader2 className="size-5 animate-spin" /> : <Radar className="size-5" />}
                {running ? "Recall running…" : done ? "Run again" : "Start recall"}
              </button>
            </div>
          </div>

          {/* Pipeline */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {STEPS.map(({ id, label, icon: Icon }) => {
              const s = stepState(id);
              return (
                <div key={id} className={`card rounded-2xl p-4 transition ${s === "done" ? "bg-brown text-paper" : s === "active" ? "ring-2 ring-brown/40" : ""}`}>
                  <div className="flex items-center justify-between">
                    <Icon className={`size-5 ${s === "done" ? "" : "text-brown"}`} />
                    {s === "done" ? <Check className="size-4" /> : s === "active" ? <Loader2 className="size-4 animate-spin text-brown" /> : null}
                  </div>
                  <p className="mt-3 text-sm font-medium">{label}</p>
                  <p className={`text-xs ${s === "done" ? "text-paper/70" : "text-muted"}`}>
                    {id === "list" && list ? `${list.data.alerts} alerts · ${list.data.month}` : id === "match" && has("matching_done") ? `${matches.length} affected` : id === "notify" && notes.length ? `${notes.length} sent` : " "}
                  </p>
                </div>
              );
            })}
          </div>

          {/* Agents */}
          <div className="card rounded-3xl p-5">
            <p className="flex items-center gap-2 font-medium"><Bot className="size-4 text-brown" /> One agent per source, in parallel</p>
            <div className="mt-4 space-y-2">
              {Object.entries(agents).map(([id, a]) => (
                <div key={id} className="flex items-center gap-3 rounded-2xl bg-cream/60 px-4 py-3">
                  <span className={`size-2.5 shrink-0 rounded-full ${a.status === "done" ? "bg-safe" : a.status === "running" ? "animate-pulse bg-brown" : a.status === "failed" ? "bg-danger" : "bg-clay"}`} />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium">{a.name}</p>
                    <p className="truncate text-xs text-muted">{a.step ?? (a.status === "idle" ? "Waiting" : "")}</p>
                  </div>
                  {a.rows !== undefined && <span className="font-mono text-sm">{a.rows} rows</span>}
                </div>
              ))}
            </div>
            {stream && (
              <div className="mt-4 overflow-hidden rounded-2xl border border-line">
                <p className="bg-sand/60 px-3 py-1.5 text-xs text-muted">TinyFish live browser</p>
                <iframe src={stream} className="h-72 w-full" title="Agent live view" />
              </div>
            )}
          </div>

          {/* Matches */}
          <AnimatePresence>
            {matches.length > 0 && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="card rounded-3xl p-5">
                <p className="flex items-center gap-2 font-medium"><Users className="size-4 text-danger" /> People holding a flagged batch</p>
                <div className="mt-3 divide-y divide-line">
                  {matches.map((m, i) => (
                    <motion.div key={i} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm">
                      <div>
                        <p className="font-medium">{m.data.who ?? "Customer"} <span className="font-normal text-muted">· {m.data.where}{m.data.city ? `, ${m.data.city}` : ""}</span></p>
                        <p className="font-mono text-xs text-muted">{m.data.medicine} · batch {m.data.batch}</p>
                      </div>
                      <span className={`rounded-full px-3 py-1 text-xs font-semibold ${m.data.category === "spurious" ? "bg-danger/10 text-danger" : "bg-sand text-brown"}`}>
                        {m.data.category === "spurious" ? "Spurious" : "NSQ"}
                      </span>
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Right column: the phone */}
        <div className="lg:sticky lg:top-24 lg:h-fit">
          <div className="mx-auto w-full max-w-[360px] rounded-[2.75rem] border border-espresso/10 bg-espresso p-3 shadow-[0_40px_80px_-30px_rgba(42,28,21,0.6)]">
            <div className="flex h-[620px] flex-col overflow-hidden rounded-[2.2rem] bg-[#efe7dd]">
              <div className="flex items-center gap-3 bg-[#075e54] px-4 py-3 text-white">
                <span className="grid size-9 place-items-center rounded-full bg-white/20"><MessageCircle className="size-5" /></span>
                <div>
                  <p className="text-sm font-semibold">KinCare Alerts</p>
                  <p className="text-[11px] text-white/70">{form.phone ? form.phone : "patient’s phone"}</p>
                </div>
              </div>

              <div className="flex-1 space-y-3 overflow-y-auto p-3">
                {!whatsapp && !voice && (
                  <p className="mt-40 text-center text-sm text-espresso/40">Waiting for the next alert list…</p>
                )}
                <AnimatePresence>
                  {voice && (
                    <motion.div key="call" initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} className="rounded-2xl bg-espresso p-4 text-paper shadow-lg">
                      <div className="flex items-center gap-3">
                        <motion.span animate={{ scale: [1, 1.15, 1] }} transition={{ repeat: Infinity, duration: 1.2 }} className="grid size-11 place-items-center rounded-full bg-safe">
                          <PhoneCall className="size-5" />
                        </motion.span>
                        <div className="flex-1">
                          <p className="text-sm font-semibold">Incoming call · KinCare</p>
                          <p className="text-[11px] text-paper/60">{voice.data.language === "hi" ? "Hindi voice alert" : "Voice alert"} · {voice.data.status === "sent" ? "placed via Twilio" : "preview"}</p>
                        </div>
                        <button onClick={() => speak(voice.data.message ?? "", voice.data.language ?? "hi")} className="grid size-9 place-items-center rounded-full bg-paper/15" aria-label="Play call">
                          <Play className="size-4" />
                        </button>
                      </div>
                      <p className="mt-3 text-xs leading-relaxed text-paper/80">{voice.data.message}</p>
                    </motion.div>
                  )}
                  {whatsapp && (
                    <motion.div key="wa" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="ml-auto max-w-[88%] whitespace-pre-line rounded-2xl rounded-tr-sm bg-[#dcf8c6] p-3 text-[13px] leading-relaxed text-espresso shadow-sm">
                      {whatsapp.data.message}
                      <p className="mt-1 text-right text-[10px] text-espresso/50">{whatsapp.data.status === "sent" ? "✓✓ delivered via Twilio" : "outbox preview"}</p>
                      {whatsapp.data.checkin && (
                        <a href={whatsapp.data.checkin} target="_blank" rel="noreferrer" className="mt-2 block rounded-xl bg-[#075e54] px-3 py-2 text-center text-xs font-semibold text-white">
                          Open the patient’s check-in →
                        </a>
                      )}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>
          </div>
          <label className="mt-4 flex items-center justify-center gap-2 text-xs text-muted">
            <input type="checkbox" checked={autoSpeak} onChange={(e) => setAutoSpeak(e.target.checked)} className="accent-[#8a4b2c]" />
            <Volume2 className="size-3.5" /> Speak the call aloud on this laptop
          </label>

          <AnimatePresence>
            {done && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mt-4 rounded-3xl bg-brown p-6 text-center text-paper">
                <p className="text-sm text-paper/70">Recall complete</p>
                <p className="mt-1 text-3xl font-medium tracking-tight">{done.data.seconds}s</p>
                <p className="mt-1 text-sm text-paper/80">{done.data.affected} {done.data.affected === 1 ? "person" : "people"} reached · {done.data.notifications} messages</p>
                <p className="mt-3 text-xs text-paper/60">From a government list to a patient’s phone. Today this takes weeks, if it happens at all.</p>
              </motion.div>
            )}
          </AnimatePresence>
          {!form.phone && <p className="mt-3 text-center text-xs text-muted"><Phone className="mr-1 inline size-3" />Add a phone number to put a real person in the recall.</p>}
        </div>
      </div>

      {/* Event log */}
      {events.length > 0 && (
        <details className="card mt-6 rounded-3xl p-5 text-sm">
          <summary className="cursor-pointer font-medium">Event log ({events.length})</summary>
          <div className="mt-3 max-h-72 space-y-1 overflow-y-auto font-mono text-xs">
            {events.map((e, i) => (
              <p key={i}><span className="text-muted">{String(e.data.t ?? "").padStart(5)}s</span> <span className="text-brown">{e.type}</span> {e.data.source ?? e.data.who ?? e.data.month ?? ""} {e.data.step ?? ""}</p>
            ))}
          </div>
        </details>
      )}
    </main>
  );
}

export default function LivePage() {
  return <RoleGate perm="recall.run" role="pharmacist" what="Live recall run"><Live /></RoleGate>;
}
