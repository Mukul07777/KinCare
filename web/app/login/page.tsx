"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, ArrowRight, Check, HeartPulse, Loader2, Lock, MessageCircle, ShieldCheck, Smartphone, Users } from "lucide-react";
import { authStart, authVerify } from "@/lib/api";

export default function LoginPage() {
  return <Suspense><Login /></Suspense>;
}

function Login() {
  const router = useRouter();
  const next = useSearchParams().get("next") || "/care";
  const [step, setStep] = useState<"phone" | "code" | "done">("phone");
  const [phone, setPhone] = useState("");
  const [digits, setDigits] = useState(["", "", "", "", "", ""]);
  const [demo, setDemo] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ new: boolean; merged: number; masked: string } | null>(null);
  const [resendIn, setResendIn] = useState(0);
  const boxes = useRef<(HTMLInputElement | null)[]>([]);

  useEffect(() => {
    if (resendIn <= 0) return;
    const t = setTimeout(() => setResendIn((s) => s - 1), 1000);
    return () => clearTimeout(t);
  }, [resendIn]);

  const send = async () => {
    const d = phone.replace(/\D/g, "");
    if (d.length < 10) return setError("Enter your 10-digit mobile number");
    setBusy(true); setError(null);
    try {
      const r = await authStart(phone);
      setDemo(r.demo_code ?? null);
      setDigits(["", "", "", "", "", ""]);
      setStep("code"); setResendIn(30);
      setTimeout(() => boxes.current[0]?.focus(), 50);
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };

  const verify = async (code: string) => {
    setBusy(true); setError(null);
    try {
      const r = await authVerify(phone, code);
      // The server swapped the guest session for a signed-in one in the HttpOnly cookie; nothing to store here.
      setResult(r); setStep("done");
      setTimeout(() => { router.push(next); router.refresh(); }, 1400);
    } catch (e) {
      setError((e as Error).message);
      setDigits(["", "", "", "", "", ""]);
      boxes.current[0]?.focus();
    } finally { setBusy(false); }
  };

  const setDigit = (i: number, v: string) => {
    const only = v.replace(/\D/g, "");
    if (only.length > 1) { // pasted the whole code
      const all = only.slice(0, 6).split("");
      const d = [...all, ...Array(6 - all.length).fill("")];
      setDigits(d);
      if (all.length === 6) verify(all.join(""));
      else boxes.current[all.length]?.focus();
      return;
    }
    const d = [...digits]; d[i] = only; setDigits(d);
    if (only && i < 5) boxes.current[i + 1]?.focus();
    if (d.every(Boolean)) verify(d.join(""));
  };

  return (
    <main className="mx-auto grid min-h-[calc(100vh-4rem)] max-w-6xl items-center gap-8 px-4 py-12 sm:px-6 lg:grid-cols-[1fr_1.05fr]">
      {/* Why sign in */}
      <div className="relative hidden overflow-hidden rounded-[2.5rem] bg-espresso p-10 text-paper lg:block">
        <div className="pointer-events-none absolute -right-20 -top-24 size-80 rounded-full bg-teal/30 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-28 -left-16 size-80 rounded-full bg-brown/50 blur-3xl" />
        <p className="relative text-sm text-paper/60">KinCare account</p>
        <p className="relative mt-3 text-4xl font-medium leading-tight tracking-tight">Your family&apos;s medicines,<br /><span className="text-paper/55">on every phone.</span></p>
        <div className="relative mt-10 space-y-5">
          {[
            [Users, "One account for the family", "Dadi's doses on her phone, your phone and the caregiver's. Same plan, same reminders."],
            [HeartPulse, "Nothing lost when you switch phones", "Prescriptions, vitals, watchlist and doctor links come with you."],
            [ShieldCheck, "No password to forget", "A 6-digit code on WhatsApp. That's it."],
          ].map(([Icon, t, d]) => {
            const I = Icon as typeof Users;
            return (
              <div key={t as string} className="flex gap-4">
                <span className="grid size-10 shrink-0 place-items-center rounded-2xl bg-paper/10"><I className="size-5 text-[#7fd6cb]" /></span>
                <div><p className="font-medium">{t as string}</p><p className="text-sm text-paper/60">{d as string}</p></div>
              </div>
            );
          })}
        </div>
        <p className="relative mt-12 flex items-center gap-2 text-xs text-paper/45"><Lock className="size-3.5" /> Batch checks and recall alerts work without an account, always.</p>
      </div>

      {/* Form */}
      <div className="card mx-auto w-full max-w-md rounded-[2.5rem] p-8 sm:p-10">
        <AnimatePresence mode="wait">
          {step === "phone" && (
            <motion.div key="phone" initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -12 }}>
              <span className="grid size-12 place-items-center rounded-2xl bg-mint"><Smartphone className="size-6 text-teal" /></span>
              <h1 className="mt-6 text-3xl font-medium tracking-tight">Sign in</h1>
              <p className="mt-2 text-sm text-muted">We&apos;ll send a 6-digit code to your WhatsApp.</p>
              <label className="mt-8 block text-xs font-medium text-muted">Mobile number</label>
              <div className="mt-2 flex items-center rounded-2xl border border-line bg-paper px-4 focus-within:border-teal/50 focus-within:ring-4 focus-within:ring-teal/10">
                <span className="border-r border-line pr-3 font-mono text-sm text-muted">+91</span>
                <input value={phone} onChange={(e) => setPhone(e.target.value)} onKeyDown={(e) => e.key === "Enter" && send()} inputMode="tel" autoFocus
                  placeholder="98765 43210" className="w-full bg-transparent px-3 py-3.5 font-mono text-lg tracking-wide outline-none placeholder:text-clay" />
              </div>
              {error && <p className="mt-3 text-sm text-danger">{error}</p>}
              <button onClick={send} disabled={busy} className="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-full bg-espresso py-3.5 font-medium text-paper transition hover:bg-brown">
                {busy ? <Loader2 className="size-4 animate-spin" /> : <MessageCircle className="size-4" />} Send code on WhatsApp
              </button>
              <p className="mt-4 text-center text-xs text-muted">New here? The same step creates your account, with 14 days of Family free.</p>
            </motion.div>
          )}

          {step === "code" && (
            <motion.div key="code" initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -12 }}>
              <button onClick={() => { setStep("phone"); setError(null); }} className="inline-flex items-center gap-1 text-sm text-muted hover:text-espresso"><ArrowLeft className="size-4" /> Change number</button>
              <h1 className="mt-6 text-3xl font-medium tracking-tight">Enter the code</h1>
              <p className="mt-2 text-sm text-muted">Sent to <b className="font-mono text-espresso">+91 {phone.replace(/\D/g, "").slice(-10)}</b> on WhatsApp.</p>
              {demo && (
                <div className="mt-5 flex items-center justify-between gap-3 rounded-2xl bg-warn-soft px-4 py-3 text-sm text-warn">
                  <span>Demo mode (WhatsApp not set up on this server): your code is <b className="font-mono tracking-widest">{demo}</b></span>
                  <button onClick={() => setDigit(0, demo)} className="shrink-0 rounded-full bg-warn px-3 py-1 text-xs font-semibold text-paper">Fill</button>
                </div>
              )}
              <div className="mt-6 flex justify-between gap-2">
                {digits.map((d, i) => (
                  <input key={i} ref={(el) => { boxes.current[i] = el; }} value={d} inputMode="numeric" autoComplete={i === 0 ? "one-time-code" : "off"} maxLength={i === 0 ? 6 : 1}
                    onChange={(e) => setDigit(i, e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Backspace" && !d && i > 0) boxes.current[i - 1]?.focus(); }}
                    className={`size-12 rounded-2xl border bg-paper text-center font-mono text-2xl font-semibold outline-none transition sm:size-14 ${error ? "border-danger/50" : d ? "border-teal/50" : "border-line"} focus:border-teal focus:ring-4 focus:ring-teal/10`} />
                ))}
              </div>
              {error && <p className="mt-3 text-sm text-danger">{error}</p>}
              <div className="mt-6 flex items-center justify-between text-sm">
                {busy ? <span className="inline-flex items-center gap-2 text-muted"><Loader2 className="size-4 animate-spin" /> Checking…</span> : <span className="text-muted">Valid for 10 minutes</span>}
                <button onClick={send} disabled={resendIn > 0 || busy} className="font-medium text-teal disabled:text-muted">
                  {resendIn > 0 ? `Resend in ${resendIn}s` : "Resend code"}
                </button>
              </div>
            </motion.div>
          )}

          {step === "done" && result && (
            <motion.div key="done" initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} className="py-6 text-center">
              <motion.span initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: "spring", stiffness: 260, damping: 16 }}
                className="mx-auto grid size-20 place-items-center rounded-full bg-teal text-paper shadow-[0_16px_40px_-12px_rgba(15,118,110,0.7)]">
                <Check className="size-10" strokeWidth={3} />
              </motion.span>
              <h1 className="mt-6 text-3xl font-medium tracking-tight">{result.new ? "Account created" : "Welcome back"}</h1>
              <p className="mt-2 text-sm text-muted">
                Signed in as <b className="font-mono text-espresso">{result.masked}</b>.
                {result.merged > 0 && <> {result.merged} item{result.merged > 1 ? "s" : ""} from this phone added to your account.</>}
              </p>
              <p className="mt-6 inline-flex items-center gap-1 text-sm text-teal">Taking you to your family&apos;s care <ArrowRight className="size-4" /></p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </main>
  );
}
