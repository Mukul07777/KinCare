"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowRight, CalendarX2, ExternalLink, ImageUp, Loader2, QrCode, ScanLine, Square } from "lucide-react";
import type { DecodeHintType as Hint } from "@zxing/library";
import { parsePackCode, type PackCode } from "@/lib/qr";
import Link from "next/link";
import { formatMonth, packScan, type PackVerdict } from "@/lib/api";

// Test codes in the real formats, carrying batches from real CDSCO alerts. Labelled as tests in the UI.
const TESTS = [
  { label: "GS1 code, spurious batch", hint: "Telma H 05240198, CDSCO Feb 2025", text: "0108901234567890172701311005240198\u001d21TST0001" },
  { label: "Maker link, NSQ batch", hint: "Dexacos P24L220, CDSCO Jun 2025", text: "https://verify.example-pharma.in/check?product=Dexacos&batch=P24L220&mfr=Paksons%20Pharmaceuticals&exp=11/2026" },
  { label: "Clean batch", hint: "in no alert", text: "Brand: Amlodipine 5 mg\nBatch No: AML24017\nExp: 03/2027" },
];

type Controls = { stop: () => void };

export function QrScan() {
  const router = useRouter();
  const video = useRef<HTMLVideoElement>(null);
  const testBox = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const controls = useRef<Controls | null>(null);
  const [live, setLive] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [code, setCode] = useState<PackCode | null>(null);
  const [form, setForm] = useState({ batch: "", brand: "", maker: "", expiry: "" });
  const [shown, setShown] = useState<string | null>(null);
  const [pack, setPack] = useState<PackVerdict | "checking" | null>(null);

  useEffect(() => () => controls.current?.stop(), []);

  const found = (text: string) => {
    const c = parsePackCode(text);
    setCode(c);
    setForm({ batch: c.batch ?? "", brand: c.brand ?? "", maker: c.maker ?? "", expiry: c.expiry ?? "" });
    try { navigator.vibrate?.(80); } catch {}
    setPack(null);
    if (c.serial) checkPack(c);
  };

  // Every scan with a pack serial feeds the fake-pack radar. Location is optional and rounded to ~1 km by the API.
  const checkPack = async (c: PackCode) => {
    setPack("checking");
    const where = await new Promise<GeolocationPosition | null>((res) => {
      try { navigator.geolocation.getCurrentPosition(res, () => res(null), { timeout: 4000, maximumAge: 600000 }); } catch { res(null); }
    });
    try {
      setPack(await packScan({ serial: c.serial!, gtin: c.gtin, batch: c.batch, expiry: c.expiry,
        ...(where ? { lat: where.coords.latitude, lng: where.coords.longitude } : {}) }));
    } catch { setPack(null); }
  };

  const reader = async () => {
    const [{ BrowserMultiFormatReader }, { BarcodeFormat, DecodeHintType }] = await Promise.all([import("@zxing/browser"), import("@zxing/library")]);
    const hints = new Map<Hint, unknown>([[DecodeHintType.POSSIBLE_FORMATS, [BarcodeFormat.QR_CODE, BarcodeFormat.DATA_MATRIX]], [DecodeHintType.TRY_HARDER, true]]);
    return new BrowserMultiFormatReader(hints);
  };

  const start = async () => {
    setError(null); setCode(null); setBusy(true);
    try {
      const r = await reader();
      controls.current = await r.decodeFromConstraints({ video: { facingMode: "environment" } }, video.current!, (res) => {
        if (!res) return;
        controls.current?.stop();
        setLive(false);
        found(res.getText());
      });
      setLive(true);
    } catch (e) {
      const m = (e as Error).message || "";
      setError(/NotAllowed|denied|Permission/i.test(m) ? "Camera permission was blocked. Allow it, or upload a photo of the code." : "Could not open the camera. Upload a photo of the code instead.");
    } finally { setBusy(false); }
  };

  const stop = () => { controls.current?.stop(); setLive(false); };

  const onFile = async (file?: File) => {
    if (!file) return;
    setError(null); setBusy(true);
    try {
      const r = await reader();
      found((await r.decodeFromImageUrl(URL.createObjectURL(file))).getText());
    } catch {
      setError("No QR or Data Matrix code found in that photo. Fill the frame with the code and keep it sharp.");
    } finally { setBusy(false); }
  };

  // Draw a test code on screen so someone can scan it with their own phone.
  const showTest = (text: string) => setShown(text);
  useEffect(() => {
    if (!shown) return;
    import("@zxing/browser").then(({ BrowserQRCodeSvgWriter }) => testBox.current?.replaceChildren(new BrowserQRCodeSvgWriter().write(shown, 220, 220)));
  }, [shown]);

  const check = () => {
    if (!form.batch.trim()) return;
    router.push(`/result?${new URLSearchParams(Object.entries(form).filter(([, v]) => v.trim()))}`);
  };

  const expired = code?.expiry && code.expiry < new Date().toISOString().slice(0, 7);

  return (
    <div className="grid gap-5 lg:grid-cols-[1.1fr_1fr]">
      <div className="card rounded-[2rem] p-3">
        <input ref={fileRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={(e) => onFile(e.target.files?.[0])} />
        <div className="relative grid aspect-[4/3] place-items-center overflow-hidden rounded-[1.6rem] bg-espresso">
          <video ref={video} muted playsInline className={live ? "absolute inset-0 size-full object-cover" : "hidden"} />
          {live && (
            <>
              <div className="pointer-events-none absolute inset-[18%] rounded-3xl border-4 border-paper/80 shadow-[0_0_0_9999px_rgba(0,0,0,0.35)]" />
              <div className="scan-line absolute inset-x-[18%] top-[18%] h-0.5 bg-paper shadow-[0_0_18px_4px_rgba(255,255,255,0.6)] [--scan-h:220px]" />
              <button onClick={stop} className="absolute bottom-3 right-3 inline-flex items-center gap-1.5 rounded-full bg-paper/90 px-3 py-1.5 text-xs font-medium"><Square className="size-3" /> Stop</button>
            </>
          )}
          {!live && (
            <div className="p-8 text-center text-paper">
              <QrCode className="mx-auto size-12 text-paper/70" />
              <p className="mt-3 text-lg font-medium">Scan the QR code on the pack</p>
              <p className="mx-auto mt-1 max-w-sm text-sm text-paper/70">Since August 2023 the top 300 brands in India must print one with the batch and expiry (Schedule H2). Data Matrix codes work too.</p>
              <div className="mt-5 flex flex-wrap justify-center gap-2">
                <button onClick={start} disabled={busy} className="inline-flex items-center gap-2 rounded-full bg-paper px-5 py-2.5 text-sm font-semibold text-espresso disabled:opacity-60">
                  {busy ? <Loader2 className="size-4 animate-spin" /> : <ScanLine className="size-4" />} Open camera
                </button>
                <button onClick={() => fileRef.current?.click()} className="inline-flex items-center gap-2 rounded-full border border-paper/40 px-5 py-2.5 text-sm font-medium"><ImageUp className="size-4" /> Upload photo</button>
              </div>
            </div>
          )}
        </div>
        {error && <p className="px-3 pt-3 text-sm text-danger">{error}</p>}
        <div className="px-3 pb-2 pt-4">
          <p className="text-xs font-medium text-muted">No pack to hand? Test codes (real flagged batches, sample codes):</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {TESTS.map((t) => (
              <span key={t.label} className="inline-flex overflow-hidden rounded-full border border-line text-xs">
                <button onClick={() => found(t.text)} className="bg-paper px-3 py-1.5 font-medium hover:bg-cream" title={t.hint}>{t.label}</button>
                <button onClick={() => showTest(t.text)} className="border-l border-line bg-sand px-2.5 py-1.5 text-brown" title="Show this code to scan with another phone"><QrCode className="size-3.5" /></button>
              </span>
            ))}
          </div>
          {shown && (
            <div className="mt-3 flex items-center gap-4 rounded-2xl bg-paper p-3">
              <div ref={testBox} className="size-[220px] shrink-0 rounded-xl bg-white p-1" />
              <p className="text-xs text-muted">Scan this with another phone at <b>/scan → QR</b>. It holds a test code, not a real pack.</p>
            </div>
          )}
        </div>
      </div>

      <AnimatePresence mode="wait">
        {code ? (
          <motion.div key="c" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="card rounded-[2rem] p-6">
            <p className="text-xs font-semibold uppercase tracking-wider text-brown">
              {code.format === "gs1" ? "GS1 product code" : code.format === "url" ? "Maker verification link" : "Printed code"} read
            </p>
            {expired && (
              <p className="mt-3 flex items-center gap-2 rounded-2xl bg-danger p-3 text-sm font-semibold text-paper"><CalendarX2 className="size-4" /> Expired {formatMonth(code.expiry!)}. Do not use. Return it to the chemist.</p>
            )}
            <div className="mt-4 grid grid-cols-2 gap-3">
              {([["batch", "Batch number", true], ["expiry", "Expiry (YYYY-MM)", false], ["brand", "Brand", false], ["maker", "Manufacturer", false]] as const).map(([k, label, mono]) => (
                <label key={k} className="block">
                  <span className="text-xs font-medium text-muted">{label}</span>
                  <input value={form[k]} onChange={(e) => setForm({ ...form, [k]: e.target.value })}
                    className={`mt-1 w-full rounded-2xl border border-line bg-cream/60 px-3 py-2.5 text-sm outline-none focus:border-brown/40 ${mono ? "font-mono tracking-wider" : ""}`} />
                </label>
              ))}
            </div>
            <dl className="mt-4 space-y-1 text-xs text-muted">
              {code.gtin && <div className="flex justify-between"><dt>Product code (GTIN)</dt><dd className="font-mono">{code.gtin}</dd></div>}
              {code.mfg && <div className="flex justify-between"><dt>Manufactured</dt><dd>{formatMonth(code.mfg)}</dd></div>}
              {code.serial && <div className="flex justify-between"><dt>Pack serial</dt><dd className="font-mono">{code.serial}</dd></div>}
            </dl>
            {code.url && (
              <a href={code.url} target="_blank" rel="noreferrer noopener" className="mt-3 inline-flex items-center gap-1.5 text-xs font-medium text-brown underline">
                <ExternalLink className="size-3.5" /> Open the link in the code ({new URL(code.url).hostname})
              </a>
            )}
            {!form.batch && <p className="mt-3 text-sm text-danger">This code has no batch number. Type it from the strip.</p>}
            <button onClick={check} disabled={!form.batch.trim()} className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-full bg-brown py-3.5 font-medium text-paper hover:bg-brown-2 disabled:opacity-50">
              Check this batch against every alert <ArrowRight className="size-4" />
            </button>
            {pack === "checking" && <p className="mt-4 flex items-center gap-2 text-xs text-muted"><Loader2 className="size-3.5 animate-spin" /> Checking this pack&apos;s serial on the fake-pack radar…</p>}
            {pack && pack !== "checking" && (
              <div className={`mt-4 rounded-2xl p-4 text-sm ${pack.level === "clone" ? "bg-danger text-paper" : pack.level === "watch" ? "bg-warn-soft text-warn" : "bg-mint text-teal-2"}`}>
                <p className="font-semibold">
                  {pack.level === "clone" ? "⚠️ This pack code looks copied" : pack.level === "watch" ? "This serial has been scanned on several phones"
                    : pack.you_before ? "You scanned this pack before" : pack.seen_before ? "Serial seen before, nothing suspicious" : "✓ First scan of this pack serial"}
                </p>
                {pack.reasons.map((r) => <p key={r.kind} className="mt-1">{r.text}</p>)}
                {pack.level === "clone" && <p className="mt-2">A real pack has one serial. Don&apos;t take it; show it to your chemist and report it.</p>}
                {pack.level !== "ok" && <Link href="/radar" className="mt-2 inline-flex items-center gap-1 font-semibold underline">See it on the fake-pack radar <ArrowRight className="size-3.5" /></Link>}
              </div>
            )}
            <p className="mt-3 text-[11px] text-muted">A QR code can be copied onto a fake pack. KinCare checks the batch against regulator alerts and watches each serial for copies; it cannot prove a single pack is genuine.</p>
          </motion.div>
        ) : (
          <motion.div key="e" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="card rounded-[2rem] p-6 text-sm text-muted">
            <p className="text-lg font-medium text-espresso">What the code tells you</p>
            <ul className="mt-3 list-disc space-y-1.5 pl-5">
              <li>Batch number, checked against every CDSCO and state alert since 2019</li>
              <li>Expiry, with a warning if it has passed</li>
              <li>Product code and manufacture date, if the maker prints them</li>
            </ul>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
