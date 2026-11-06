"use client";

import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Ambulance, HeartPulse, Hospital, Loader2, MapPin, Phone, Pill, Plus, Send, Trash2, UserRound } from "lucide-react";
import { Eyebrow, Heading } from "@/components/Heading";
import { addContact, formatIST, getContacts, getSosCard, removeContact, triggerSos, type Contact, type SosCard } from "@/lib/api";

const MEMBERS = ["Me", "Maa", "Papa", "Dadi", "Dada", "Child"];

function locate(): Promise<GeolocationPosition | null> {
  return new Promise((res) => {
    if (!navigator.geolocation) return res(null);
    navigator.geolocation.getCurrentPosition(res, () => res(null), { enableHighAccuracy: true, timeout: 8000 });
  });
}

export default function SosPage() {
  const [member, setMember] = useState("Me");
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [card, setCard] = useState<SosCard | null>(null);
  const [pos, setPos] = useState<{ lat: number; lng: number } | null>(null);
  const [form, setForm] = useState({ name: "", phone: "", relation: "" });
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState<Awaited<ReturnType<typeof triggerSos>> | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    getContacts().then(setContacts).catch(() => {});
    getSosCard(member).then(setCard).catch(() => {});
  }, [member]);
  useEffect(() => { load(); setSent(null); }, [load]);

  const sos = async () => {
    setBusy(true);
    setError(null);
    try {
      const p = await locate();
      const here = p ? { lat: p.coords.latitude, lng: p.coords.longitude } : null;
      setPos(here);
      setSent(await triggerSos({ member, ...(here ?? {}) }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const add = async () => {
    setError(null);
    try {
      await addContact({ name: form.name, phone: form.phone, relation: form.relation || undefined });
      setForm({ name: "", phone: "", relation: "" });
      load();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const hospitals = pos ? `https://www.google.com/maps/search/hospital/@${pos.lat},${pos.lng},14z` : "https://www.google.com/maps/search/hospital+near+me";
  const v = card?.last_vitals;
  const input = "w-full rounded-xl border border-line bg-cream/60 px-3 py-2 text-sm outline-none focus:border-brown/40";

  return (
    <main className="mx-auto max-w-6xl px-4 pt-12 sm:px-6 sm:pt-16">
      <div className="grid items-end gap-6 md:grid-cols-2">
        <div>
          <Eyebrow>Emergency</Eyebrow>
          <Heading as="h1" lead="One tap," tail="and help is on the way." className="mt-4 text-4xl sm:text-6xl" />
        </div>
        <p className="max-w-sm text-muted md:ml-auto">
          Call an ambulance, send your family your live location, and show the doctor your medicines and latest vitals.
        </p>
      </div>

      <div className="mt-10 grid gap-4 sm:grid-cols-3">
        <a href="tel:112" className="flex items-center gap-4 rounded-3xl bg-danger p-6 text-paper shadow-[0_20px_50px_-20px_rgba(190,40,40,0.7)] transition hover:brightness-110">
          <Phone className="size-8" /><div><p className="text-3xl font-semibold">112</p><p className="text-sm text-paper/80">National emergency</p></div>
        </a>
        <a href="tel:108" className="flex items-center gap-4 rounded-3xl bg-danger/90 p-6 text-paper transition hover:brightness-110">
          <Ambulance className="size-8" /><div><p className="text-3xl font-semibold">108</p><p className="text-sm text-paper/80">Ambulance</p></div>
        </a>
        <a href={hospitals} target="_blank" rel="noreferrer" className="card flex items-center gap-4 rounded-3xl p-6 transition hover:border-brown">
          <Hospital className="size-8 text-brown" /><div><p className="text-lg font-semibold">Nearest hospitals</p><p className="text-sm text-muted">Opens maps{pos ? " at your location" : ""}</p></div>
        </a>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[1.2fr_1fr]">
        <div className="card rounded-[2rem] p-6">
          <div className="flex flex-wrap gap-2">
            {MEMBERS.map((m) => (
              <button key={m} onClick={() => setMember(m)} className={`rounded-full px-4 py-1.5 text-sm ${member === m ? "bg-brown text-paper" : "border border-line"}`}>{m}</button>
            ))}
          </div>
          <motion.button whileTap={{ scale: 0.97 }} onClick={sos} disabled={busy}
            className="relative mt-6 grid w-full place-items-center overflow-hidden rounded-[2rem] bg-danger py-10 text-paper disabled:opacity-70">
            <span className="absolute size-40 animate-ping rounded-full bg-paper/10" />
            {busy ? <Loader2 className="size-10 animate-spin" /> : <Send className="size-10" />}
            <span className="mt-3 text-2xl font-semibold">Send SOS for {member}</span>
            <span className="text-sm text-paper/80">Location + medicines + vitals to {contacts.length} contact{contacts.length === 1 ? "" : "s"}</span>
          </motion.button>
          {error && <p className="mt-3 text-sm text-danger">{error}</p>}

          {sent && (
            <div className="mt-5 space-y-3">
              {sent.deliveries.length === 0 && <p className="text-sm text-danger">No emergency contacts yet. Add one on the right, then send again.</p>}
              {sent.deliveries.map((d) => (
                <div key={`${d.name}-${d.phone}`} className="flex items-center justify-between rounded-2xl bg-sand px-4 py-3 text-sm">
                  <span><b>{d.name}</b> · {d.phone}</span>
                  {d.status === "caregiver" ? <span className="font-medium text-safe">Alerted in KinCare</span> : d.status === "sent" ? <span className="font-medium text-safe">WhatsApp sent</span> : (
                    <a href={d.link ?? undefined} target="_blank" rel="noreferrer" className="rounded-full bg-[#25D366] px-4 py-1.5 font-medium text-white">Tap to send on WhatsApp</a>
                  )}
                </div>
              ))}
              <pre className="whitespace-pre-wrap rounded-2xl border border-line bg-paper p-4 text-xs text-muted">{sent.message}</pre>
            </div>
          )}
        </div>

        <div className="space-y-6">
          <div className="card rounded-[2rem] p-6">
            <p className="flex items-center gap-2 font-medium"><UserRound className="size-4 text-brown" /> Emergency contacts</p>
            <div className="mt-3 divide-y divide-line">
              {contacts.map((c) => (
                <div key={c.id} className="flex items-center justify-between py-2 text-sm">
                  <span>{c.name}{c.relation ? ` (${c.relation})` : ""} · <span className="font-mono text-xs">{c.phone}</span></span>
                  <button onClick={() => removeContact(c.id).then(load)} aria-label="Remove"><Trash2 className="size-4 text-muted hover:text-danger" /></button>
                </div>
              ))}
            </div>
            <div className="mt-3 grid grid-cols-2 gap-2">
              <input className={input} placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              <input className={input} placeholder="Relation" value={form.relation} onChange={(e) => setForm({ ...form, relation: e.target.value })} />
              <input className={`${input} col-span-2`} placeholder="Phone, e.g. 98xxxxxxxx" inputMode="tel" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
            </div>
            <button onClick={add} disabled={!form.name || !form.phone} className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-espresso px-4 py-2 text-sm font-medium text-paper disabled:opacity-40"><Plus className="size-4" /> Add contact</button>
          </div>

          <div className="card rounded-[2rem] p-6 text-sm">
            <p className="flex items-center gap-2 font-medium"><HeartPulse className="size-4 text-brown" /> For the doctor: {member}</p>
            {v ? (
              <p className="mt-2 font-mono text-xs">
                {[v.temp_c && `${v.temp_c}°C`, v.bp_sys && `BP ${v.bp_sys}/${v.bp_dia ?? "?"}`, v.pulse && `pulse ${v.pulse}`, v.spo2 && `SpO₂ ${v.spo2}%`].filter(Boolean).join(" · ")}
                <span className="ml-2 text-muted">{formatIST(v.at)}</span>
              </p>
            ) : <p className="mt-2 text-muted">No vitals recorded. Add them in Care → Vitals.</p>}
            <p className="mt-4 flex items-center gap-2 font-medium"><Pill className="size-4 text-brown" /> Current medicines</p>
            {card?.medicines.length ? (
              <ul className="mt-2 space-y-1">
                {card.medicines.map((m, i) => <li key={i}>{m.name} {m.strength} <span className="text-muted">({m.morning}-{m.noon}-{m.night}{m.doctor ? `, Dr ${m.doctor}` : ""})</span></li>)}
              </ul>
            ) : <p className="mt-2 text-muted">No prescription saved. Scan one in Care → Prescription.</p>}
            {pos && <p className="mt-4 flex items-center gap-1.5 text-xs text-muted"><MapPin className="size-3.5" /> {pos.lat.toFixed(5)}, {pos.lng.toFixed(5)}</p>}
          </div>
        </div>
      </div>
      <p className="mt-6 text-xs text-muted">KinCare does not dispatch ambulances. In a life-threatening emergency call 112 or 108 first.</p>
    </main>
  );
}
