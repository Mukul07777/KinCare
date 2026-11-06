"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { HeartPulse, Loader2, PhoneCall, ShieldCheck } from "lucide-react";
import { formatMonth, getCheckin, postCheckin, type CheckinInfo } from "@/lib/api";

const T = {
  en: {
    hello: (n: string | null) => `Hello${n ? " " + n : ""}`,
    intro: "You were sent an alert about a medicine batch. A quick check-in helps your pharmacist know who to call first.",
    how: "How are you feeling since taking this medicine?",
    ok: "I feel fine",
    unwell: "I feel unwell",
    which: "Anything like this? (tap all that apply)",
    bp: "Blood pressure, if you have a reading (optional)",
    note: "Anything else? (optional)",
    send: "Send to my pharmacist",
    urgent: "Please get medical help now",
    urgentBody: "Some of what you told us needs prompt attention. Call your doctor, or 108 for an emergency. Your pharmacist has been alerted.",
    review: "Thank you. Your pharmacist will call you",
    reviewBody: "Keep taking your medicines as advised until you speak to them. Do not stop on your own.",
    fine: "Thank you, glad you are well",
    fineBody: "Still show the alert to your pharmacist so they can replace the batch.",
    done: "You already sent a check-in. Thank you.",
  },
  hi: {
    hello: (n: string | null) => `नमस्ते${n ? " " + n : ""}`,
    intro: "आपको एक दवा के बैच के बारे में सूचना भेजी गई थी। यह छोटा-सा जवाब आपके फ़ार्मासिस्ट को बताता है कि पहले किसे फ़ोन करना है।",
    how: "यह दवा लेने के बाद आप कैसा महसूस कर रहे हैं?",
    ok: "मैं ठीक हूँ",
    unwell: "मेरी तबीयत ठीक नहीं",
    which: "क्या इनमें से कुछ है? (जो लागू हो, सब चुनें)",
    bp: "ब्लड प्रेशर, अगर नापा हो (वैकल्पिक)",
    note: "और कुछ बताना है? (वैकल्पिक)",
    send: "फ़ार्मासिस्ट को भेजें",
    urgent: "कृपया तुरंत डॉक्टरी मदद लें",
    urgentBody: "आपकी बताई कुछ बातों पर तुरंत ध्यान देना ज़रूरी है। अपने डॉक्टर को या आपातकाल में 108 पर फ़ोन करें। आपके फ़ार्मासिस्ट को सूचना दे दी गई है।",
    review: "धन्यवाद। आपके फ़ार्मासिस्ट आपको फ़ोन करेंगे",
    reviewBody: "उनसे बात होने तक दवाएँ सलाह के अनुसार लेते रहें। अपने आप बंद न करें।",
    fine: "धन्यवाद, ख़ुशी है कि आप ठीक हैं",
    fineBody: "फिर भी यह सूचना अपने फ़ार्मासिस्ट को दिखाएँ ताकि वे बैच बदल सकें।",
    done: "आप पहले ही जवाब भेज चुके हैं। धन्यवाद।",
  },
};

function Checkin() {
  const token = useSearchParams().get("t") ?? "";
  const [info, setInfo] = useState<CheckinInfo | null>(null);
  const [lang, setLang] = useState<"en" | "hi">("hi");
  const [feeling, setFeeling] = useState<"ok" | "unwell" | null>(null);
  const [symptoms, setSymptoms] = useState<string[]>([]);
  const [bp, setBp] = useState({ sys: "", dia: "" });
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<"urgent" | "review" | "ok" | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return setError("Missing check-in link.");
    getCheckin(token).then((i) => { setInfo(i); setLang(i.language === "en" ? "en" : "hi"); }).catch((e) => setError(e.message));
  }, [token]);

  const t = T[lang];
  const toggle = (k: string) => setSymptoms((s) => (s.includes(k) ? s.filter((x) => x !== k) : [...s, k]));

  const send = async () => {
    if (!feeling) return;
    setBusy(true);
    setError(null);
    try {
      const r = await postCheckin(token, { feeling, symptoms, bp_sys: bp.sys ? Number(bp.sys) : undefined, bp_dia: bp.dia ? Number(bp.dia) : undefined, note: note || undefined });
      setResult(r.triage);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="mx-auto max-w-lg px-4 pt-8">
      <div className="flex justify-end">
        <div className="flex rounded-full border border-line bg-paper p-1 text-xs">
          {([["hi", "हिन्दी"], ["en", "English"]] as const).map(([v, l]) => (
            <button key={v} onClick={() => setLang(v)} className={`rounded-full px-3 py-1 font-medium ${lang === v ? "bg-brown text-paper" : "text-muted"}`}>{l}</button>
          ))}
        </div>
      </div>

      {error && <p className="card mt-6 rounded-3xl p-6 text-center text-danger">{error}</p>}
      {!info && !error && <p className="mt-16 text-center text-muted"><Loader2 className="mx-auto size-6 animate-spin" /></p>}

      {info && !result && (
        <div className="card mt-4 rounded-[2rem] p-6 sm:p-8">
          <span className="grid size-12 place-items-center rounded-2xl bg-sand text-brown"><HeartPulse className="size-6" /></span>
          <h1 className="mt-4 text-2xl font-medium tracking-tight">{t.hello(info.name)}</h1>
          <p className="mt-2 text-sm leading-relaxed text-muted">{t.intro}</p>
          {info.alert && (
            <div className="mt-4 rounded-2xl bg-danger/5 px-4 py-3 text-sm">
              <p className="font-medium">{info.alert.brand || info.alert.product_name}</p>
              <p className="font-mono text-xs text-muted">Batch {info.batch} · {info.alert.category === "spurious" ? "spurious" : "NSQ"} · {formatMonth(info.alert.alert_month)}</p>
            </div>
          )}

          {info.responded ? (
            <p className="mt-6 rounded-2xl bg-sand/60 px-4 py-3 text-sm">{t.done}</p>
          ) : (
            <>
              <p className="mt-6 font-medium">{t.how}</p>
              <div className="mt-3 grid grid-cols-2 gap-2">
                {(["ok", "unwell"] as const).map((f) => (
                  <button key={f} onClick={() => setFeeling(f)}
                    className={`rounded-2xl border px-4 py-4 text-sm font-medium transition ${feeling === f ? (f === "ok" ? "border-safe bg-safe text-paper" : "border-danger bg-danger text-paper") : "border-line bg-cream/60"}`}>
                    {f === "ok" ? t.ok : t.unwell}
                  </button>
                ))}
              </div>

              {feeling === "unwell" && (
                <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }}>
                  <p className="mt-6 text-sm font-medium">{t.which}</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {info.symptoms.map((s) => (
                      <button key={s.key} onClick={() => toggle(s.key)}
                        className={`rounded-full border px-3 py-1.5 text-sm transition ${symptoms.includes(s.key) ? "border-brown bg-brown text-paper" : "border-line bg-cream/60"}`}>
                        {lang === "hi" ? s.hi : s.en}
                      </button>
                    ))}
                  </div>
                </motion.div>
              )}

              {feeling && (
                <>
                  <p className="mt-6 text-sm font-medium">{t.bp}</p>
                  <div className="mt-2 flex items-center gap-2">
                    <input value={bp.sys} onChange={(e) => setBp({ ...bp, sys: e.target.value.replace(/\D/g, "") })} inputMode="numeric" placeholder="120" className="w-24 rounded-xl border border-line bg-cream/60 px-3 py-2.5 text-center outline-none focus:border-brown/40" />
                    <span className="text-muted">/</span>
                    <input value={bp.dia} onChange={(e) => setBp({ ...bp, dia: e.target.value.replace(/\D/g, "") })} inputMode="numeric" placeholder="80" className="w-24 rounded-xl border border-line bg-cream/60 px-3 py-2.5 text-center outline-none focus:border-brown/40" />
                    <span className="text-xs text-muted">mmHg</span>
                  </div>
                  <textarea value={note} onChange={(e) => setNote(e.target.value)} placeholder={t.note} rows={2} className="mt-4 w-full rounded-xl border border-line bg-cream/60 px-3 py-2.5 text-sm outline-none focus:border-brown/40" />
                  <button onClick={send} disabled={busy} className="mt-4 w-full rounded-full bg-brown py-4 font-medium text-paper transition hover:bg-brown-2 disabled:opacity-50">
                    {busy ? <Loader2 className="mx-auto size-5 animate-spin" /> : t.send}
                  </button>
                </>
              )}
            </>
          )}
        </div>
      )}

      {result && (
        <motion.div initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }}
          className={`mt-6 rounded-[2rem] p-8 text-paper ${result === "urgent" ? "bg-danger" : result === "review" ? "bg-brown" : "bg-safe"}`}>
          {result === "urgent" ? <PhoneCall className="size-9" /> : <ShieldCheck className="size-9" />}
          <p className="mt-4 text-2xl font-semibold tracking-tight">{result === "urgent" ? t.urgent : result === "review" ? t.review : t.fine}</p>
          <p className="mt-2 leading-relaxed text-paper/90">{result === "urgent" ? t.urgentBody : result === "review" ? t.reviewBody : t.fineBody}</p>
          {result === "urgent" && <a href="tel:108" className="mt-5 inline-block rounded-full bg-paper px-6 py-3 font-semibold text-danger">Call 108</a>}
        </motion.div>
      )}
      <p className="mt-6 text-center text-[11px] text-muted">KinCare · This is not a diagnosis. Your answers go to your pharmacist.</p>
    </main>
  );
}

export default function CheckinPage() {
  return (
    <Suspense>
      <Checkin />
    </Suspense>
  );
}
