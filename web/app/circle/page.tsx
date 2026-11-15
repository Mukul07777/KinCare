"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { CalendarPlus, Check, KeyRound, Loader2, Pill, ShieldCheck, Sparkles, Trash2, UserMinus, Users } from "lucide-react";
import {
  createProfile, decide, deleteMed, getToken, leave, myProfiles, note, removeMember, saveAppt, saveMed, setMemberEdit, tick, unlock, updateProfile, view,
  type Med, type OwnProfile, type View,
} from "@/lib/circle";

// Big, high-contrast controls: many people using this page are over 65.
const btn = "inline-flex min-h-12 items-center justify-center gap-2 rounded-xl px-5 py-3 text-lg font-semibold focus:outline-none focus-visible:ring-4 focus-visible:ring-blue-500 disabled:opacity-50";
const primary = `${btn} bg-blue-700 text-white hover:bg-blue-800`;
const ghost = `${btn} border-2 border-slate-400 bg-white text-slate-900 hover:bg-slate-100`;
const input = "mt-1 block w-full rounded-xl border-2 border-slate-400 bg-white px-4 py-3 text-lg text-slate-900 focus:border-blue-700 focus:outline-none focus-visible:ring-4 focus-visible:ring-blue-300";
const card = "rounded-2xl border border-slate-300 bg-white p-5 shadow-sm";
const SLOT = { morning: "Morning 8:00", noon: "Afternoon 2:00", night: "Night 9:00" } as const;

function Field({ label, children, hint }: { label: string; children: React.ReactNode; hint?: string }) {
  return <label className="block text-lg font-medium text-slate-900">{label}{children}{hint && <span className="mt-1 block text-base font-normal text-slate-600">{hint}</span>}</label>;
}

function Status({ msg, err }: { msg: string; err?: boolean }) {
  return <p role={err ? "alert" : "status"} aria-live="polite" className={`min-h-7 text-lg ${err ? "text-red-700" : "text-green-800"}`}>{msg}</p>;
}

// ---------- start: create (elder) or unlock (family / caretaker) ----------
function Start({ onOpen }: { onOpen: (code: string) => void }) {
  const [mine, setMine] = useState<OwnProfile[]>([]);
  const [c, setC] = useState({ elder_name: "", member: "Me", elder_email: "", passcode: "", approve_changes: true });
  const [u, setU] = useState({ code: "", passcode: "", name: "", email: "", role: "family" });
  const [msg, setMsg] = useState(""); const [err, setErr] = useState(false); const [busy, setBusy] = useState(false);
  useEffect(() => { myProfiles().then(setMine).catch(() => {}); }, []);
  const run = async (fn: () => Promise<string>) => {
    setBusy(true); setMsg("");
    try { onOpen(await fn()); } catch (e) { setErr(true); setMsg((e as Error).message); } finally { setBusy(false); }
  };
  return (
    <div className="grid gap-6 md:grid-cols-2">
      {mine.length > 0 && (
        <section className={`${card} md:col-span-2`} aria-labelledby="mine-h">
          <h2 id="mine-h" className="text-2xl font-bold">Your care profiles</h2>
          <ul className="mt-3 flex flex-wrap gap-3">{mine.map((p) => (
            <li key={p.code}><button className={primary} onClick={() => onOpen(p.code)}>{p.elder_name} · {p.code}{p.pending.length > 0 && ` · ${p.pending.length} to approve`}</button></li>
          ))}</ul>
        </section>
      )}
      <form className={card} aria-labelledby="create-h" onSubmit={(e) => { e.preventDefault(); run(async () => (await createProfile(c)).code); }}>
        <h2 id="create-h" className="flex items-center gap-2 text-2xl font-bold"><ShieldCheck aria-hidden /> I am the elder: create my profile</h2>
        <p className="mt-1 text-lg text-slate-700">You choose the passcode and who gets it. You can remove anyone, anytime.</p>
        <div className="mt-4 space-y-4">
          <Field label="Your name"><input required className={input} value={c.elder_name} onChange={(e) => setC({ ...c, elder_name: e.target.value })} autoComplete="name" /></Field>
          <Field label="Your email (for reminders)" hint="Optional. Dose and appointment reminders come here."><input type="email" className={input} value={c.elder_email} onChange={(e) => setC({ ...c, elder_email: e.target.value })} autoComplete="email" /></Field>
          <Field label="Passcode to share with family" hint="6 or more characters. Not 123456."><input required type="password" minLength={6} className={input} value={c.passcode} onChange={(e) => setC({ ...c, passcode: e.target.value })} autoComplete="new-password" /></Field>
          <label className="flex items-start gap-3 text-lg"><input type="checkbox" className="mt-1 h-6 w-6" checked={c.approve_changes} onChange={(e) => setC({ ...c, approve_changes: e.target.checked })} />
            <span>Ask me before anyone changes my medicines</span></label>
          <button className={primary} disabled={busy}>{busy ? <Loader2 className="animate-spin" aria-hidden /> : <KeyRound aria-hidden />} Create profile</button>
        </div>
      </form>
      <form className={card} aria-labelledby="unlock-h" onSubmit={(e) => { e.preventDefault(); run(() => unlock(u)); }}>
        <h2 id="unlock-h" className="flex items-center gap-2 text-2xl font-bold"><Users aria-hidden /> Family or caretaker: open a profile</h2>
        <p className="mt-1 text-lg text-slate-700">Ask the elder for their profile ID and passcode. They will be told that you joined.</p>
        <div className="mt-4 space-y-4">
          <Field label="Profile ID"><input required className={`${input} uppercase`} placeholder="KC-XXXXXX" value={u.code} onChange={(e) => setU({ ...u, code: e.target.value })} /></Field>
          <Field label="Passcode"><input required type="password" className={input} value={u.passcode} onChange={(e) => setU({ ...u, passcode: e.target.value })} autoComplete="current-password" /></Field>
          <Field label="Your name"><input required className={input} value={u.name} onChange={(e) => setU({ ...u, name: e.target.value })} autoComplete="name" /></Field>
          <Field label="Your email" hint="Missed-dose and appointment alerts come here."><input type="email" className={input} value={u.email} onChange={(e) => setU({ ...u, email: e.target.value })} autoComplete="email" /></Field>
          <fieldset><legend className="text-lg font-medium">I am</legend>
            <div className="mt-1 flex gap-6">{["family", "caretaker"].map((r) => (
              <label key={r} className="flex items-center gap-2 text-lg capitalize"><input type="radio" name="role" className="h-6 w-6" checked={u.role === r} onChange={() => setU({ ...u, role: r })} />{r}</label>
            ))}</div>
          </fieldset>
          <button className={primary} disabled={busy}>Open profile</button>
        </div>
      </form>
      <div className="md:col-span-2"><Status msg={msg} err={err} /></div>
    </div>
  );
}

// ---------- medicine form ----------
function MedForm({ med, onSave, onCancel }: { med?: Med; onSave: (b: Record<string, unknown>) => void; onCancel: () => void }) {
  const [f, setF] = useState({ name: med?.name ?? "", strength: med?.strength ?? "", food: med?.food ?? "", morning: !!med?.morning, noon: !!med?.noon, night: !!med?.night, as_needed: !!med?.as_needed });
  return (
    <form className="mt-3 space-y-3 rounded-xl bg-slate-50 p-4" onSubmit={(e) => { e.preventDefault(); onSave(f); }} aria-label={med ? `Edit ${med.name}` : "Add a medicine"}>
      <div className="grid gap-3 sm:grid-cols-3">
        <Field label="Medicine"><input required className={input} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></Field>
        <Field label="Strength"><input className={input} placeholder="40 mg" value={f.strength} onChange={(e) => setF({ ...f, strength: e.target.value })} /></Field>
        <Field label="With food?"><select className={input} value={f.food} onChange={(e) => setF({ ...f, food: e.target.value })}>
          <option value="">No instruction</option><option>after food</option><option>before food</option></select></Field>
      </div>
      <fieldset><legend className="text-lg font-medium">When</legend>
        <div className="mt-1 flex flex-wrap gap-5">{(["morning", "noon", "night"] as const).map((s) => (
          <label key={s} className="flex items-center gap-2 text-lg"><input type="checkbox" className="h-6 w-6" checked={f[s]} onChange={(e) => setF({ ...f, [s]: e.target.checked })} />{SLOT[s]}</label>
        ))}<label className="flex items-center gap-2 text-lg"><input type="checkbox" className="h-6 w-6" checked={f.as_needed} onChange={(e) => setF({ ...f, as_needed: e.target.checked })} />Only when needed</label></div>
      </fieldset>
      <div className="flex gap-3"><button className={primary}>Save</button><button type="button" className={ghost} onClick={onCancel}>Cancel</button></div>
    </form>
  );
}

// ---------- the shared profile ----------
function Profile({ code, onClose }: { code: string; onClose: () => void }) {
  const [v, setV] = useState<View | null>(null);
  const [own, setOwn] = useState<OwnProfile | null>(null);
  const [msg, setMsg] = useState(""); const [err, setErr] = useState(false);
  const [editing, setEditing] = useState<number | "new" | null>(null);
  const [ai, setAi] = useState<{ text: string; source: string } | null>(null);
  const [lang, setLang] = useState("en");
  const [appt, setAppt] = useState({ doctor: "", specialty: "", place: "", at: "", notes: "" });

  const load = useCallback(async () => {
    try {
      setV(await view(code));
      if (!getToken(code)) myProfiles().then((ps) => setOwn(ps.find((p) => p.code === code) ?? null)).catch(() => {});
    } catch (e) { setErr(true); setMsg((e as Error).message); }
  }, [code]);
  useEffect(() => { load(); const id = setInterval(load, 30000); return () => clearInterval(id); }, [load]);
  useEffect(() => { note(code, lang).then(setAi).catch(() => setAi(null)); }, [code, lang]);

  const act = async (fn: () => Promise<unknown>, ok: string) => {
    setMsg("");
    try { const r = (await fn()) as { status?: string }; setErr(false); setMsg(r?.status === "pending" ? "Sent to the elder for approval. Nothing changes until they agree." : ok); setEditing(null); load(); }
    catch (e) { setErr(true); setMsg((e as Error).message); }
  };
  if (!v) return <div><Status msg={msg || "Loading…"} err={err} /><button className={ghost} onClick={onClose}>Back</button></div>;
  const a = v.adherence;

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold">{v.profile.elder_name}&apos;s care</h1>
          <p className="text-lg text-slate-700">Profile {v.profile.code} · you are {v.you.role === "elder" ? "the elder (in charge)" : `${v.you.name}, ${v.you.role}`}{!v.you.can_edit && " · view only"}</p>
        </div>
        <div className="flex gap-3">
          {v.you.role !== "elder" && <button className={ghost} onClick={() => leave(code).finally(onClose)}>Leave</button>}
          <button className={ghost} onClick={onClose}>Back</button>
        </div>
      </header>
      <Status msg={msg} err={err} />

      {ai && (
        <section className={`${card} border-blue-300 bg-blue-50`} aria-labelledby="note-h">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 id="note-h" className="flex items-center gap-2 text-xl font-bold"><Sparkles aria-hidden /> This week, in plain words</h2>
            <label className="text-base">Language <select className="ml-2 rounded-lg border-2 border-slate-400 px-2 py-1" value={lang} onChange={(e) => setLang(e.target.value)}><option value="en">English</option><option value="hi">हिन्दी</option></select></label>
          </div>
          <p className="mt-2 text-xl leading-relaxed" lang={lang}>{ai.text}</p>
          <p className="mt-2 text-sm text-slate-600">{ai.source === "gemini" ? "Written by Google Gemini from the numbers below. It never changes medicines." : "Summary from the numbers below."}</p>
        </section>
      )}

      {own && own.pending.length > 0 && (
        <section className={`${card} border-amber-400 bg-amber-50`} aria-labelledby="pend-h">
          <h2 id="pend-h" className="text-2xl font-bold">Waiting for your decision</h2>
          <ul className="mt-3 space-y-3">{own.pending.map((c) => (
            <li key={c.id} className="flex flex-wrap items-center justify-between gap-3">
              <span className="text-lg"><b>{c.member_name}</b> asks: {c.summary}</span>
              <span className="flex gap-2"><button className={primary} onClick={() => act(() => decide(code, c.id, true), "Approved. The schedule is updated.")}>Approve</button>
                <button className={ghost} onClick={() => act(() => decide(code, c.id, false), "Declined.")}>Decline</button></span>
            </li>))}</ul>
        </section>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <section className={card} aria-labelledby="today-h">
          <h2 id="today-h" className="text-2xl font-bold">Today&apos;s doses</h2>
          {v.today.length === 0 ? <p className="mt-2 text-lg">No doses scheduled today.</p> : (
            <ul className="mt-3 divide-y">{v.today.map((d) => (
              <li key={`${d.med_id}-${d.slot}`} className="flex flex-wrap items-center justify-between gap-3 py-3">
                <span className="text-lg"><b>{d.time}</b> {d.name} {d.strength}{d.food && ` · ${d.food}`}
                  <span className={`ml-2 rounded-full px-3 py-1 text-base font-semibold ${d.state === "taken" ? "bg-green-100 text-green-900" : d.state === "missed" ? "bg-red-100 text-red-900" : d.state === "due" ? "bg-amber-100 text-amber-900" : "bg-slate-100 text-slate-800"}`}>{d.state}</span></span>
                <button className={d.taken_at ? ghost : primary} aria-label={`${d.taken_at ? "Undo" : "Mark taken"}: ${d.name} ${d.time}`}
                  onClick={() => act(() => tick(code, { med_id: d.med_id, slot: d.slot, taken: !d.taken_at }), d.taken_at ? "Marked not taken." : "Marked as taken. The family can see it.")}>
                  {d.taken_at ? "Undo" : <><Check aria-hidden /> Taken</>}</button>
              </li>))}</ul>)}
        </section>

        <section className={card} aria-labelledby="adh-h">
          <h2 id="adh-h" className="text-2xl font-bold">Doses taken</h2>
          <dl className="mt-3 grid grid-cols-3 gap-3 text-center">
            {[["Last 7 days", a.pct_7 === null ? "–" : `${a.pct_7}%`], ["Last 30 days", a.pct_30 === null ? "–" : `${a.pct_30}%`], ["Full days in a row", a.streak_days]].map(([k, val]) => (
              <div key={k as string} className="rounded-xl bg-slate-100 p-3"><dt className="text-base text-slate-700">{k}</dt><dd className="text-3xl font-bold">{val}</dd></div>))}
          </dl>
          <ol className="mt-4 flex items-end gap-1" aria-label="Last 14 days">{a.days.slice(-14).map((d) => (
            <li key={d.day} className="flex-1" title={`${d.day}: ${d.taken} of ${d.due}`}>
              <span className="sr-only">{d.day}: {d.taken} of {d.due} doses</span>
              <div aria-hidden className={`rounded-t ${d.pct === null ? "bg-slate-200" : d.pct >= 80 ? "bg-green-600" : d.pct >= 50 ? "bg-amber-500" : "bg-red-600"}`} style={{ height: `${8 + (d.pct ?? 0) * 0.6}px` }} />
            </li>))}</ol>
          <ul className="mt-3 space-y-1 text-lg">{a.medicines.filter((m) => m.pct !== null).map((m) => (
            <li key={m.med_id}>{m.name}: <b>{m.pct}%</b> ({m.taken}/{m.due}){m.pct! < 80 && " · often missed"}</li>))}</ul>
        </section>
      </div>

      <section className={card} aria-labelledby="meds-h">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 id="meds-h" className="flex items-center gap-2 text-2xl font-bold"><Pill aria-hidden /> Medicines</h2>
          {v.you.can_edit && <button className={primary} onClick={() => setEditing("new")}>Add medicine</button>}
        </div>
        {v.you.role !== "elder" && v.profile.approve_changes === 1 && <p className="mt-1 text-lg text-slate-700">{v.profile.elder_name} approves every change you make here.</p>}
        {editing === "new" && <MedForm onCancel={() => setEditing(null)} onSave={(b) => act(() => saveMed(code, b), "Medicine added.")} />}
        <ul className="mt-3 divide-y">{v.medicines.map((m) => (
          <li key={m.id} className="py-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <span className="text-lg"><b>{m.name}</b> {m.strength} · {m.as_needed ? "only when needed" : (["morning", "noon", "night"] as const).filter((s) => m[s]).map((s) => SLOT[s]).join(", ")}{m.food && ` · ${m.food}`}</span>
              {v.you.can_edit && <span className="flex gap-2">
                <button className={ghost} onClick={() => setEditing(m.id)}>Edit</button>
                <button className={ghost} aria-label={`Stop ${m.name}`} onClick={() => confirm(`Stop ${m.name}? Only do this if the doctor said so.`) && act(() => deleteMed(code, m.id), "Medicine removed.")}><Trash2 aria-hidden /></button>
              </span>}
            </div>
            {editing === m.id && <MedForm med={m} onCancel={() => setEditing(null)} onSave={(b) => act(() => saveMed(code, b, m.id), "Saved.")} />}
          </li>))}</ul>
      </section>

      <section className={card} aria-labelledby="appt-h">
        <h2 id="appt-h" className="text-2xl font-bold">Doctor appointments</h2>
        <p className="text-lg text-slate-700">Everyone in the circle gets an email the day before and 2 hours before.</p>
        <ul className="mt-3 divide-y">{v.appointments.map((x) => (
          <li key={x.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
            <span className="text-lg"><b>{new Date(x.at).toLocaleString("en-IN", { weekday: "short", day: "numeric", month: "short", hour: "numeric", minute: "2-digit" })}</b> · {x.doctor}{x.specialty && ` (${x.specialty})`}{x.place && ` · ${x.place}`}</span>
            <span className="flex gap-2">
              <a className={ghost} href={x.gcal} target="_blank" rel="noopener noreferrer"><CalendarPlus aria-hidden /> Google Calendar</a>
              <button className={ghost} onClick={() => act(() => saveAppt(code, { status: "done" }, x.id), "Marked as done.")}>Done</button>
              <button className={ghost} onClick={() => act(() => saveAppt(code, { status: "cancelled" }, x.id), "Cancelled.")}>Cancel</button>
            </span>
          </li>))}</ul>
        <form className="mt-4 grid gap-3 sm:grid-cols-2" aria-label="Add an appointment" onSubmit={(e) => { e.preventDefault(); act(() => saveAppt(code, appt), "Appointment added. Reminders are set."); setAppt({ doctor: "", specialty: "", place: "", at: "", notes: "" }); }}>
          <Field label="Doctor"><input required className={input} value={appt.doctor} onChange={(e) => setAppt({ ...appt, doctor: e.target.value })} /></Field>
          <Field label="Date and time"><input required type="datetime-local" className={input} value={appt.at} onChange={(e) => setAppt({ ...appt, at: e.target.value })} /></Field>
          <Field label="Speciality"><input className={input} value={appt.specialty} onChange={(e) => setAppt({ ...appt, specialty: e.target.value })} /></Field>
          <Field label="Place"><input className={input} value={appt.place} onChange={(e) => setAppt({ ...appt, place: e.target.value })} /></Field>
          <div className="sm:col-span-2"><button className={primary}>Add appointment</button></div>
        </form>
      </section>

      {own && (
        <section className={card} aria-labelledby="circle-h">
          <h2 id="circle-h" className="text-2xl font-bold">Who can see your profile</h2>
          {own.members.length === 0 ? <p className="mt-2 text-lg">Nobody yet. Share your profile ID <b>{own.code}</b> and passcode with family.</p> : (
            <ul className="mt-3 divide-y">{own.members.map((m) => (
              <li key={m.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                <span className="text-lg"><b>{m.name}</b> · {m.role}{m.email && ` · ${m.email}`}</span>
                <span className="flex flex-wrap gap-2">
                  <label className="flex items-center gap-2 text-lg"><input type="checkbox" className="h-6 w-6" checked={!!m.can_edit} onChange={(e) => act(() => setMemberEdit(code, m.id, e.target.checked), "Permission updated.")} />Can edit</label>
                  <button className={ghost} onClick={() => act(() => removeMember(code, m.id), `${m.name} removed.`)}><UserMinus aria-hidden /> Remove</button>
                </span>
              </li>))}</ul>)}
          <label className="mt-4 flex items-start gap-3 text-lg"><input type="checkbox" className="mt-1 h-6 w-6" checked={v.profile.approve_changes === 1}
            onChange={(e) => act(() => updateProfile(code, { approve_changes: e.target.checked }), "Saved.")} />Ask me before anyone changes my medicines</label>
        </section>
      )}

      <section className={card} aria-labelledby="log-h">
        <h2 id="log-h" className="text-2xl font-bold">Recent activity</h2>
        <ul className="mt-2 space-y-1 text-lg">{v.activity.map((x, i) => (
          <li key={i}><b>{x.who}</b> {x.action.replace("_", " ")}{x.detail && `: ${x.detail}`} <span className="text-slate-600">· {new Date(x.at).toLocaleString("en-IN")}</span></li>))}</ul>
      </section>
    </div>
  );
}

function CirclePage() {
  const params = useSearchParams();
  const router = useRouter();
  const code = params.get("p");
  const open = (c: string | null) => router.push(c ? `/circle?p=${encodeURIComponent(c)}` : "/circle");
  return (
    <main id="main" className="mx-auto max-w-5xl px-4 py-8 text-slate-900">
      {!code && <>
        <h1 className="text-4xl font-bold">Care circle</h1>
        <p className="mb-6 mt-2 max-w-3xl text-xl text-slate-700">One shared health profile for an elder, their family and caretakers. Medicines, doses, appointments and
          email reminders in one place, and the elder decides who is in and what changes.</p>
      </>}
      {code ? <Profile code={code} onClose={() => open(null)} /> : <Start onOpen={open} />}
    </main>
  );
}

export default function Page() {
  return <Suspense><CirclePage /></Suspense>;
}
