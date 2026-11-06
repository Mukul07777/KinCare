"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { AlertOctagon, ArrowUpRight, Check, Loader2, ReceiptText, RotateCcw } from "lucide-react";
import { formatIST, formatMonth, scanBill, type BillResult } from "@/lib/api";

export function BillScan() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<BillResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const onFile = async (file?: File) => {
    if (!file) return;
    setPreview(URL.createObjectURL(file));
    setResult(null);
    setError(null);
    setBusy(true);
    try {
      setResult(await scanBill(file));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid gap-5 lg:grid-cols-[1fr_1.15fr]">
      <div className="card rounded-[2rem] p-3">
        <input ref={fileRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={(e) => onFile(e.target.files?.[0])} />
        {preview ? (
          <div className="relative overflow-hidden rounded-[1.6rem] bg-sand">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={preview} alt="Pharmacy bill" className="max-h-[480px] w-full object-contain" />
            {busy && <div className="scan-line absolute inset-x-0 top-0 h-0.5 bg-brown shadow-[0_0_18px_4px_rgba(138,75,44,0.6)] [--scan-h:460px]" />}
            <button onClick={() => { setPreview(null); setResult(null); }} className="absolute right-3 top-3 inline-flex items-center gap-1.5 rounded-full bg-paper/90 px-3 py-1.5 text-xs font-medium">
              <RotateCcw className="size-3.5" /> New bill
            </button>
          </div>
        ) : (
          <button onClick={() => fileRef.current?.click()} className="group relative grid aspect-[4/3] w-full place-items-center overflow-hidden rounded-[1.6rem] bg-sand/60 transition hover:bg-sand">
            <div className="dots absolute inset-0 opacity-40" />
            <div className="relative text-center">
              <span className="mx-auto grid size-16 place-items-center rounded-full bg-brown text-paper transition group-hover:scale-105"><ReceiptText className="size-7" /></span>
              <p className="mt-4 font-medium">Photograph the pharmacy bill</p>
              <p className="mt-1 text-sm text-muted">Every batch on it is checked at once</p>
            </div>
          </button>
        )}
        <a href="/sample-bill.png" download className="mt-3 block px-3 text-xs text-muted underline">Download a sample bill to try</a>
      </div>

      <div className="card rounded-[2rem] p-6">
        <h2 className="text-xl font-medium tracking-tight">Medicines on this bill</h2>
        {!preview && <p className="mt-2 text-sm text-muted">Upload a bill to see each batch number and whether a regulator alert names it.</p>}
        {busy && <p className="mt-4 flex items-center gap-2 text-sm text-muted"><Loader2 className="size-4 animate-spin text-brown" /> Reading the bill and checking every batch…</p>}
        {error && <p className="mt-4 text-sm text-danger">{error}</p>}
        {result && (
          <>
            <div className={`mt-4 rounded-2xl px-4 py-3 text-sm font-medium ${result.flagged ? "bg-danger text-paper" : "bg-safe text-paper"}`}>
              {result.flagged
                ? `${result.flagged} of ${result.items.length} batches appear in a regulator alert`
                : `No alert found for any of ${result.items.length} batches, as of ${formatIST(result.checked_at)}`}
            </div>
            {result.items.length === 0 && <p className="mt-3 text-sm text-muted">No batch numbers found. Try a sharper, straight-on photo.</p>}
            <div className="mt-3 divide-y divide-line">
              {result.items.map((it, i) => (
                <motion.div key={it.batch} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.08 }} className="flex items-start gap-3 py-3">
                  <span className={`mt-0.5 grid size-7 shrink-0 place-items-center rounded-full ${it.match ? "bg-danger text-paper" : "bg-safe/15 text-safe"}`}>
                    {it.match ? <AlertOctagon className="size-4" /> : <Check className="size-4" />}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="font-mono text-sm font-medium">{it.batch}</p>
                    <p className="truncate text-xs text-muted">{it.line}</p>
                    {it.match && (
                      <p className="mt-1 text-xs text-danger">
                        {it.match.alert.product_name} · {it.match.alert.category === "spurious" ? "spurious" : "NSQ"} · {formatMonth(it.match.alert.alert_month)}
                        {it.match.explain?.[0] && <> · {it.match.explain[0].label}</>}
                      </p>
                    )}
                  </div>
                  <Link href={`/result?${new URLSearchParams({ batch: it.batch })}`} className="shrink-0 rounded-full border border-line px-2.5 py-1 text-xs hover:border-brown hover:text-brown">
                    Details <ArrowUpRight className="inline size-3" />
                  </Link>
                </motion.div>
              ))}
            </div>
            <p className="mt-3 text-xs text-muted">Check each batch number against the bill. Tokens that are not batch numbers simply show no alert.</p>
          </>
        )}
      </div>
    </div>
  );
}
