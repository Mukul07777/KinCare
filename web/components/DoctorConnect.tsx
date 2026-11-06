"use client";

import { useCallback, useEffect, useState } from "react";
import { Check, Copy, ExternalLink, Link2, Loader2, MessageCircle, PhoneCall, Send, ShieldOff, Stethoscope, Video } from "lucide-react";
import {
  createDoctorLink, formatIST, getCareMessages, getDoctorLinks, markMessagesRead, patientSend, revokeDoctorLink,
  type DoctorLink, type DoctorMessage,
} from "@/lib/api";

const KIND_LABEL: Record<DoctorMessage["kind"], string> = { note: "Note", advice: "Advice · added to reminders", followup: "Follow-up", urgent: "Urgent", call: "Call request" };
const consoleUrl = (token: string) => `${typeof window !== "undefined" ? window.location.origin : ""}/doctor/${token}`;

export function DoctorConnect({ member, onLinks }: { member: string; onLinks?: (n: number) => void }) {
  const [links, setLinks] = useState<DoctorLink[]>([]);
  const [msgs, setMsgs] = useState<DoctorMessage[]>([]);
  const [doctor, setDoctor] = useState("");
  const [hours, setHours] = useState(72);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);
  const [reply, setReply] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [l, m] = await Promise.all([getDoctorLinks(), getCareMessages()]);
      setLinks(l);
      setMsgs(m.messages);
      onLinks?.(l.length);
      if (m.unread) markMessagesRead().catch(() => {});
    } catch { /* api offline */ }
  }, [onLinks]);

  useEffect(() => {
    load();
    const t = setInterval(load, 4000); // doctor's replies appear without a refresh
    return () => clearInterval(t);
  }, [load]);

  const mine = links.filter((l) => l.member === member);
  const active = mine[0];

  const create = async () => {
    setBusy(true); setError(null);
    try {
      await createDoctorLink({ member, doctor: doctor || undefined, hours });
      setDoctor("");
      await load();
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };

  const copy = async (token: string) => {
    try { await navigator.clipboard.writeText(consoleUrl(token)); setCopied(token); setTimeout(() => setCopied(null), 1500); } catch {}
  };

  const send = async (kind: "note" | "call", text: string) => {
    if (!active || !text.trim()) return;
    try { await patientSend({ token: active.token, kind, text }); setReply(""); load(); } catch (e) { setError((e as Error).message); }
  };

  const wa = (l: DoctorLink) =>
    `https://wa.me/?text=${encodeURIComponent(`Doctor, here is ${l.member}'s live KinCare record: vitals, medicines and adherence. Private link, expires ${formatIST(l.expires_at)}:\n${consoleUrl(l.token)}`)}`;

  const thread = msgs.filter((m) => m.member === member).slice().reverse();

  return (
    <div className="grid gap-5 lg:grid-cols-[1fr_1.1fr]">
      <div className="space-y-5">
        <div className="card rounded-[2rem] p-6">
          <p className="flex items-center gap-2 text-lg font-medium tracking-tight"><Stethoscope className="size-5 text-teal" /> Connect {member}&apos;s doctor</p>
          <p className="mt-1 text-sm text-muted">
            Your doctor gets a private link, no app or login. They see live pulse and oxygen, the early-warning score, every medicine and missed dose,
            and can send advice that goes straight into {member}&apos;s daily reminders.
          </p>
          <div className="mt-5 grid gap-3 sm:grid-cols-[1fr_auto]">
            <input value={doctor} onChange={(e) => setDoctor(e.target.value)} placeholder="Doctor's name (e.g. Dr. Mehta)"
              className="rounded-2xl border border-line bg-cream/60 px-4 py-3 text-sm outline-none focus:border-brown/40" />
            <select value={hours} onChange={(e) => setHours(Number(e.target.value))} className="rounded-2xl border border-line bg-cream/60 px-4 py-3 text-sm outline-none">
              <option value={24}>24 hours</option>
              <option value={72}>3 days</option>
              <option value={168}>7 days</option>
              <option value={720}>30 days</option>
            </select>
          </div>
          <button onClick={create} disabled={busy} className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-full bg-brown py-3.5 font-medium text-paper hover:bg-brown-2 disabled:opacity-50">
            {busy ? <Loader2 className="size-5 animate-spin" /> : <><Link2 className="size-4" /> Create private doctor link</>}
          </button>
          {error && <p className="mt-3 text-sm text-danger">{error}</p>}
          <p className="mt-3 text-[11px] text-muted">Links expire on their own and you can switch one off any time. Only {member}&apos;s data is shared.</p>
        </div>

        {mine.map((l) => (
          <div key={l.token} className="card rounded-3xl p-5 text-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="font-medium">{l.doctor ?? "Doctor"} · {l.member}</p>
              <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${l.last_seen ? "bg-safe/15 text-safe" : "bg-sand text-brown"}`}>
                {l.last_seen ? `Opened ${formatIST(l.last_seen)}` : "Not opened yet"}
              </span>
            </div>
            <p className="mt-1 text-xs text-muted">Expires {formatIST(l.expires_at)}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <a href={wa(l)} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 rounded-full bg-[#1f8a4c] px-4 py-2 text-xs font-semibold text-paper"><MessageCircle className="size-3.5" /> Send on WhatsApp</a>
              <button onClick={() => copy(l.token)} className="inline-flex items-center gap-1.5 rounded-full border border-line px-4 py-2 text-xs font-semibold">
                {copied === l.token ? <><Check className="size-3.5" /> Copied</> : <><Copy className="size-3.5" /> Copy link</>}
              </button>
              <a href={`/doctor/${l.token}`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 rounded-full border border-line px-4 py-2 text-xs font-semibold"><ExternalLink className="size-3.5" /> Preview</a>
              <button onClick={async () => { await revokeDoctorLink(l.token); load(); }} className="inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-xs font-semibold text-danger"><ShieldOff className="size-3.5" /> Switch off</button>
            </div>
          </div>
        ))}
      </div>

      <div className="card flex flex-col rounded-[2rem] p-6">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-lg font-medium tracking-tight">Messages with the doctor</p>
          {active?.room && (
            <a href={`https://meet.jit.si/${active.room}`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 rounded-full bg-espresso px-4 py-2 text-xs font-semibold text-paper"><Video className="size-3.5" /> Join video consult</a>
          )}
        </div>
        <div className="mt-4 flex-1 space-y-3 overflow-y-auto" style={{ maxHeight: 420 }}>
          {thread.length === 0 && <p className="rounded-2xl bg-cream/60 p-6 text-center text-sm text-muted">{active ? "No messages yet. The doctor's advice will show here." : "Create a doctor link to start."}</p>}
          {thread.map((m) => (
            <div key={m.id} className={`max-w-[85%] rounded-2xl p-3 text-sm ${m.author === "doctor" ? (m.kind === "urgent" ? "bg-danger text-paper" : "bg-sand") : "ml-auto bg-brown text-paper"}`}>
              <p className="text-[10px] font-semibold uppercase tracking-wider opacity-70">{m.author === "doctor" ? `Doctor · ${KIND_LABEL[m.kind]}` : m.kind === "call" ? "You · call request" : "You"}</p>
              <p className="mt-1 whitespace-pre-wrap">{m.text}</p>
              <p className="mt-1 text-[10px] opacity-60">{formatIST(m.at)}</p>
            </div>
          ))}
        </div>
        {active && (
          <div className="mt-4 space-y-2">
            <div className="flex gap-2">
              <input value={reply} onChange={(e) => setReply(e.target.value)} onKeyDown={(e) => e.key === "Enter" && send("note", reply)} placeholder="Write to the doctor…"
                className="flex-1 rounded-full border border-line bg-cream/60 px-4 py-2.5 text-sm outline-none" />
              <button onClick={() => send("note", reply)} className="rounded-full bg-brown p-3 text-paper"><Send className="size-4" /></button>
            </div>
            <button onClick={() => send("call", `${member} would like a video consult. Please join when you can.`)} className="inline-flex items-center gap-1.5 text-xs font-semibold text-brown">
              <PhoneCall className="size-3.5" /> Request a video consult
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
