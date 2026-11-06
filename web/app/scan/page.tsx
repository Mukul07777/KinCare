"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowRight, Camera, ImageUp, Loader2, Lock, QrCode, Receipt, RotateCcw, ScanText, Sparkles } from "lucide-react";
import { Eyebrow, Heading } from "@/components/Heading";
import { scanImage } from "@/lib/api";
import { BillScan } from "@/components/BillScan";
import { QrScan } from "@/components/QrScan";

// Real batches from CDSCO alert PDFs, plus one batch that appears in no alert.
const DEMOS = [
  { label: "Telma H", tag: "CDSCO spurious, Feb 2025", brand: "Telma H", batch: "05240198", maker: "Glenmark" },
  { label: "Dexacos", tag: "CDSCO NSQ, Jun 2025", brand: "Dexacos", batch: "P24L220", maker: "Paksons Pharmaceuticals" },
  { label: "Clean batch", tag: "not in any alert", brand: "Amlodipine 5 mg", batch: "AML24017", maker: "" },
];

type OcrState = { status: "idle" | "reading" | "done" | "error"; message?: string; lines?: string[] };

export default function ScanPage() {
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [form, setForm] = useState({ batch: "", brand: "", maker: "", expiry: "" });
  const [ocr, setOcr] = useState<OcrState>({ status: "idle" });
  const [mode, setModeState] = useState<"strip" | "qr" | "bill">("strip");
  // ?mode=qr|bill opens that tab directly (menu links, WhatsApp, the pitch), and the tab stays in the URL.
  useEffect(() => {
    const m = new URLSearchParams(window.location.search).get("mode");
    if (m === "qr" || m === "bill") setModeState(m);
  }, []);
  const setMode = (m: typeof mode) => { setModeState(m); window.history.replaceState(null, "", m === "strip" ? "/scan" : `/scan?mode=${m}`); };

  const onFile = async (file?: File) => {
    if (!file) return;
    setPreview(URL.createObjectURL(file));
    setOcr({ status: "reading" });
    try {
      const r = await scanImage(file);
      const f = r.fields;
      setForm((prev) => ({ batch: f.batch ?? prev.batch, brand: f.brand ?? prev.brand, maker: f.maker ?? prev.maker, expiry: f.expiry ?? prev.expiry }));
      const found = [f.batch && "batch", f.brand && "brand", f.maker && "maker", f.expiry && `expiry ${f.expiry}`].filter(Boolean);
      setOcr({
        status: "done",
        message: f.batch ? `Read ${found.join(", ")}. Check each field against the strip.` : "Couldn’t find a batch number. Retake closer, or type it in.",
        lines: r.lines,
      });
    } catch (e) {
      setOcr({ status: "error", message: (e as Error).message });
    }
  };

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.batch.trim()) return;
    check(form);
  };

  const check = (f: typeof form) => router.push(`/result?${new URLSearchParams(Object.entries(f).filter(([, v]) => v.trim()))}`);

  const field = (key: keyof typeof form, label: string, placeholder: string, mono = false) => (
    <label className="block">
      <span className="text-xs font-medium text-muted">{label}</span>
      <input
        value={form[key]}
        onChange={(e) => setForm({ ...form, [key]: e.target.value })}
        placeholder={placeholder}
        autoComplete="off"
        {...(mono ? { spellCheck: false, autoCapitalize: "characters", autoCorrect: "off", enterKeyHint: "go" as const } : {})}
        className={`mt-1.5 w-full rounded-2xl border border-line bg-cream/60 px-4 py-3.5 outline-none transition placeholder:text-clay focus:border-brown/40 focus:bg-paper focus:shadow-[0_0_0_4px_rgba(138,75,44,0.08)] ${
          mono ? "font-mono tracking-wider" : ""
        }`}
      />
    </label>
  );

  return (
    <main className="blush mx-auto max-w-6xl px-4 pt-12 sm:px-6 sm:pt-16">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <Eyebrow>New check</Eyebrow>
          <Heading as="h1" lead="Scan a" tail={mode === "strip" ? "medicine strip." : mode === "qr" ? "pack QR code." : "pharmacy bill."} className="mt-4 text-4xl sm:text-6xl" />
          <p className="mt-4 max-w-xl text-muted">
            {mode === "strip"
              ? "Photograph the back of the strip where the batch number is printed, then confirm the details."
              : mode === "qr"
                ? "Point the camera at the QR or Data Matrix code on the pack. Batch and expiry are read instantly, no typing."
                : "One photo of the bill checks every medicine you bought this month."}
          </p>
        </div>
        <div role="tablist" aria-label="What to scan" className="flex rounded-full border border-line bg-paper p-1 text-sm">
          {([["strip", "Strip", Camera], ["qr", "QR code", QrCode], ["bill", "Bill", Receipt]] as const).map(([v, l, Icon]) => (
            <button key={v} role="tab" aria-selected={mode === v} onClick={() => setMode(v)}
              className={`inline-flex items-center gap-1.5 rounded-full px-4 py-2 font-medium transition sm:px-5 ${mode === v ? "bg-brown text-paper" : "text-muted hover:text-espresso"}`}>
              <Icon className="size-4" /> {l}
            </button>
          ))}
        </div>
      </div>

      {mode === "qr" ? <div className="mt-10"><QrScan /></div> : mode === "bill" ? <div className="mt-10"><BillScan /></div> : (
      <div className="mt-10 grid gap-5 lg:grid-cols-[1.1fr_1fr]">
        {/* Capture */}
        <div className="card rounded-[2rem] p-3">
          <input ref={fileRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={(e) => onFile(e.target.files?.[0])} />
          <AnimatePresence mode="wait">
            {preview ? (
              <motion.div key="p" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="relative aspect-[4/3] overflow-hidden rounded-[1.6rem] bg-sand">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={preview} alt="Scanned strip" className="size-full object-cover" />
                <div className="scan-line absolute inset-x-0 top-0 h-0.5 bg-brown shadow-[0_0_18px_4px_rgba(138,75,44,0.6)] [--scan-h:340px]" />
                <button onClick={() => { setPreview(null); setOcr({ status: "idle" }); }} className="absolute right-3 top-3 inline-flex items-center gap-1.5 rounded-full bg-paper/90 px-3 py-1.5 text-xs font-medium backdrop-blur">
                  <RotateCcw className="size-3.5" /> Retake
                </button>
              </motion.div>
            ) : (
              <motion.button
                key="e"
                type="button"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onClick={() => fileRef.current?.click()}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  onFile(e.dataTransfer.files?.[0]);
                }}
                className="group relative grid aspect-[4/3] w-full place-items-center overflow-hidden rounded-[1.6rem] bg-sand/60 transition hover:bg-sand"
              >
                <div className="dots absolute inset-0 opacity-40" />
                {["left-6 top-6 border-l-2 border-t-2", "right-6 top-6 border-r-2 border-t-2", "left-6 bottom-6 border-l-2 border-b-2", "right-6 bottom-6 border-r-2 border-b-2"].map((c) => (
                  <span key={c} className={`absolute size-9 rounded-md border-brown/60 ${c}`} />
                ))}
                <div className="relative text-center">
                  <span className="mx-auto grid size-16 place-items-center rounded-full bg-brown text-paper shadow-[0_10px_30px_-8px_rgba(138,75,44,0.7)] transition group-hover:scale-105">
                    <Camera className="size-7" />
                  </span>
                  <p className="mt-4 font-medium">Tap to open camera</p>
                  <p className="mt-1 inline-flex items-center gap-1.5 text-sm text-muted">
                    <ImageUp className="size-4" /> or drop a photo here
                  </p>
                </div>
              </motion.button>
            )}
          </AnimatePresence>
          {ocr.status !== "idle" && (
            <div className={`mx-1 mt-3 rounded-2xl px-4 py-3 text-sm ${ocr.status === "error" ? "bg-danger/10 text-danger" : "bg-sand/70"}`}>
              {ocr.status === "reading" ? (
                <span className="inline-flex items-center gap-2"><Loader2 className="size-4 animate-spin text-brown" /> Reading the strip…</span>
              ) : (
                <>
                  <p className="inline-flex items-center gap-2 font-medium">{ocr.status === "done" && <ScanText className="size-4 text-brown" />}{ocr.message}</p>
                  {ocr.lines && ocr.lines.length > 0 && (
                    <details className="mt-2 text-xs text-muted">
                      <summary className="cursor-pointer">Show all text read ({ocr.lines.length} lines)</summary>
                      <p className="mt-1 font-mono">{ocr.lines.join(" · ")}</p>
                    </details>
                  )}
                </>
              )}
            </div>
          )}
          <p className="flex items-center gap-1.5 px-3 pb-1 pt-3 text-xs text-muted">
            <Lock className="size-3.5" /> Read by an OCR model on our server. The photo is not stored.
          </p>
        </div>

        {/* Confirm */}
        <form onSubmit={submit} className="card flex flex-col rounded-[2rem] p-6 sm:p-8">
          <h2 className="text-xl font-medium tracking-tight">Confirm details</h2>
          <p className="mt-1 text-sm text-muted">Type the batch exactly as printed. We match it exactly, never loosely.</p>
          <div className="mt-6 space-y-4">
            {field("batch", "Batch number *", "e.g. 05240198", true)}
            <div className="grid gap-4 sm:grid-cols-2">
              {field("brand", "Brand", "e.g. Telma H")}
              {field("maker", "Manufacturer", "e.g. Glenmark")}
              {field("expiry", "Expiry", "e.g. 01/2027")}
            </div>
          </div>
          <button
            disabled={!form.batch.trim()}
            className="group mt-6 inline-flex items-center justify-center gap-2 rounded-full bg-brown px-6 py-4 font-medium text-paper shadow-[0_10px_30px_-10px_rgba(138,75,44,0.7)] transition hover:bg-brown-2 disabled:cursor-not-allowed disabled:opacity-40 disabled:shadow-none"
          >
            Check all sources <ArrowRight className="size-4 transition group-hover:translate-x-0.5" />
          </button>

          <div className="mt-8 border-t border-line pt-6">
            <p className="inline-flex items-center gap-1.5 text-xs font-medium text-muted">
              <Sparkles className="size-3.5 text-brown" /> No strip handy? Try a real one, one tap
            </p>
            <div className="mt-3 grid gap-2 sm:grid-cols-3">
              {DEMOS.map((d) => (
                <button
                  key={d.label}
                  type="button"
                  onClick={() => { const f = { batch: d.batch, brand: d.brand, maker: d.maker, expiry: "" }; setForm(f); check(f); }}
                  className="rounded-2xl border border-line bg-cream/50 px-3 py-2.5 text-left transition hover:border-brown/40 hover:bg-paper"
                >
                  <p className="text-sm font-medium">{d.label}</p>
                  <p className="text-[11px] text-muted">{d.tag}</p>
                </button>
              ))}
            </div>
          </div>
        </form>
      </div>
      )}
    </main>
  );
}
