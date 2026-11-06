"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Activity, Bluetooth, Camera, Database, FastForward, HeartPulse, Loader2, Square, Stethoscope, Wind } from "lucide-react";
import { LiveChart } from "./LiveChart";
import { getReferenceRecord, getReferenceRecords, sendLive, type LiveAck, type LiveSource, type ReferenceRecord, type ReferenceSummary } from "@/lib/api";
import { bluetoothSupported, cameraSupported, startSource, type Reading, type Stop } from "@/lib/live";

const SOURCES: { id: LiveSource; label: string; hint: string; icon: typeof Bluetooth; needs: "bt" | "cam" | null }[] = [
  { id: "ble_hr", label: "Watch / HR strap", hint: "Bluetooth heart-rate (Polar, Garmin, Amazfit, Mi Band in broadcast mode)", icon: Bluetooth, needs: "bt" },
  { id: "ble_oximeter", label: "Pulse oximeter", hint: "Bluetooth fingertip oximeter: SpO₂ + pulse", icon: Wind, needs: "bt" },
  { id: "camera", label: "Phone camera", hint: "Fingertip on the back camera, flash on. Pulse only, ~30 s", icon: Camera, needs: "cam" },
  { id: "replay", label: "Recorded ICU patient", hint: "Real monitor data from 53 ICU patients (PhysioNet BIDMC), replayed second by second", icon: Database, needs: null },
];

export function LiveVitals({ member, sharedWithDoctor }: { member: string; sharedWithDoctor: boolean }) {
  const [source, setSource] = useState<LiveSource | null>(null);
  const [status, setStatus] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [now, setNow] = useState<Reading>({});
  const [pulses, setPulses] = useState<(number | null)[]>([]);
  const [oxy, setOxy] = useState<(number | null)[]>([]);
  const [wave, setWave] = useState<number[]>([]);
  const [ack, setAck] = useState<LiveAck | null>(null);
  const [records, setRecords] = useState<ReferenceSummary[] | null>(null);
  const [validation, setValidation] = useState<{ records: number; mae: number | null; within5: number | null } | null>(null);
  const [picking, setPicking] = useState(false);
  const [rec, setRec] = useState<ReferenceRecord | null>(null);
  const [support, setSupport] = useState({ bt: false, cam: false });
  const stop = useRef<Stop | null>(null);
  const pending = useRef<Reading[]>([]);
  const lastPush = useRef(0);
  const video = useRef<HTMLVideoElement>(null);

  useEffect(() => setSupport({ bt: bluetoothSupported(), cam: cameraSupported() }), []);
  useEffect(() => {
    getReferenceRecords().then((r) => { setRecords(r.records); setValidation(r.validation); }).catch(() => setRecords([]));
  }, []);

  // Batch upload every 2 s; the server judges on a 30 s median, so one bad beat never alarms.
  useEffect(() => {
    if (!source) return;
    const t = setInterval(async () => {
      const batch = pending.current.splice(0);
      if (!batch.length) return;
      try { setAck(await sendLive(member, source, batch)); } catch (e) { setError((e as Error).message); }
    }, 2000);
    return () => clearInterval(t);
  }, [source, member]);

  useEffect(() => () => stop.current?.(), []);

  const onReading = (r: Reading) => {
    const t = Date.now();
    setNow((p) => ({ pulse: r.pulse ?? p.pulse, spo2: r.spo2 ?? p.spo2 }));
    if (t - lastPush.current < 900) return; // devices notify ~1/s; keep one sample per second
    lastPush.current = t;
    pending.current.push(r);
    setPulses((p) => [...p.slice(-119), r.pulse ?? null]);
    setOxy((p) => [...p.slice(-119), r.spo2 ?? null]);
  };

  const start = async (id: LiveSource, recordId?: string) => {
    if (id === "replay" && !recordId) { setPicking(true); return; }
    stop.current?.();
    setError(null); setAck(null); setNow({}); setPulses([]); setOxy([]); setWave([]); setPicking(false);
    setStarting(true);
    try {
      const record = recordId ? await getReferenceRecord(recordId) : undefined;
      setRec(record ?? null);
      stop.current = await startSource(id, {
        onReading,
        onStatus: setStatus,
        onWave: (v) => setWave((w) => [...w.slice(-149), v]),
      }, { video: video.current ?? undefined, record });
      setSource(id);
    } catch (e) {
      const msg = (e as Error).message || "";
      setError(/cancel/i.test(msg) ? "No device chosen." : /permission|denied|NotAllowed/i.test(msg) ? "Permission was blocked. Allow it in the browser and try again." : msg || "Could not start.");
      setSource(null);
    } finally {
      setStarting(false);
    }
  };

  const end = () => {
    stop.current?.();
    stop.current = null;
    setSource(null);
    setStatus("");
  };

  const lvl = ack?.assessment.level;
  const player = stop.current as (Stop & { seek?: (s: number) => void }) | null;

  return (
    <div className="clinical rounded-[2rem] p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="flex items-center gap-2 text-lg font-medium tracking-tight"><Activity className="size-5 text-teal" /> Live vitals for {member}</p>
          <p className="mt-1 text-sm text-muted">Stream pulse and oxygen straight from a device. KinCare checks every 30 seconds and saves a reading to history every 5 minutes.</p>
        </div>
        {source && (
          <span className="inline-flex items-center gap-2 rounded-full bg-danger/10 px-3 py-1 text-xs font-semibold text-danger">
            <span className="size-2 animate-pulse rounded-full bg-danger" /> LIVE{source === "replay" && " · RECORDED"}
          </span>
        )}
      </div>

      <video ref={video} className={source === "camera" ? "mt-4 h-20 w-20 rounded-full object-cover ring-4 ring-danger/30" : "hidden"} />

      {!source && picking && (
        <div className="mt-5">
          <div className="flex items-center justify-between gap-2">
            <p className="text-sm font-medium">Choose a real ICU patient to replay</p>
            <button onClick={() => setPicking(false)} className="text-xs text-muted underline">Back</button>
          </div>
          <p className="mt-1 text-xs text-muted">8-minute bedside monitor recordings from Beth Israel Deaconess Medical Center (MIMIC-II), de-identified. Most eventful first.</p>
          {!records ? <p className="mt-3 text-sm text-muted"><Loader2 className="inline size-4 animate-spin" /> Loading…</p>
            : records.length === 0 ? <p className="mt-3 rounded-2xl bg-sand p-4 text-sm">Recordings are not loaded on this server yet. Run <code>python -m ingest.bidmc</code> in the api folder.</p>
            : (
              <div className="mt-3 grid max-h-80 gap-2 overflow-y-auto sm:grid-cols-2">
                {records.map((r) => (
                  <button key={r.id} onClick={() => start("replay", r.id)} className="rounded-2xl border border-line bg-cream/60 p-3 text-left text-xs transition hover:border-brown/40">
                    <p className="text-sm font-medium">{r.age ?? "?"} {r.gender ?? ""} · {r.location?.toUpperCase() ?? "ICU"} <span className="font-normal text-muted">#{r.id.slice(-2)}</span></p>
                    <p className="mt-0.5 text-muted">Pulse {r.summary.pulse_min}–{r.summary.pulse_max} · SpO₂ low {r.summary.spo2_min}%</p>
                    {(r.summary.seconds_spo2_below_92 > 0 || r.summary.seconds_pulse_above_100 > 0) && (
                      <p className="mt-0.5 font-medium text-danger">
                        {[r.summary.seconds_spo2_below_92 > 0 && `${r.summary.seconds_spo2_below_92}s SpO₂ < 92`, r.summary.seconds_pulse_above_100 > 0 && `${r.summary.seconds_pulse_above_100}s pulse > 100`].filter(Boolean).join(" · ")}
                      </p>
                    )}
                  </button>
                ))}
              </div>
            )}
        </div>
      )}

      {!source && !picking && (
        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          {SOURCES.map((s) => {
            const ok = s.needs === null || support[s.needs];
            return (
              <button key={s.id} disabled={!ok || starting} onClick={() => start(s.id)}
                className="group rounded-2xl border border-line bg-cream/60 p-4 text-left transition hover:border-brown/40 disabled:opacity-50">
                <p className="flex items-center gap-2 font-medium"><s.icon className="size-4 text-brown" /> {s.label}</p>
                {s.id === "camera" && validation?.mae != null && (
                  <p className="mt-1 text-[11px] font-medium text-safe">Tested on {validation.records} real ICU patients: ±{validation.mae} bpm, {Math.round((validation.within5 ?? 0) * 100)}% within 5 bpm</p>
                )}
                <p className="mt-1 text-xs text-muted">{ok ? s.hint : s.needs === "bt" ? "Needs Chrome or Edge on Android, Windows, Mac or ChromeOS (not iPhone)" : "Camera not available here"}</p>
              </button>
            );
          })}
        </div>
      )}
      {starting && <p className="mt-4 flex items-center gap-2 text-sm text-muted"><Loader2 className="size-4 animate-spin" /> Waiting for the device…</p>}
      {error && <p className="mt-3 text-sm text-danger">{error}</p>}

      {source && (
        <>
          <p className="mt-3 text-xs text-muted">{status}</p>
          <div className="mt-4 grid grid-cols-2 gap-3">
            <div className="rounded-2xl bg-cream/70 p-4">
              <p className="flex items-center gap-1.5 text-xs font-medium text-muted">
                <motion.span animate={{ scale: [1, 1.35, 1] }} transition={{ repeat: Infinity, duration: now.pulse ? 60 / now.pulse : 1 }}>
                  <HeartPulse className="size-4 text-danger" />
                </motion.span>
                Pulse
              </p>
              <p className="mt-1 font-mono text-4xl font-semibold tabular-nums">{now.pulse ?? "--"}<span className="ml-1 text-sm font-normal text-muted">bpm</span></p>
              <LiveChart values={pulses} min={40} max={160} flag={100} color="var(--danger)" height={56} />
            </div>
            <div className="rounded-2xl bg-cream/70 p-4">
              <p className="flex items-center gap-1.5 text-xs font-medium text-muted"><Wind className="size-4 text-brown" /> Oxygen (SpO₂)</p>
              <p className="mt-1 font-mono text-4xl font-semibold tabular-nums">{now.spo2 ?? "--"}<span className="ml-1 text-sm font-normal text-muted">%</span></p>
              <LiveChart values={oxy} min={85} max={100} flag={95} height={56} />
            </div>
          </div>
          {wave.length > 10 && (
            <div className="mt-3 rounded-2xl bg-espresso p-3">
              <p className="text-[10px] font-medium uppercase tracking-wider text-paper/60">Pulse wave</p>
              <LiveChart values={wave} color="#6fd6c8" height={60} fill={false} />
            </div>
          )}

          <AnimatePresence>
            {ack && lvl !== "ok" && (
              <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                className={`mt-4 rounded-2xl p-4 text-paper ${lvl === "urgent" ? "bg-danger" : "bg-warn"}`}>
                <p className="font-semibold">{lvl === "urgent" ? "Get help now" : "See a doctor today"} · {ack.assessment.reasons.join(" · ")}</p>
                <p className="mt-1 text-sm">{ack.assessment.en}</p>
                <p className="text-sm text-paper/85">{ack.assessment.hi}</p>
                {sharedWithDoctor && <p className="mt-2 flex items-center gap-1.5 text-sm font-medium"><Stethoscope className="size-4" /> Your doctor is seeing this live.</p>}
                {lvl === "urgent" && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    <a href="tel:108" className="rounded-full bg-paper px-5 py-2 text-sm font-semibold text-danger">Call 108</a>
                    <a href="/sos" className="rounded-full border border-paper/60 px-5 py-2 text-sm font-semibold">Send SOS to family</a>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
          {ack?.saved_to_history && <p className="mt-2 text-xs text-safe">Saved a 30-second median reading to {member}&apos;s history.</p>}

          <div className="mt-4 flex flex-wrap gap-2">
            <button onClick={end} className="inline-flex items-center gap-2 rounded-full bg-espresso px-5 py-2.5 text-sm font-medium text-paper"><Square className="size-3.5" /> Stop</button>
            {source === "replay" && rec && (
              <button onClick={() => player?.seek?.(rec.worst_second)}
                className="inline-flex items-center gap-2 rounded-full border border-line px-5 py-2.5 text-sm font-medium">
                <FastForward className="size-4" /> Jump to this patient&apos;s worst minute
              </button>
            )}
          </div>
        </>
      )}
      {source === "replay" && <p className="mt-3 text-[11px] text-muted">Data: BIDMC PPG and Respiration Dataset, PhysioNet (ODC-By 1.0). Pimentel et al., IEEE TBME 2016.</p>}
      <p className="mt-4 text-[11px] text-muted">Camera pulse is an estimate for wellness use, not a medical device. Thresholds are general adult red flags.</p>
    </div>
  );
}
