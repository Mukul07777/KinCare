"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import {
  Activity, ArrowLeft, Bell, Check, Copy, Eye, HeartPulse, Loader2, Lock, MessageCircleHeart, Pill, Share2, ShieldCheck, Siren, UserPlus, Users, X,
} from "lucide-react";
import { Eyebrow, Heading } from "@/components/Heading";
import { TelegramConnect } from "@/components/TelegramConnect";
import { enableNotifications } from "@/lib/push";
import {
  acceptInvite, authMe, createInvite, formatIST, getAccessLog, getCareLinks, getElder, nudgeElder, previewInvite, revokeLink,
  type AccessEntry, type CareLink, type ElderView, type Scope,
} from "@/lib/api";

const MEMBERS = ["Me", "Maa", "Papa", "Dadi", "Dada", "Nani", "Nana"];
const SCOPES: { key: Scope; label: string; why: string; icon: typeof Pill }[] = [
  { key: "doses", label: "Medicines and doses", why: "Which medicines, and whether each dose was ticked", icon: Pill },
  { key: "vitals", label: "Vitals", why: "BP, pulse, oxygen and temperature readings", icon: HeartPulse },
  { key: "sos", label: "Emergencies", why: "SOS presses and “I can't breathe” in Dadi mode", icon: Siren },
];
const NUDGES = ["Please take your medicine 🙏", "Have you eaten? Take the tablet after food.", "Please check your BP today.", "I'll call you in 10 minutes."];
const pill = "inline-flex items-center gap-2 rounded-full px-5 py-3 text-base font-medium transition disabled:opacity-50";
const ago = (iso: string) => {
  const s = (Date.now() - new Date(iso.endsWith("Z") || iso.includes("+") ? iso : iso + "Z").getTime()) / 1000;
  return s < 90 ? "just now" : s < 3600 ? `${Math.round(s / 60)} min ago` : s < 86400 ? `${Math.round(s / 3600)} h ago` : `${Math.round(s / 86400)} d ago`;
};

// ---------- the elder's side: share, see who looks, stop ----------
function ShareSide() {
  const [member, setMember] = useState("Me");
  const [name, setName] = useState("");
  const [scopes, setScopes] = useState<Scope[]>(["doses", "vitals", "sos"]);
  const [agree, setAgree] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [invite, setInvite] = useState<{ code: string; url: string; expires_at: string } | null>(null);
  const [links, setLinks] = useState<CareLink[] | null>(null);
  const [log, setLog] = useState<AccessEntry[]>([]);
  const [copied, setCopied] = useState(false);

  const load = useCallback(() => {
    getCareLinks().then((l) => setLinks(l.caregivers)).catch(() => setLinks([]));
    getAccessLog().then(setLog).catch(() => {});
  }, []);
  useEffect(() => { load(); const id = setInterval(load, 15000); return () => clearInterval(id); }, [load]);

  const make = async () => {
    setBusy(true); setErr("");
    try { setInvite(await createInvite({ member, elder_name: name || undefined, scopes })); }
    catch (e) { setErr((e as Error).message); }
    finally { setBusy(false); }
  };
  const msg = invite && `${name || "I"} would like you to look after ${member === "Me" ? "my" : `${member}'s`} medicines on KinCare.\nOpen: ${invite.url}\nOr enter code ${invite.code} in KinCare > Family. Valid 48 hours.`;
  const share = async () => {
    if (!msg) return;
    try { if (navigator.share) { await navigator.share({ text: msg }); return; } } catch { return; }
    window.open(`https://wa.me/?text=${encodeURIComponent(msg)}`, "_blank", "noopener");
  };
  const copy = async () => { if (invite) { await navigator.clipboard.writeText(invite.code).catch(() => {}); setCopied(true); setTimeout(() => setCopied(false), 1500); } };
  const stop = async (l: CareLink) => {
    if (!confirm(`Stop sharing with ${l.caregiver_name}? They lose access immediately.`)) return;
    await revokeLink(l.id).catch(() => {});
    load();
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[1.1fr_1fr]">
      <section className="rounded-[2rem] border border-line bg-paper p-6">
        <h2 className="flex items-center gap-2 text-xl font-semibold"><UserPlus className="size-5 text-teal" /> Invite a caregiver</h2>
        <p className="mt-1 text-muted">Your son, daughter or a nurse sees only what you tick below. You can stop it anytime.</p>

        <AnimatePresence mode="wait">
          {!invite ? (
            <motion.div key="form" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <p className="mt-5 text-sm font-medium text-brown">Whose health is shared?</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {MEMBERS.map((m) => (
                  <button key={m} onClick={() => setMember(m)} aria-pressed={member === m}
                    className={`rounded-full px-4 py-2 text-base ${member === m ? "bg-espresso text-paper" : "border border-line bg-cream"}`}>{m}</button>
                ))}
              </div>
              <label className="mt-4 block text-sm font-medium text-brown">Their name, as family calls them
                <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Ramesh ji" maxLength={40}
                  className="mt-1.5 w-full rounded-2xl border border-line bg-cream px-4 py-3 text-lg outline-none focus:border-teal/40" />
              </label>

              <p className="mt-5 text-sm font-medium text-brown">What can the caregiver see?</p>
              <div className="mt-2 space-y-2">
                {SCOPES.map((s) => {
                  const on = scopes.includes(s.key);
                  return (
                    <button key={s.key} onClick={() => setScopes(on ? scopes.filter((x) => x !== s.key) : [...scopes, s.key])} aria-pressed={on}
                      className={`flex w-full items-center gap-3 rounded-2xl border p-4 text-left transition ${on ? "border-teal/40 bg-mint" : "border-line bg-cream"}`}>
                      <span className={`grid size-7 shrink-0 place-items-center rounded-lg border ${on ? "border-teal bg-teal text-paper" : "border-clay bg-paper"}`}>{on && <Check className="size-4" />}</span>
                      <s.icon className="size-5 shrink-0 text-brown" />
                      <span><span className="block font-semibold">{s.label}</span><span className="block text-sm text-muted">{s.why}</span></span>
                    </button>
                  );
                })}
              </div>

              <label className="mt-5 flex items-start gap-3 rounded-2xl bg-cream p-4 text-sm">
                <input type="checkbox" checked={agree} onChange={(e) => setAgree(e.target.checked)} className="mt-0.5 size-5 accent-[var(--teal)]" />
                <span>
                  {member === "Me" ? "I agree" : `${member} agrees`} to share the items ticked above with one caregiver. Every time they look, it is logged here.
                  Sharing can be stopped anytime, and the caregiver can never change medicines or readings.
                </span>
              </label>
              {err && <p className="mt-3 text-sm text-danger">{err}</p>}
              <button onClick={make} disabled={busy || !agree || !scopes.length} className={`${pill} mt-5 bg-teal text-paper hover:bg-teal-2`}>
                {busy ? <Loader2 className="size-5 animate-spin" /> : <ShieldCheck className="size-5" />} Create invite code
              </button>
            </motion.div>
          ) : (
            <motion.div key="code" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="mt-5">
              <p className="text-sm text-muted">Give this code to the caregiver. It works once, for 48 hours.</p>
              <button onClick={copy} className="mt-3 flex w-full items-center justify-center gap-3 rounded-3xl bg-espresso py-6 font-mono text-5xl font-semibold tracking-[0.3em] text-paper">
                {invite.code} {copied ? <Check className="size-6" /> : <Copy className="size-6 opacity-60" />}
              </button>
              <div className="mt-4 flex flex-wrap gap-2">
                <button onClick={share} className={`${pill} bg-teal text-paper hover:bg-teal-2`}><Share2 className="size-5" /> Send to family</button>
                <button onClick={() => { setInvite(null); setAgree(false); }} className={`${pill} border border-line bg-cream`}>Done</button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </section>

      <div className="space-y-6">
        <section className="rounded-[2rem] border border-line bg-paper p-6">
          <h2 className="flex items-center gap-2 text-xl font-semibold"><Users className="size-5 text-teal" /> Who looks after you</h2>
          {links === null ? <div className="mt-4 h-20 animate-pulse rounded-2xl bg-sand/60" /> : links.length === 0 ? (
            <p className="mt-3 text-muted">Nobody yet. Nothing is shared until you create a code.</p>
          ) : (
            <ul className="mt-4 space-y-3">
              {links.map((l) => (
                <li key={l.id} className="rounded-2xl bg-cream p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold">{l.caregiver_name}{l.relation ? <span className="font-normal text-muted"> · {l.relation}</span> : null}</p>
                      <p className="text-sm text-muted">For {l.elder_name || l.member} · {l.last_seen ? `last looked ${ago(l.last_seen)}` : "hasn't looked yet"}</p>
                      <div className="mt-2 flex flex-wrap gap-1.5">{l.scopes.map((s) => <span key={s} className="rounded-full bg-paper px-2.5 py-0.5 text-xs font-medium text-brown">{SCOPES.find((x) => x.key === s)?.label}</span>)}</div>
                    </div>
                    <button onClick={() => stop(l)} className="shrink-0 rounded-full border border-danger/30 px-3 py-1.5 text-sm font-medium text-danger hover:bg-danger hover:text-paper">Stop sharing</button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
        {log.length > 0 && (
          <section className="rounded-[2rem] border border-line bg-paper p-6">
            <h2 className="flex items-center gap-2 text-lg font-semibold"><Eye className="size-5 text-teal" /> Access log</h2>
            <p className="text-sm text-muted">Every look, reminder and alert, so you always know.</p>
            <ul className="mt-3 max-h-72 space-y-2 overflow-y-auto text-sm">
              {log.map((e, i) => (
                <li key={i} className="flex justify-between gap-3 border-b border-line pb-2 last:border-0">
                  <span><b>{e.caregiver_name}</b> {{ viewed: "looked at", nudged: "sent a reminder:", linked: "joined.", revoked: "link ended,", alerted: "was alerted:" }[e.action]} <span className="text-muted">{e.detail}</span></span>
                  <span className="shrink-0 text-muted">{ago(e.at)}</span>
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </div>
  );
}

// ---------- the caregiver's side ----------
function JoinCard({ initial, onJoined }: { initial: string; onJoined: (id: number) => void }) {
  const [code, setCode] = useState(initial);
  const [prev, setPrev] = useState<Awaited<ReturnType<typeof previewInvite>> | null>(null);
  const [name, setName] = useState("");
  const [relation, setRelation] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const look = useCallback(async (c: string) => {
    setBusy(true); setErr("");
    try { setPrev(await previewInvite(c)); } catch (e) { setErr((e as Error).message); setPrev(null); } finally { setBusy(false); }
  }, []);
  useEffect(() => { if (initial) look(initial); }, [initial, look]);
  useEffect(() => { try { setName(localStorage.getItem("kincare.cg.name") || ""); } catch {} }, []);

  const accept = async () => {
    setBusy(true); setErr("");
    try {
      try { localStorage.setItem("kincare.cg.name", name); } catch {}
      const r = await acceptInvite({ code, name, relation: relation || undefined });
      enableNotifications().catch(() => {});
      onJoined(r.link_id);
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  };

  return (
    <section className="rounded-[2rem] border border-line bg-paper p-6">
      <h2 className="flex items-center gap-2 text-xl font-semibold"><Lock className="size-5 text-teal" /> Enter the code they gave you</h2>
      {!prev ? (
        <form onSubmit={(e) => { e.preventDefault(); look(code); }} className="mt-4 flex gap-2">
          <input value={code} onChange={(e) => setCode(e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 6))} placeholder="ABC234" aria-label="Invite code"
            className="w-48 rounded-2xl border border-line bg-cream px-4 py-3 text-center font-mono text-2xl tracking-[0.25em] outline-none focus:border-teal/40" />
          <button disabled={busy || code.length !== 6} className={`${pill} bg-espresso text-paper`}>{busy ? <Loader2 className="size-5 animate-spin" /> : "Continue"}</button>
        </form>
      ) : (
        <div className="mt-4">
          <p className="text-lg"><b>{prev.elder_name}</b> agreed to share with you:</p>
          <ul className="mt-3 space-y-2">
            {prev.scopes.map((s) => <li key={s.key} className="flex items-center gap-2 rounded-2xl bg-mint px-4 py-3"><Check className="size-5 text-teal" /> {s.label}</li>)}
          </ul>
          <p className="mt-3 text-sm text-muted">You can see and send reminders. You can&apos;t change their medicines or readings. They can see each time you look, and can stop this anytime.</p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" maxLength={40} aria-label="Your name" className="rounded-2xl border border-line bg-cream px-4 py-3 text-lg outline-none focus:border-teal/40" />
            <input value={relation} onChange={(e) => setRelation(e.target.value)} placeholder="Relation (son, daughter…)" maxLength={20} aria-label="Relation" className="rounded-2xl border border-line bg-cream px-4 py-3 text-lg outline-none focus:border-teal/40" />
          </div>
          <div className="mt-4 flex gap-2">
            <button onClick={accept} disabled={busy || !name.trim()} className={`${pill} bg-teal text-paper hover:bg-teal-2`}>{busy ? <Loader2 className="size-5 animate-spin" /> : <ShieldCheck className="size-5" />} Accept and start caring</button>
            <button onClick={() => { setPrev(null); setCode(""); }} className={`${pill} border border-line bg-cream`}>Cancel</button>
          </div>
        </div>
      )}
      {err && <p className="mt-3 text-sm text-danger">{err}</p>}
    </section>
  );
}

const LEVEL = { ok: "bg-safe/10 text-safe", doctor: "bg-warn-soft text-warn", urgent: "bg-danger text-paper" } as Record<string, string>;

function Spark({ values, lo, hi }: { values: number[]; lo: number; hi: number }) {
  if (values.length < 2) return null;
  const max = Math.max(hi, ...values), min = Math.min(lo, ...values);
  const pts = values.map((v, i) => `${(i / (values.length - 1)) * 100},${36 - ((v - min) / (max - min || 1)) * 32}`).join(" ");
  const y = (v: number) => 36 - ((v - min) / (max - min || 1)) * 32;
  return (
    <svg viewBox="0 0 100 40" className="mt-2 h-10 w-full" preserveAspectRatio="none" aria-hidden>
      <rect x="0" y={y(hi)} width="100" height={Math.max(y(lo) - y(hi), 0)} fill="var(--mint)" />
      <polyline points={pts} fill="none" stroke="var(--teal)" strokeWidth="2" vectorEffect="non-scaling-stroke" strokeLinejoin="round" />
    </svg>
  );
}

function ElderDashboard({ id, onBack }: { id: number; onBack: () => void }) {
  const [v, setV] = useState<ElderView | null>(null);
  const [err, setErr] = useState("");
  const [sent, setSent] = useState("");
  const [custom, setCustom] = useState("");
  const load = useCallback(() => getElder(id).then(setV).catch((e) => setErr((e as Error).message)), [id]);
  useEffect(() => { load(); const t = setInterval(load, 30000); return () => clearInterval(t); }, [load]);

  const nudge = async (text: string) => {
    setSent("");
    try { const r = await nudgeElder(id, text); setSent(r.phone || r.telegram ? "Sent to their phone." : "Sent. They'll see it in Dadi mode."); setCustom(""); }
    catch (e) { setSent((e as Error).message); }
  };

  if (err) return <div className="rounded-[2rem] border border-line bg-paper p-6"><p className="text-danger">{err}</p><button onClick={onBack} className="mt-3 text-teal">← Back</button></div>;
  if (!v) return <div className="h-96 animate-pulse rounded-[2rem] bg-sand/60" />;
  const who = v.link.elder_name || v.link.member;
  const lv = v.vitals?.latest;
  const missedToday = v.doses?.today.filter((d) => d.state === "missed") ?? [];
  const bp = (v.vitals?.history ?? []).filter((x) => x.bp_sys).map((x) => x.bp_sys as number).reverse();

  return (
    <div>
      <button onClick={onBack} className="inline-flex items-center gap-1 text-sm font-medium text-teal"><ArrowLeft className="size-4" /> Everyone you look after</button>
      <div className="mt-3 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-4xl font-semibold tracking-tight">{who}</h2>
          <p className="mt-1 text-muted">Shared with you: {v.link.scopes.map((s) => SCOPES.find((x) => x.key === s)?.label).join(", ")}</p>
        </div>
        {missedToday.length > 0 ? (
          <span className="inline-flex items-center gap-2 rounded-full bg-danger px-4 py-2 font-medium text-paper"><Bell className="size-4" /> {missedToday.length} dose{missedToday.length > 1 ? "s" : ""} missed today</span>
        ) : v.doses ? <span className="inline-flex items-center gap-2 rounded-full bg-safe px-4 py-2 font-medium text-paper"><Check className="size-4" /> On track today</span> : null}
      </div>

      <div className="mt-6 grid gap-5 lg:grid-cols-3">
        {/* doses */}
        {v.doses && (
          <section className="rounded-[2rem] border border-line bg-paper p-6 lg:col-span-2">
            <div className="flex items-start justify-between gap-4">
              <h3 className="flex items-center gap-2 text-lg font-semibold"><Pill className="size-5 text-teal" /> Today</h3>
              {v.doses.adherence !== null && (
                <div className="text-right"><p className="text-3xl font-semibold">{v.doses.adherence}%</p><p className="text-xs text-muted">doses taken, last 7 days</p></div>
              )}
            </div>
            {v.doses.today.length === 0 ? <p className="mt-3 text-muted">No doses scheduled today.</p> : (
              <ul className="mt-4 space-y-2">
                {v.doses.today.map((d) => (
                  <li key={`${d.med_id}-${d.slot}`} className={`flex items-center justify-between gap-3 rounded-2xl px-4 py-3 ${d.state === "taken" ? "bg-safe/10" : d.state === "missed" ? "bg-danger/10" : "bg-cream"}`}>
                    <span><b>{d.name}</b> <span className="text-muted">{d.strength}</span><span className="block text-sm text-muted">{d.time} · {d.slot}{d.food ? ` · ${d.food}` : ""}</span></span>
                    <span className={`shrink-0 rounded-full px-3 py-1 text-sm font-medium ${d.state === "taken" ? "bg-safe text-paper" : d.state === "missed" ? "bg-danger text-paper" : "bg-paper text-muted"}`}>
                      {d.state === "taken" ? `Taken ${d.taken_at ? formatIST(d.taken_at).split(",").pop()?.trim() : ""}` : d.state === "missed" ? "Not taken" : "Later"}
                    </span>
                  </li>
                ))}
              </ul>
            )}
            <div className="mt-6">
              <p className="text-sm font-medium text-brown">Last 7 days</p>
              <div className="mt-2 grid grid-cols-7 gap-2">
                {v.doses.week.map((w) => {
                  const pct = w.due ? w.taken / w.due : null;
                  return (
                    <div key={w.day} title={w.missed.length ? `Missed: ${w.missed.join(", ")}` : undefined} className="text-center">
                      <div className="relative mx-auto h-20 w-full overflow-hidden rounded-xl bg-cream">
                        {pct !== null && <div className={`absolute inset-x-0 bottom-0 ${pct === 1 ? "bg-safe" : pct >= 0.5 ? "bg-warn" : "bg-danger"}`} style={{ height: `${Math.max(pct * 100, 6)}%` }} />}
                      </div>
                      <p className="mt-1 text-xs text-muted">{new Date(w.day).toLocaleDateString("en-IN", { weekday: "short" })}</p>
                      <p className="text-xs font-medium">{w.due ? `${w.taken}/${w.due}` : "–"}</p>
                    </div>
                  );
                })}
              </div>
            </div>
          </section>
        )}

        {/* nudge */}
        <section className="rounded-[2rem] border border-line bg-paper p-6">
          <h3 className="flex items-center gap-2 text-lg font-semibold"><MessageCircleHeart className="size-5 text-teal" /> Send a reminder</h3>
          <p className="mt-1 text-sm text-muted">Shows up on their phone and is read out in Dadi mode.</p>
          <div className="mt-3 space-y-2">
            {NUDGES.map((n) => <button key={n} onClick={() => nudge(n)} className="block w-full rounded-2xl bg-cream px-4 py-3 text-left hover:bg-mint">{n}</button>)}
          </div>
          <form onSubmit={(e) => { e.preventDefault(); if (custom.trim()) nudge(custom); }} className="mt-3 flex gap-2">
            <input value={custom} onChange={(e) => setCustom(e.target.value)} placeholder="Your own words…" maxLength={200} aria-label="Reminder text" className="min-w-0 flex-1 rounded-full border border-line bg-cream px-4 py-2.5 outline-none" />
            <button disabled={!custom.trim()} className="rounded-full bg-espresso px-4 text-paper disabled:opacity-40">Send</button>
          </form>
          {sent && <p className="mt-2 text-sm text-teal">{sent}</p>}
        </section>

        {/* vitals */}
        {v.vitals && (
          <section className="rounded-[2rem] border border-line bg-paper p-6 lg:col-span-2">
            <h3 className="flex items-center gap-2 text-lg font-semibold"><Activity className="size-5 text-teal" /> Vitals</h3>
            {!lv ? <p className="mt-3 text-muted">No readings yet. In Dadi mode they can just say “BP 130/80”.</p> : (
              <>
                <p className="mt-1 text-sm text-muted">Latest {ago(lv.at)} · {lv.source === "voice" ? "said in Dadi mode" : lv.source}</p>
                <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
                  {[["BP", lv.bp_sys ? `${lv.bp_sys}/${lv.bp_dia ?? "?"}` : null], ["Pulse", lv.pulse], ["Oxygen", lv.spo2 ? `${lv.spo2}%` : null], ["Temp", lv.temp_c ? `${lv.temp_c}°C` : null]].map(([k, val]) => (
                    <div key={k as string} className="rounded-2xl bg-cream p-4"><p className="text-xs text-muted">{k}</p><p className="text-2xl font-semibold">{val ?? "–"}</p></div>
                  ))}
                </div>
                <span className={`mt-3 inline-block rounded-full px-3 py-1 text-sm font-medium ${LEVEL[lv.level] ?? "bg-cream"}`}>
                  {lv.level === "urgent" ? "Needs urgent help" : lv.level === "doctor" ? "See a doctor today" : "Within the usual range"}
                </span>
                {bp.length > 1 && (<div className="mt-4"><p className="text-xs text-muted">Systolic BP, last {bp.length} readings (shaded: 90–140)</p><Spark values={bp} lo={90} hi={140} /></div>)}
              </>
            )}
          </section>
        )}

        {/* alerts for this caregiver */}
        <section className="rounded-[2rem] border border-line bg-paper p-6">
          <h3 className="flex items-center gap-2 text-lg font-semibold"><Bell className="size-5 text-teal" /> Your alerts</h3>
          <p className="mt-1 text-sm text-muted">Missed doses (1 hour late), worrying readings{v.sos ? " and SOS" : ""} reach you here and on your phone.</p>
          {v.sos?.last && (
            <p className={`mt-3 rounded-2xl p-3 text-sm ${v.sos.last.resolved_at ? "bg-cream" : "bg-danger text-paper"}`}>
              Last SOS {ago(v.sos.last.at)}{v.sos.last.lat ? <> · <a className="underline" href={`https://maps.google.com/?q=${v.sos.last.lat},${v.sos.last.lng}`} target="_blank" rel="noreferrer">location</a></> : null}
            </p>
          )}
          <div className="mt-3 space-y-2">
            <button onClick={() => enableNotifications().catch(() => {})} className={`${pill} w-full justify-center border border-line bg-cream py-2.5 text-sm`}><Bell className="size-4" /> Turn on phone alerts</button>
            <TelegramConnect role="caregiver" compact />
          </div>
        </section>

        {v.doses && v.doses.medicines.length > 0 && (
          <section className="rounded-[2rem] border border-line bg-paper p-6 lg:col-span-3">
            <h3 className="text-lg font-semibold">Their medicines</h3>
            <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {v.doses.medicines.map((m, i) => (
                <div key={i} className="rounded-2xl bg-cream p-4">
                  <p className="font-semibold">{m.name} <span className="font-normal text-muted">{m.strength}</span></p>
                  <p className="text-sm text-muted">{m.as_needed ? "When needed" : m.schedule} {m.food && `· ${m.food}`}{m.doctor ? ` · ${m.doctor}` : ""}</p>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}

function CareSide({ code, link, setLink }: { code: string; link: number | null; setLink: (id: number | null) => void }) {
  const [watching, setWatching] = useState<CareLink[] | null>(null);
  const [joining, setJoining] = useState(!!code);
  const load = useCallback(() => getCareLinks().then((l) => setWatching(l.watching)).catch(() => setWatching([])), []);
  useEffect(() => { load(); }, [load, link]);

  if (link) return <ElderDashboard id={link} onBack={() => { setLink(null); load(); }} />;
  return (
    <div className="space-y-6">
      {watching === null ? <div className="h-32 animate-pulse rounded-[2rem] bg-sand/60" /> : watching.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {watching.map((l) => (
            <div key={l.id} className="rounded-[2rem] border border-line bg-paper p-6 text-left transition hover:border-teal/40 hover:shadow-sm">
              <button onClick={() => setLink(l.id)} className="block w-full text-left">
                <p className="text-2xl font-semibold">{l.elder_name || l.member}</p>
                <p className="mt-1 text-sm text-muted">Since {new Date(l.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}</p>
                <div className="mt-3 flex flex-wrap gap-1.5">{l.scopes.map((s) => <span key={s} className="rounded-full bg-mint px-2.5 py-0.5 text-xs font-medium text-teal">{SCOPES.find((x) => x.key === s)?.label}</span>)}</div>
                <p className="mt-4 inline-flex items-center gap-1 font-medium text-teal">Open →</p>
              </button>
              <button onClick={async () => { if (confirm("Stop looking after them? You'll need a new code to come back.")) { await revokeLink(l.id).catch(() => {}); load(); } }}
                className="mt-2 inline-flex items-center gap-1 text-xs text-muted hover:text-danger"><X className="size-3" /> Leave</button>
            </div>
          ))}
        </div>
      )}
      {joining || watching?.length === 0 ? (
        <JoinCard initial={code} onJoined={(id) => { setJoining(false); setLink(id); }} />
      ) : (
        <button onClick={() => setJoining(true)} className={`${pill} border border-line bg-paper`}><UserPlus className="size-5" /> Add someone with a code</button>
      )}
    </div>
  );
}

// Sharing medical data needs a verified phone on both sides; say so up front instead of failing on the button.
function SignInFirst() {
  const [me, setMe] = useState<string | null | undefined>(undefined);
  useEffect(() => { authMe().then((m) => setMe(m.masked)).catch(() => setMe(null)); }, []);
  if (me !== null) return null;
  const next = typeof window === "undefined" ? "/family" : window.location.pathname + window.location.search;
  return (
    <div className="mt-8 flex flex-wrap items-center justify-between gap-3 rounded-[1.5rem] border border-warn/30 bg-warn-soft p-5">
      <p className="flex items-center gap-2 text-sm text-espresso"><Lock className="size-4 text-warn" /> Sharing health data needs a verified phone number, for you and for the person you share with.</p>
      <Link href={`/login?next=${encodeURIComponent(next)}`} className="rounded-full bg-espresso px-5 py-2.5 text-sm font-medium text-paper hover:bg-brown">Sign in with your phone</Link>
    </div>
  );
}

function Family() {
  const params = useSearchParams();
  const router = useRouter();
  const code = (params.get("code") || "").toUpperCase();
  const linkParam = Number(params.get("link")) || null;
  const [tab, setTab] = useState<"care" | "share">(code || linkParam ? "care" : "share");
  const [link, setLinkState] = useState<number | null>(linkParam);
  useEffect(() => { if (!code && !linkParam) getCareLinks().then((l) => { if (l.watching.length && !l.caregivers.length) setTab("care"); }).catch(() => {}); }, [code, linkParam]);
  const setLink = (id: number | null) => { setLinkState(id); router.replace(id ? `/family?link=${id}` : "/family", { scroll: false }); };

  return (
    <main className="blush mx-auto max-w-6xl px-4 pb-24 pt-12 sm:px-6 sm:pt-16">
      <Eyebrow>Family care, with consent</Eyebrow>
      <Heading as="h1" lead="Look after them" tail="from anywhere." className="mt-4 text-4xl sm:text-6xl" />
      <p className="mt-4 max-w-2xl text-lg text-muted">
        See whether Papa took his BP tablet, what his last reading was, and get a message if a dose is an hour late. Only what he agrees to share, and he can see every time you look.
      </p>

      <div className="mt-8 inline-flex rounded-full border border-line bg-paper p-1">
        {([["care", "I look after someone"], ["share", "Someone looks after me"]] as const).map(([k, label]) => (
          <button key={k} onClick={() => setTab(k)} aria-pressed={tab === k}
            className={`rounded-full px-5 py-2.5 text-sm font-medium transition sm:text-base ${tab === k ? "bg-espresso text-paper" : "text-muted"}`}>{label}</button>
        ))}
      </div>

      <SignInFirst />

      <div className="mt-8">{tab === "care" ? <CareSide code={code} link={link} setLink={setLink} /> : <ShareSide />}</div>
    </main>
  );
}

export default function FamilyPage() {
  return <Suspense><Family /></Suspense>;
}
