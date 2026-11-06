"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ArrowRight, Check, Loader2, Mic, Moon, PhoneCall, Send, Siren, Square, Sun, SunMedium, Trash2, Users, Volume2, VolumeX } from "lucide-react";
import { TelegramConnect } from "@/components/TelegramConnect";
import { dadiChat, dadiClear, dadiHistory, dadiMe, getToday, markDose, type DadiAnswer, type DadiMsg, type Dose } from "@/lib/api";

type Lang = "hi" | "en";
type Msg = Pick<DadiMsg, "role" | "text" | "kind" | "data" | "channel"> & { id: number | string; at: string };

const TRY: Record<Lang, string[]> = {
  hi: ["आज कौन सी दवा लेनी है?", "मैंने दवा ले ली", "BP 135/85", "डोलो 650 कितने की आती है?", "टेल्मा 40 किस लिए है?", "बेटे को बुलाओ"],
  en: ["Which medicines are due today?", "I took my medicine", "BP 135/85", "How much is Dolo 650?", "What is Telma 40 for?", "Call my family"],
};
const T = {
  hi: { title: "दादी मोड", sub: "बोलिए या लिखिए। KinCare बोलकर जवाब देगा।", tap: "दबाकर बोलिए", listening: "सुन रहे हैं… फिर से दबाएँ", thinking: "देख रहे हैं…",
        placeholder: "यहाँ लिखिए…", today: "आज की दवाइयाँ", none: "अभी कोई पर्ची सेव नहीं है।", addRx: "पर्ची जोड़ें", taken: "ले ली", hello: "नमस्ते! मैं KinCare हूँ। दवा, कीमत, BP या परिवार, कुछ भी पूछिए।",
        noMic: "इस ब्राउज़र में आवाज़ नहीं चलती, लिखकर पूछिए।", speak: "बोलकर सुनाएँ", family: "परिवार", from: "से संदेश" },
  en: { title: "Dadi mode", sub: "Speak or type. KinCare answers out loud.", tap: "Tap and speak", listening: "Listening… tap to stop", thinking: "Checking…",
        placeholder: "Type here…", today: "Today's medicines", none: "No prescription saved yet.", addRx: "Add prescription", taken: "Taken", hello: "Hello! I'm KinCare. Ask about medicines, prices, BP or your family.",
        noMic: "Voice isn't available in this browser. Type instead.", speak: "Speak replies", family: "Family", from: "message from" },
};
const SLOT = { morning: Sun, noon: SunMedium, night: Moon } as const;

/* eslint-disable @typescript-eslint/no-explicit-any */
const Recognition = () => (typeof window === "undefined" ? null : (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition || null);

function say(text: string, lang: Lang, onEnd?: () => void) {
  try {
    const u = new SpeechSynthesisUtterance(text.replace(/[*_]/g, ""));
    u.lang = lang === "hi" ? "hi-IN" : "en-IN";
    const vs = speechSynthesis.getVoices();
    const v = vs.find((x) => x.lang.replace("_", "-").startsWith(u.lang)) ?? vs.find((x) => x.lang.startsWith(u.lang.slice(0, 2)));
    if (v) u.voice = v;
    u.rate = 0.9; // slower for older ears
    u.onend = () => onEnd?.();
    speechSynthesis.cancel();
    speechSynthesis.speak(u);
  } catch { onEnd?.(); }
}

const hhmm = (iso: string) => new Date(iso.endsWith("Z") || iso.includes("+") ? iso : iso + "Z").toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", hour12: false });

function Actions({ m, lang }: { m: Msg; lang: Lang }) {
  const d = m.data ?? {};
  const pill = "inline-flex items-center gap-2 rounded-full border border-line bg-paper px-4 py-2.5 text-base font-medium text-espresso";
  if (m.kind === "emergency")
    return (
      <div className="mt-4 flex flex-wrap gap-2">
        <a href="tel:108" className="inline-flex items-center gap-2 rounded-full bg-paper px-6 py-3 text-lg font-bold text-danger"><PhoneCall className="size-5" /> 108</a>
        <Link href="/sos" className="inline-flex items-center gap-2 rounded-full border-2 border-paper px-6 py-3 text-lg font-bold"><Siren className="size-5" /> SOS</Link>
      </div>
    );
  if (m.kind === "price" && d.medicine) return <Link href={`/save?q=${encodeURIComponent(d.medicine.name)}`} className={`${pill} mt-4`}>{lang === "hi" ? "सारे सस्ते विकल्प" : "All cheaper options"} <ArrowRight className="size-4" /></Link>;
  if (m.kind === "uses" && d.medicine) return <Link href={`/medicine/${d.medicine.id}`} className={`${pill} mt-4`}>{lang === "hi" ? "पूरी जानकारी" : "Full details"} <ArrowRight className="size-4" /></Link>;
  if (m.kind === "batch_alert" && d.batch) return <Link href={`/result?batch=${encodeURIComponent(d.batch)}`} className="mt-4 inline-flex items-center gap-2 rounded-full border-2 border-paper px-4 py-2.5 text-base font-semibold">{lang === "hi" ? "अलर्ट देखें" : "See the alert"} <ArrowRight className="size-4" /></Link>;
  if (m.kind === "family_none") return <Link href="/family" className={`${pill} mt-4`}><Users className="size-4" /> {lang === "hi" ? "परिवार जोड़ें" : "Add family"}</Link>;
  if (m.kind === "vitals_urgent") return <a href="tel:108" className="mt-4 inline-flex items-center gap-2 rounded-full bg-paper px-5 py-2.5 text-base font-bold text-danger"><PhoneCall className="size-4" /> 108</a>;
  return null;
}

function Bubble({ m, lang, onReplay }: { m: Msg; lang: Lang; onReplay: () => void }) {
  if (m.role === "me")
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-[1.6rem] rounded-br-md bg-teal px-5 py-3.5 text-xl leading-snug text-paper sm:text-2xl">
          {m.text}
          <p className="mt-1 text-right text-xs text-paper/70">{m.channel === "telegram" ? "Telegram · " : ""}{hhmm(m.at)}</p>
        </div>
      </div>
    );
  if (m.role === "family") {
    const [who, ...rest] = m.text.split(": ");
    return (
      <div className="flex">
        <div className="max-w-[85%] rounded-[1.6rem] rounded-bl-md border-2 border-warn/30 bg-warn-soft px-5 py-4">
          <p className="flex items-center gap-1.5 text-sm font-semibold text-warn"><Users className="size-4" /> {who} {lang === "hi" ? T.hi.from : ""}</p>
          <p className="mt-1 text-xl leading-snug text-espresso sm:text-2xl">{rest.join(": ")}</p>
          <p className="mt-1 text-xs text-muted">{hhmm(m.at)}</p>
        </div>
      </div>
    );
  }
  const red = m.kind === "emergency" || m.kind === "batch_alert" || m.kind === "vitals_urgent";
  const green = m.kind === "batch_clean" || m.kind === "taken" || m.kind === "vitals_ok";
  return (
    <div className="flex">
      <div className={`max-w-[90%] rounded-[1.6rem] rounded-bl-md px-5 py-4 shadow-sm ${red ? "bg-danger text-paper" : green ? "bg-safe text-paper" : m.kind === "vitals_doctor" ? "bg-warn-soft text-espresso" : "clinical text-espresso"}`}>
        <p className="text-xl leading-snug sm:text-[26px]">{m.text}</p>
        <Actions m={m} lang={lang} />
        <div className={`mt-2 flex items-center gap-3 text-xs ${red || green ? "text-paper/75" : "text-muted"}`}>
          <button onClick={onReplay} aria-label="Hear again" className="inline-flex items-center gap-1 font-medium"><Volume2 className="size-4" /> {lang === "hi" ? "फिर सुनें" : "Hear again"}</button>
          <span>{m.channel === "telegram" ? "Telegram · " : ""}{hhmm(m.at)}</span>
        </div>
      </div>
    </div>
  );
}

export default function DadiPage() {
  const [lang, setLang] = useState<Lang>("hi");
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [doses, setDoses] = useState<Dose[] | null>(null);
  const [state, setState] = useState<"idle" | "listening" | "thinking">("idle");
  const [heard, setHeard] = useState("");
  const [typed, setTyped] = useState("");
  const [micOk, setMicOk] = useState(true);
  const [voiceOn, setVoiceOn] = useState(true);
  const [member, setMember] = useState("Me");
  const [members, setMembers] = useState<string[]>([]);
  const rec = useRef<any>(null);
  const end = useRef<HTMLDivElement>(null);
  const lastId = useRef<number>(0);
  const t = T[lang];

  const loadDoses = useCallback(() => getToday().then((d) => setDoses(d.doses)).catch(() => setDoses([])), []);
  const loadHistory = useCallback(async (speakNew = false) => {
    try {
      const h = await dadiHistory();
      const newest = h.at(-1)?.id ?? 0;
      // A family member's reminder that arrived while the page was open: read it out.
      if (speakNew && newest > lastId.current) {
        const fresh = h.filter((m) => m.id > lastId.current && m.role === "family").at(-1);
        if (fresh && voiceOn) say(fresh.text, lang);
      }
      lastId.current = newest;
      setMsgs(h);
    } catch { /* offline: keep what we have */ }
  }, [lang, voiceOn]);

  useEffect(() => {
    setMicOk(!!Recognition());
    try { setLang((localStorage.getItem("kincare.dadi.lang") as Lang) || "hi"); setVoiceOn(localStorage.getItem("kincare.dadi.voice") !== "off"); } catch {}
    try { speechSynthesis.getVoices(); } catch {}
    loadHistory(); loadDoses();
    // Who is talking matters: Papa's BP and "call my son" must reach Papa's caregiver, not "Me".
    dadiMe().then((r) => {
      setMembers(r.members);
      let saved: string | null = null;
      try { saved = localStorage.getItem("kincare.dadi.member"); } catch {}
      setMember(saved && r.members.includes(saved) ? saved : r.member);
    }).catch(() => {});
    return () => { try { rec.current?.abort(); speechSynthesis.cancel(); } catch {} };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const id = setInterval(() => { if (state === "idle") { loadHistory(true); loadDoses(); } }, 20000);
    return () => clearInterval(id);
  }, [state, loadHistory, loadDoses]);

  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [msgs, state]);

  const pickLang = (l: Lang) => { setLang(l); try { localStorage.setItem("kincare.dadi.lang", l); } catch {} };
  const toggleVoice = () => { const v = !voiceOn; setVoiceOn(v); if (!v) try { speechSynthesis.cancel(); } catch {} try { localStorage.setItem("kincare.dadi.voice", v ? "on" : "off"); } catch {} };

  const ask = async (q: string) => {
    const text = q.trim();
    if (!text || state === "thinking") return;
    const at = new Date().toISOString();
    setMsgs((m) => [...m, { id: `me-${at}`, role: "me", text, kind: null, data: {}, channel: "app", at }]);
    setTyped(""); setHeard(""); setState("thinking");
    let a: DadiAnswer;
    try { a = await dadiChat(text, lang, member); }
    catch (e) { a = { kind: "help", say: (e as Error).message, show: (e as Error).message, data: {} }; }
    setMsgs((m) => [...m, { id: `c-${at}`, role: "kincare", text: a.show, kind: a.kind, data: a.data, channel: "app", at: new Date().toISOString() }]);
    setState("idle");
    if (voiceOn) say(a.say, lang);
    if (["taken", "doses", "vitals_ok", "vitals_doctor", "vitals_urgent"].includes(a.kind)) loadDoses();
    loadHistory();
  };

  const listen = () => {
    if (state === "listening") { rec.current?.stop(); return; }
    try { speechSynthesis.cancel(); } catch {}
    const R = Recognition();
    if (!R) { setMicOk(false); return; }
    const r = new R();
    r.lang = lang === "hi" ? "hi-IN" : "en-IN";
    r.interimResults = true;
    let final = "";
    r.onresult = (e: any) => {
      let text = "";
      for (let i = 0; i < e.results.length; i++) text += e.results[i][0].transcript;
      setHeard(text);
      if (e.results[e.results.length - 1].isFinal) final = text;
    };
    r.onerror = () => setState("idle");
    r.onend = () => { if (final) ask(final); else setState((s) => (s === "listening" ? "idle" : s)); };
    rec.current = r;
    setHeard(""); setState("listening");
    r.start();
  };

  const tick = async (d: Dose) => {
    setDoses((ds) => ds?.map((x) => (x === d ? { ...x, taken_at: x.taken_at ? null : new Date().toISOString() } : x)) ?? null);
    await markDose(d.med_id, d.slot, !d.taken_at).catch(() => {});
    if (!d.taken_at && voiceOn) say(lang === "hi" ? `${d.name} दर्ज कर ली। शाबाश!` : `${d.name} ticked. Well done!`, lang);
    loadDoses();
  };

  const clear = async () => { await dadiClear().catch(() => {}); setMsgs([]); lastId.current = 0; };

  return (
    <main className="blush mx-auto flex min-h-[calc(100dvh-4rem)] max-w-3xl flex-col px-4 pt-6 sm:px-6">
      {/* top bar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex rounded-full border border-line bg-paper p-1 text-base">
          {(["hi", "en"] as const).map((l) => (
            <button key={l} onClick={() => pickLang(l)} aria-pressed={lang === l}
              className={`rounded-full px-5 py-2 font-semibold transition ${lang === l ? "bg-teal text-paper" : "text-muted"}`}>{l === "hi" ? "हिंदी" : "English"}</button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <button onClick={toggleVoice} aria-pressed={voiceOn} aria-label={t.speak}
            className={`grid size-11 place-items-center rounded-full border border-line ${voiceOn ? "bg-mint text-teal" : "bg-paper text-muted"}`}>
            {voiceOn ? <Volume2 className="size-5" /> : <VolumeX className="size-5" />}
          </button>
          <Link href="/family" className="inline-flex items-center gap-2 rounded-full border border-line bg-paper px-4 py-2.5 text-base font-medium"><Users className="size-5" /> {t.family}</Link>
          <a href="tel:108" className="inline-flex items-center gap-2 rounded-full bg-danger px-5 py-2.5 text-base font-semibold text-paper"><PhoneCall className="size-5" /> 108</a>
        </div>
      </div>

      <div className="mt-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">{t.title}</h1>
          <p className="mt-1 text-lg text-muted">{t.sub}</p>
        </div>
        <TelegramConnect role="self" compact />
      </div>

      {members.length > 1 && (
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <span className="text-base text-muted">{lang === "hi" ? "कौन बात कर रहा है?" : "Who is talking?"}</span>
          {members.map((m) => (
            <button key={m} onClick={() => { setMember(m); try { localStorage.setItem("kincare.dadi.member", m); } catch {} }} aria-pressed={member === m}
              className={`rounded-full px-4 py-2 text-base font-medium ${member === m ? "bg-espresso text-paper" : "border border-line bg-paper"}`}>{m}</button>
          ))}
        </div>
      )}

      {/* today's medicines, always in view */}
      <section className="mt-5 rounded-[1.75rem] border border-line bg-paper p-4">
        <p className="px-1 text-base font-semibold text-brown">{t.today}</p>
        {doses === null ? (
          <div className="mt-3 h-16 animate-pulse rounded-2xl bg-sand/60" />
        ) : doses.length === 0 ? (
          <p className="mt-2 px-1 text-lg text-muted">{t.none} <Link href="/care" className="font-medium text-teal">{t.addRx} →</Link></p>
        ) : (
          <div className="-mx-1 mt-3 flex gap-2 overflow-x-auto px-1 pb-1">
            {doses.map((d) => {
              const Icon = SLOT[d.slot];
              return (
                <button key={`${d.med_id}-${d.slot}`} onClick={() => tick(d)} aria-pressed={!!d.taken_at}
                  className={`flex min-w-44 shrink-0 items-center gap-3 rounded-2xl px-4 py-3 text-left transition ${d.taken_at ? "bg-safe text-paper" : "bg-cream hover:bg-mint"}`}>
                  <span className={`grid size-11 shrink-0 place-items-center rounded-full ${d.taken_at ? "bg-paper/20" : "bg-paper"}`}>
                    {d.taken_at ? <Check className="size-6" /> : <Icon className="size-5 text-brown" />}
                  </span>
                  <span>
                    <span className="block text-lg font-semibold leading-tight">{d.name}</span>
                    <span className={`block text-sm ${d.taken_at ? "text-paper/80" : "text-muted"}`}>{d.time}{d.member !== "Me" ? ` · ${d.member}` : ""}{d.taken_at ? ` · ${t.taken}` : ""}</span>
                  </span>
                </button>
              );
            })}
          </div>
        )}
      </section>

      {/* the conversation */}
      <section aria-live="polite" className="mt-5 flex-1 space-y-4 pb-6">
        {msgs.length === 0 && (
          <div className="clinical rounded-[1.6rem] rounded-bl-md px-5 py-4 text-xl leading-snug text-espresso sm:text-2xl">{t.hello}</div>
        )}
        {msgs.map((m) => <Bubble key={m.id} m={m} lang={lang} onReplay={() => say(m.text, lang)} />)}
        {state === "thinking" && (
          <div className="flex"><div className="clinical inline-flex items-center gap-2 rounded-[1.6rem] rounded-bl-md px-5 py-4 text-lg text-muted"><Loader2 className="size-5 animate-spin" /> {t.thinking}</div></div>
        )}
        {state === "listening" && heard && <p className="text-right text-xl italic text-muted">“{heard}”</p>}
        {msgs.length > 0 && (
          <div className="text-center"><button onClick={clear} className="inline-flex items-center gap-1 text-sm text-muted hover:text-danger"><Trash2 className="size-3.5" /> {lang === "hi" ? "बातचीत मिटाएँ" : "Clear chat"}</button></div>
        )}
        <div ref={end} />
      </section>

      {/* composer */}
      <div className="sticky bottom-0 -mx-4 border-t border-line bg-cream/95 px-4 pb-[max(1rem,env(safe-area-inset-bottom))] pt-3 backdrop-blur sm:-mx-6 sm:px-6">
        <div className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-3">
          {TRY[lang].map((q) => (
            <button key={q} onClick={() => ask(q)} disabled={state === "thinking"} className="shrink-0 rounded-full border border-line bg-paper px-4 py-2.5 text-base transition hover:bg-mint disabled:opacity-50">{q}</button>
          ))}
        </div>
        <div className="flex items-center gap-3">
          <button onClick={listen} disabled={state === "thinking" || !micOk} aria-label={state === "listening" ? t.listening : t.tap}
            className={`relative grid size-20 shrink-0 place-items-center rounded-full text-paper shadow-[0_16px_40px_-14px_rgba(15,118,110,0.8)] transition disabled:opacity-50 ${state === "listening" ? "bg-danger" : "bg-teal hover:bg-teal-2"}`}>
            {state === "listening" && <span className="absolute inset-0 animate-ping rounded-full bg-danger/40" />}
            {state === "listening" ? <Square className="relative size-8" /> : <Mic className="relative size-9" />}
          </button>
          <form onSubmit={(e) => { e.preventDefault(); ask(typed); }} className="flex min-w-0 flex-1 items-center gap-2 rounded-full border border-line bg-paper py-1.5 pl-5 pr-1.5 focus-within:border-teal/40">
            <input value={typed} onChange={(e) => setTyped(e.target.value)} placeholder={state === "listening" ? t.listening : t.placeholder} aria-label={t.placeholder}
              className="min-w-0 flex-1 bg-transparent py-2 text-xl outline-none" />
            <button disabled={state === "thinking" || !typed.trim()} aria-label="Send" className="grid size-12 shrink-0 place-items-center rounded-full bg-espresso text-paper disabled:opacity-40"><Send className="size-5" /></button>
          </form>
        </div>
        {!micOk && <p className="mt-2 text-center text-sm text-danger">{t.noMic}</p>}
        <p className="mt-2 text-center text-xs text-muted">
          {lang === "hi" ? "KinCare कभी दवा शुरू, बंद या बदलने को नहीं कहता।" : "KinCare never tells you to start, stop or change a medicine."}
        </p>
      </div>
    </main>
  );
}
