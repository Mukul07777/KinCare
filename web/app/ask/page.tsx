"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowUp, ExternalLink, Loader2, MessagesSquare } from "lucide-react";
import { Eyebrow, Heading } from "@/components/Heading";
import { askRegulator, formatMonth, SOURCE_LABEL, type AskResult } from "@/lib/api";

const EXAMPLES = [
  "Spurious drugs in 2026",
  "Paracetamol failures in 2025",
  "Is batch BDS25003 flagged?",
  "Cipla alerts",
  "State lab alerts this month",
];

type Turn = { q: string; a?: AskResult; error?: string };

export default function AskPage() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => end.current?.scrollIntoView({ behavior: "smooth", block: "end" }), [turns]);

  const ask = async (question: string) => {
    if (!question.trim() || busy) return;
    setQ("");
    setBusy(true);
    setTurns((t) => [...t, { q: question }]);
    try {
      const a = await askRegulator(question);
      setTurns((t) => t.map((x, i) => (i === t.length - 1 ? { ...x, a } : x)));
    } catch (e) {
      setTurns((t) => t.map((x, i) => (i === t.length - 1 ? { ...x, error: (e as Error).message } : x)));
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="blush mx-auto max-w-4xl px-4 pt-12 sm:px-6 sm:pt-16">
      <Eyebrow>Ask the regulator</Eyebrow>
      <Heading as="h1" lead="Ask about any" tail="medicine alert." className="mt-4 text-4xl sm:text-6xl" />
      <p className="mt-4 max-w-xl text-muted">
        Plain-language questions over every published CDSCO and state alert since 2019. Each answer is a database query, with every row it used linked below.
      </p>

      <div className="mt-8 space-y-6">
        {turns.length === 0 && (
          <div className="card rounded-3xl p-6">
            <p className="flex items-center gap-2 text-sm font-medium"><MessagesSquare className="size-4 text-brown" /> Try asking</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {EXAMPLES.map((e) => (
                <button key={e} onClick={() => ask(e)} className="rounded-full border border-line bg-cream/60 px-3.5 py-2 text-sm transition hover:border-brown/40 hover:bg-paper">{e}</button>
              ))}
            </div>
          </div>
        )}

        {turns.map((t, i) => (
          <div key={i} className="space-y-3">
            <div className="ml-auto w-fit max-w-[85%] rounded-3xl rounded-br-md bg-brown px-5 py-3 text-paper">{t.q}</div>
            {!t.a && !t.error && <p className="flex items-center gap-2 text-sm text-muted"><Loader2 className="size-4 animate-spin" /> Searching the alert database…</p>}
            {t.error && <p className="text-sm text-danger">{t.error}</p>}
            {t.a && (
              <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="card max-w-[95%] rounded-3xl rounded-bl-md p-5">
                <p className="leading-relaxed">{t.a.answer}</p>
                {t.a.understood.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {t.a.understood.map((u) => <span key={u} className="rounded-full bg-sand px-2.5 py-0.5 text-[11px] text-brown">{u}</span>)}
                  </div>
                )}
                {t.a.citations.length > 0 && (
                  <div className="mt-4 divide-y divide-line rounded-2xl border border-line">
                    {t.a.citations.map((c) => (
                      <div key={c.id} className="flex flex-wrap items-center justify-between gap-2 px-4 py-2.5 text-sm">
                        <div className="min-w-0">
                          <Link href={`/result?${new URLSearchParams({ batch: c.batch_no, brand: c.brand })}`} className="font-medium hover:text-brown">{c.product_name}</Link>
                          <p className="truncate text-xs text-muted">Batch {c.batch_no} · {c.manufacturer || "maker not named"} · {formatMonth(c.alert_month)}</p>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${c.category === "spurious" ? "bg-danger/10 text-danger" : "bg-sand text-brown"}`}>{SOURCE_LABEL[c.source]}</span>
                          <a href={c.alert_url + (c.pdf_page ? `#page=${c.pdf_page}` : "")} target="_blank" rel="noreferrer" className="text-muted hover:text-brown" aria-label="Source"><ExternalLink className="size-3.5" /></a>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </motion.div>
            )}
          </div>
        ))}
        <div ref={end} />
      </div>

      <form onSubmit={(e) => { e.preventDefault(); ask(q); }} className="sticky bottom-4 mt-8">
        <div className="card flex items-center gap-2 rounded-full p-2 pl-5">
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Ask about a medicine, maker, batch or month…" className="flex-1 bg-transparent py-2 text-sm outline-none placeholder:text-clay" />
          <button disabled={!q.trim() || busy} className="grid size-10 place-items-center rounded-full bg-brown text-paper transition hover:bg-brown-2 disabled:opacity-40" aria-label="Ask">
            <ArrowUp className="size-4" />
          </button>
        </div>
        <p className="mt-2 text-center text-[11px] text-muted">Answers come only from published regulator alerts. Not medical advice.</p>
      </form>
    </main>
  );
}
