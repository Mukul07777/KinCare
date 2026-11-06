"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { AlertOctagon, ArrowLeft, BellPlus, Building2, Check, ExternalLink, FileText, Loader2, Share2, ShieldCheck, X } from "lucide-react";
import { ReportForm } from "@/components/ReportForm";
import { addWatch, checkBatch, formatIST, formatMonth, getWatchlist, whatsappShare, type CheckResult } from "@/lib/api";

// Must match SOURCES in api/main.py.
const SOURCE_NAMES = ["CDSCO NSQ alerts", "CDSCO spurious-drug lists", "State regulator NSQ alerts"];

const EN = {
  found: "Alert found",
  foundBody: () => "",
  action: "Show this to your pharmacist or doctor today, before your next dose.",
  clear: "No alert found",
  asOf: "As of",
  notGuarantee: "This is not a safety guarantee.",
};
const HI = {
  found: "अलर्ट मिला",
  foundBody: (cat: string) =>
    `यह बैच सरकारी (CDSCO) सूची में ${cat === "spurious" ? "नकली (स्प्यूरियस)" : "मानक गुणवत्ता से कम (NSQ)"} बताया गया है।`,
  action: "अगली खुराक से पहले, आज ही यह अपने फ़ार्मासिस्ट या डॉक्टर को दिखाएँ।",
  clear: "कोई अलर्ट नहीं मिला",
  asOf: "इस समय तक:",
  notGuarantee: "इसका मतलब यह नहीं कि दवा की जाँच हुई है। यह सुरक्षा की गारंटी नहीं है।",
};

// Each source "lands" at a staggered time so the fan-out is visible.
const REVEAL_MS = [600, 1000, 1400];

export function ResultView() {
  const params = useSearchParams();
  const batch = params.get("batch") ?? "";
  const brand = params.get("brand") ?? undefined;
  const maker = params.get("maker") ?? undefined;

  const [result, setResult] = useState<CheckResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [landed, setLanded] = useState(0);
  const [watching, setWatching] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!batch) return;
    setError(null); setResult(null); setLanded(0);
    getWatchlist().then((w) => setWatching(w.some((i) => i.batch === batch))).catch(() => {});
    checkBatch({ batch, brand, maker }).then(setResult).catch((e) => setError(e.message));
    const timers = REVEAL_MS.map((ms, i) => setTimeout(() => setLanded(i + 1), ms));
    return () => timers.forEach(clearTimeout);
  }, [batch, brand, maker, attempt]);

  const done = result && landed === SOURCE_NAMES.length;
  const found = result?.verdict === "alert_found";
  const top = result?.matches[0];

  const [askContact, setAskContact] = useState(false);
  const [contact, setContact] = useState({ name: "", phone: "", language: "hi" });
  const [member, setMember] = useState("");
  const [expiry, setExpiry] = useState(params.get("expiry") ?? "");
  const [hi, setHiState] = useState(false);
  // Remember the reader's language across checks (a per-browser convenience only).
  useEffect(() => { try { setHiState(localStorage.getItem("kincare-lang") === "hi"); } catch {} }, []);
  const setHi = (v: boolean) => { setHiState(v); try { localStorage.setItem("kincare-lang", v ? "hi" : "en"); } catch {} };
  const L = hi ? HI : EN;
  const watch = () =>
    addWatch({ batch, brand, maker, member: member || undefined, expiry: expiry || undefined, ...(contact.phone ? contact : {}) })
      .then(() => { setWatching(true); setAskContact(false); })
      .catch((e) => setError(e.message));

  if (!batch) {
    return (
      <main className="mx-auto max-w-xl px-4 py-24 text-center">
        <p className="text-muted">No batch to check.</p>
        <Link href="/scan" className="mt-4 inline-block font-medium text-brown underline">Start a scan</Link>
      </main>
    );
  }

  return (
    <main className="blush mx-auto max-w-6xl px-4 pt-10 sm:px-6 sm:pt-14">
      <div className="flex items-center justify-between">
        <Link href="/scan" className="inline-flex items-center gap-1.5 text-sm text-muted transition hover:text-brown">
          <ArrowLeft className="size-4" /> New scan
        </Link>
        <div className="flex rounded-full border border-line bg-paper p-1 text-xs">
          {[[false, "English"], [true, "हिन्दी"]].map(([v, l]) => (
            <button key={String(v)} onClick={() => setHi(v as boolean)} className={`rounded-full px-3 py-1 font-medium ${hi === v ? "bg-brown text-paper" : "text-muted"}`}>{l as string}</button>
          ))}
        </div>
      </div>

      <div className="mt-6 grid gap-5 lg:grid-cols-[1fr_1.15fr]">
        {/* Left: item + verdict */}
        <div className="space-y-4">
          <div className="card rounded-3xl p-6">
            <p className="text-xs font-medium uppercase tracking-widest text-muted">Confirmed by you</p>
            <p className="mt-2 text-3xl font-medium tracking-tight">{brand ?? "Unknown brand"}</p>
            <p className="mt-1 font-mono text-sm text-muted">
              Batch <span className="text-espresso">{batch}</span>
              {maker && <> · {maker}</>}
            </p>
          </div>

          <p className="sr-only" aria-live="assertive">{done ? (found ? L.found : L.clear) : ""}</p>
          <AnimatePresence mode="wait">
            {error ? (
              <motion.div key="err" role="alert" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="rounded-3xl border border-danger/20 bg-danger/5 p-6">
                <p className="font-medium text-danger">Couldn’t finish the check.</p>
                <p className="mt-1 text-sm text-muted">The KinCare server didn’t answer. Your batch details are kept. Nothing was lost.</p>
                <button onClick={() => setAttempt((a) => a + 1)} className="mt-4 rounded-full bg-espresso px-5 py-2.5 text-sm font-medium text-paper transition hover:bg-brown">
                  Try again
                </button>
              </motion.div>
            ) : !done ? (
              <motion.div key="load" exit={{ opacity: 0, scale: 0.98 }} className="card flex items-center gap-4 rounded-3xl p-6">
                <Loader2 className="size-6 animate-spin text-brown" />
                <div>
                  <p className="font-medium">Agents checking {SOURCE_NAMES.length} sources…</p>
                  <p className="text-sm text-muted">{landed} of {SOURCE_NAMES.length} reported back</p>
                </div>
              </motion.div>
            ) : found && top ? (
              <motion.div
                key="found"
                initial={{ opacity: 0, scale: 0.95, y: 10 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                transition={{ type: "spring", stiffness: 220, damping: 20 }}
                className="relative overflow-hidden rounded-3xl bg-danger p-7 text-paper shadow-[0_24px_60px_-20px_rgba(196,69,47,0.6)]"
              >
                <div className="dots absolute inset-0 opacity-20 [filter:invert(1)]" />
                <div className="relative">
                  <AlertOctagon className="size-9" />
                  <p className="mt-4 text-3xl font-semibold tracking-tight">{L.found}</p>
                  {hi && <p className="mt-2 leading-relaxed">{L.foundBody(top.alert.category)}</p>}
                  <p className="mt-2 leading-relaxed text-paper/95">
                    Listed as <b>{top.alert.category === "spurious" ? "spurious" : "not of standard quality"}</b> in the{" "}
                    {formatMonth(top.alert.alert_month)} regulator alert. {top.alert.reason}.
                  </p>
                  <p className="mt-4 rounded-2xl bg-paper/15 px-4 py-3 font-medium">{L.action}</p>
                  <p className="mt-3 text-sm text-paper/85">
                    Listed: {top.alert.product_name} · {top.alert.manufacturer || "maker not named"}
                    {top.alert.reported_by && <> · tested by {top.alert.reported_by}</>}
                  </p>
                  {top.score.lookalike ? (
                    <p className="mt-3 rounded-2xl bg-black/15 px-4 py-3 text-sm">
                      Your batch <b className="font-mono">{batch}</b> matches <b className="font-mono">{top.alert.batch_no}</b> only if a look-alike character was misread
                      (0 and O, 1 and I, 5 and S, 8 and B). Check the strip: if it shows <b className="font-mono">{top.alert.batch_no}</b>, don&apos;t take it.
                    </p>
                  ) : top.score.level === "possible" && (
                    <p className="mt-3 rounded-2xl bg-black/15 px-4 py-3 text-sm">
                      The batch number matches exactly, but the medicine name or maker does not clearly match. Compare your pack with the notice before acting.
                    </p>
                  )}
                  <div className="mt-4 flex flex-wrap gap-2">
                    <Link href={`/return?${params.toString()}`} className="flex items-center gap-2 rounded-full bg-paper px-4 py-2 text-sm font-medium text-danger transition hover:bg-sand">
                      <FileText className="size-4" /> Pharmacy return note
                    </Link>
                    <a href={whatsappShare(top.alert, batch)} target="_blank" rel="noreferrer" className="flex items-center gap-2 rounded-full bg-paper/15 px-4 py-2 text-sm font-medium text-paper transition hover:bg-paper/25">
                      <Share2 className="size-4" /> Share on WhatsApp
                    </a>
                    {top.alert.manufacturer && !/investigation/i.test(top.alert.manufacturer) && (
                      <Link href={`/maker?name=${encodeURIComponent(top.alert.manufacturer)}`} className="flex items-center gap-2 rounded-full bg-paper/15 px-4 py-2 text-sm font-medium text-paper transition hover:bg-paper/25">
                        <Building2 className="size-4" /> Maker history
                      </Link>
                    )}
                  </div>
                </div>
              </motion.div>
            ) : (
              <motion.div
                key="clear"
                initial={{ opacity: 0, scale: 0.95, y: 10 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                transition={{ type: "spring", stiffness: 220, damping: 20 }}
                className="rounded-3xl bg-safe p-7 text-paper shadow-[0_24px_60px_-20px_rgba(78,124,92,0.6)]"
              >
                <ShieldCheck className="size-9" />
                <p className="mt-4 text-3xl font-semibold tracking-tight">{L.clear}</p>
                <p className="mt-2 text-paper/90">{L.asOf} {formatIST(result!.checked_at)}.</p>
                <p className="text-paper/90">{L.notGuarantee}</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Right: sources + actions */}
        <div className="space-y-4">
          <div className="card rounded-3xl p-2">
            <div className="flex items-center justify-between px-4 pb-2 pt-3">
              <p className="font-medium">Sources checked</p>
              <p className="text-xs text-muted">{landed}/{SOURCE_NAMES.length}</p>
            </div>
            {SOURCE_NAMES.map((name, i) => {
              const status = result?.sources.find((s) => s.name === name)?.status;
              const arrived = i < landed && result;
              return (
                <div key={name} className="flex items-center justify-between rounded-2xl px-4 py-3.5 even:bg-cream/50">
                  <span className="text-sm">{name}</span>
                  {!arrived ? (
                    <span className="inline-flex items-center gap-2 text-xs text-muted">
                      <span className="relative flex size-2">
                        <span className="absolute inline-flex size-full animate-ping rounded-full bg-brown opacity-60" />
                        <span className="relative inline-flex size-2 rounded-full bg-brown" />
                      </span>
                      Reading…
                    </span>
                  ) : status === "match" ? (
                    <motion.span initial={{ scale: 0.6, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="inline-flex items-center gap-1.5 rounded-full bg-danger/10 px-3 py-1 text-xs font-semibold text-danger">
                      <X className="size-3.5" strokeWidth={3} /> Match
                    </motion.span>
                  ) : (
                    <motion.span initial={{ scale: 0.6, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="inline-flex items-center gap-1.5 rounded-full bg-safe/10 px-3 py-1 text-xs font-semibold text-safe">
                      <Check className="size-3.5" strokeWidth={3} /> No match
                    </motion.span>
                  )}
                </div>
              );
            })}
          </div>

          {done && (
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }} className="space-y-4">
              {found && top && top.explain?.length > 0 && (
                <div className="card rounded-3xl p-5">
                  <p className="font-medium">{hi ? "इसका क्या मतलब है" : "What this means for you"}</p>
                  <div className="mt-3 space-y-3">
                    {top.explain.map((f) => (
                      <div key={f.key} className="flex gap-3">
                        <span className={`mt-1 h-fit shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
                          f.severity === "critical" ? "bg-danger text-paper" : f.severity === "high" ? "bg-danger/15 text-danger" : f.severity === "medium" ? "bg-sand text-brown" : "bg-cream text-muted"
                        }`}>{f.severity}</span>
                        <div>
                          <p className="text-sm font-medium">{f.label}</p>
                          <p className="text-sm text-muted">{hi ? f.hi : f.en}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {found && top && (
                <div className="card grid grid-cols-3 gap-2 rounded-3xl p-5">
                  <Score label="Batch" value={top.score.batch} />
                  <Score label="Maker" value={top.score.maker} />
                  <Score label="Brand" value={top.score.brand} />
                </div>
              )}
              <div className="grid gap-3 sm:grid-cols-2">
                {found && top ? (
                  <a href={top.alert.alert_url + (top.alert.pdf_page ? `#page=${top.alert.pdf_page}` : "")} target="_blank" rel="noreferrer" className="inline-flex items-center justify-center gap-2 rounded-full bg-espresso px-6 py-4 text-sm font-medium text-paper transition hover:bg-brown-2">
                    Open regulator notice <ExternalLink className="size-4" />
                  </a>
                ) : (
                  <Link href="/scan" className="inline-flex items-center justify-center rounded-full bg-espresso px-6 py-4 text-sm font-medium text-paper transition hover:bg-brown-2">
                    Check another medicine
                  </Link>
                )}
                <button
                  onClick={() => setAskContact(true)}
                  disabled={watching}
                  className="inline-flex items-center justify-center gap-2 rounded-full border border-brown/30 bg-paper px-6 py-4 text-sm font-medium text-brown transition hover:bg-sand disabled:border-brown disabled:bg-brown disabled:text-paper"
                >
                  {watching ? <><Check className="size-4" /> Watching this batch</> : <><BellPlus className="size-4" /> Watch this batch</>}
                </button>
              </div>
              {askContact && !watching && (
                <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="card rounded-3xl p-5">
                  <p className="font-medium">Who takes this medicine?</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {["Me", "Maa", "Papa", "Dadi", "Dada", "Child"].map((m) => (
                      <button key={m} onClick={() => setMember(member === m ? "" : m)} className={`rounded-full px-3 py-1.5 text-sm ${member === m ? "bg-brown text-paper" : "bg-sand text-brown"}`}>{m}</button>
                    ))}
                    <input value={["Me", "Maa", "Papa", "Dadi", "Dada", "Child"].includes(member) ? "" : member} onChange={(e) => setMember(e.target.value)} placeholder="Other" className="w-24 rounded-full border border-line bg-cream/60 px-3 py-1.5 text-sm outline-none" />
                  </div>
                  <label className="mt-3 flex items-center gap-2 text-sm">
                    Expiry
                    <input value={expiry} onChange={(e) => setExpiry(e.target.value)} placeholder="MM/YYYY" className="w-28 rounded-xl border border-line bg-cream/60 px-3 py-1.5 font-mono text-sm outline-none" />
                  </label>
                  <p className="mt-4 font-medium">Where should we alert you?</p>
                  <p className="text-xs text-muted">If a new regulator list names this batch, you get a WhatsApp message and a voice call. Optional.</p>
                  <div className="mt-3 grid gap-2 sm:grid-cols-[1fr_1.2fr]">
                    <input value={contact.name} onChange={(e) => setContact({ ...contact, name: e.target.value })} placeholder="Name (e.g. Ravi)" className="rounded-xl border border-line bg-cream/60 px-3 py-2.5 text-sm outline-none focus:border-brown/40" />
                    <input value={contact.phone} onChange={(e) => setContact({ ...contact, phone: e.target.value })} placeholder="Phone (98xxxxxxxx)" inputMode="tel" className="rounded-xl border border-line bg-cream/60 px-3 py-2.5 text-sm outline-none focus:border-brown/40" />
                  </div>
                  <div className="mt-2 flex gap-2">
                    {[["hi", "हिन्दी"], ["en", "English"]].map(([v, l]) => (
                      <button key={v} onClick={() => setContact({ ...contact, language: v })} className={`flex-1 rounded-xl px-3 py-2 text-sm font-medium ${contact.language === v ? "bg-brown text-paper" : "bg-sand text-brown"}`}>{l}</button>
                    ))}
                    <button onClick={watch} className="flex-[2] rounded-xl bg-espresso px-3 py-2 text-sm font-medium text-paper">Save and watch</button>
                  </div>
                </motion.div>
              )}
              <p className="text-center text-xs text-muted">
                Last verified {formatIST(result!.checked_at)} ·{" "}
                {watching ? <Link href="/watchlist" className="font-medium text-brown underline">View watchlist</Link> : "We will message you if a new alert names this batch."}
              </p>
              <details className="rounded-2xl border border-line bg-paper p-4 text-sm">
                <summary className="cursor-pointer font-medium">Felt unwell or medicine not working? Report this batch</summary>
                <p className="mt-2 text-xs text-muted">Reports from many people on the same batch can flag it before any regulator list does. <Link href="/signals" className="text-brown underline">How Early Signal works</Link></p>
                <ReportForm compact batch={batch} brand={brand} maker={maker} />
              </details>
            </motion.div>
          )}
        </div>
      </div>
    </main>
  );
}

function Score({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="text-center">
      <p className="text-xs text-muted">{label} match</p>
      <p className="mt-1 text-2xl font-medium tracking-tight">{value === null ? "—" : `${Math.round(value)}%`}</p>
    </div>
  );
}
