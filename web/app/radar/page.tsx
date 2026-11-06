"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Loader2, QrCode, RotateCcw, ScanLine, ShieldAlert, Sparkles } from "lucide-react";
import { Eyebrow, Heading } from "@/components/Heading";
import { clearRadarDemo, formatIST, getRadar, seedRadarDemo, type Radar, type RadarRing } from "@/lib/api";

// Plain lat/lng projection of India's bounding box onto the panel.
const W = 600, H = 640, LNG0 = 67, LNG1 = 98, LAT0 = 6, LAT1 = 37.5;
const px = (lng: number) => ((lng - LNG0) / (LNG1 - LNG0)) * W;
const py = (lat: number) => ((LAT1 - lat) / (LAT1 - LAT0)) * H;

export default function RadarPage() {
  const [data, setData] = useState<Radar | null>(null);
  const [sel, setSel] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => getRadar().then((d) => { setData(d); setSel((s) => s ?? d.rings[0]?.serial ?? null); }).catch((e) => setError((e as Error).message)), []);
  useEffect(() => { load(); const t = setInterval(load, 8000); return () => clearInterval(t); }, [load]);

  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true); setError(null);
    try { await fn(); setSel(null); await load(); } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };

  const ring = data?.rings.find((r) => r.serial === sel) ?? null;

  return (
    <main className="blush mx-auto max-w-6xl px-4 pb-20 pt-12 sm:px-6 sm:pt-16">
      <Eyebrow>Fake-pack radar</Eyebrow>
      <Heading as="h1" lead="One pack, one code." tail="Copies give themselves away." className="mt-4 text-4xl sm:text-6xl" />
      <p className="mt-4 max-w-2xl text-muted">
        Since 2023 the top 300 brands carry a QR code with a serial for each pack. A copied code shows up on many phones, in cities hours apart,
        or with a batch that doesn&apos;t match. Every KinCare scan is a sensor.
      </p>

      <div className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[[data?.scans, "pack scans"], [data?.packs, "unique pack serials"], [data?.phones, "phones scanning"], [data?.clones, "copied codes found"]].map(([v, l], i) => (
          <div key={l as string} className={`card rounded-3xl p-5 ${i === 3 && data?.clones ? "bg-danger text-paper" : ""}`}>
            <p className="font-mono text-3xl font-semibold">{v ?? "–"}</p>
            <p className={`mt-1 text-xs ${i === 3 && data?.clones ? "text-paper/80" : "text-muted"}`}>{l}</p>
          </div>
        ))}
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-[1.15fr_1fr]">
        {/* Map */}
        <div className="relative overflow-hidden rounded-[2rem] bg-espresso p-4">
          <div className="dots absolute inset-0 opacity-10" />
          <svg viewBox={`0 0 ${W} ${H}`} className="relative w-full" role="img" aria-label="Map of India with pack scans">
            {[1, 2, 3].map((k) => <circle key={k} cx={W / 2} cy={H / 2} r={k * 120} fill="none" stroke="#7fd1c6" strokeOpacity={0.08} />)}
            {data?.cities.map((c) => (
              <g key={c.name}>
                <circle cx={px(c.lng)} cy={py(c.lat)} r={2.5} fill="#d9c3b4" fillOpacity={0.45} />
                <text x={px(c.lng) + 6} y={py(c.lat) + 4} fontSize={11} fill="#d9c3b4" fillOpacity={0.55}>{c.name}</text>
              </g>
            ))}
            {data?.rings.map((r) => {
              const on = r.serial === sel;
              const pts = r.points.map((p) => `${px(p.lng)},${py(p.lat)}`).join(" ");
              return (
                <g key={r.serial} onClick={() => setSel(r.serial)} className="cursor-pointer" opacity={on ? 1 : 0.35}>
                  {r.points.length > 1 && (
                    <motion.polyline key={`${r.serial}-${on}`} points={pts} fill="none" stroke={r.level === "clone" ? "#ff6b55" : "#e0a44a"} strokeWidth={on ? 2.5 : 1.5}
                      strokeDasharray="6 5" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 2.2, ease: "easeInOut" }} />
                  )}
                  {r.points.map((p, i) => (
                    <g key={i}>
                      {on && <circle cx={px(p.lng)} cy={py(p.lat)} r={14} fill="#ff6b55" fillOpacity={0.18}><animate attributeName="r" values="6;16;6" dur="2s" begin={`${i * 0.3}s`} repeatCount="indefinite" /></circle>}
                      <circle cx={px(p.lng)} cy={py(p.lat)} r={on ? 6 : 4} fill={r.level === "clone" ? "#ff6b55" : "#e0a44a"} stroke="#2a1c15" strokeWidth={2} />
                      {on && <text x={px(p.lng) + 9} y={py(p.lat) - 9} fontSize={12} fontWeight={700} fill="#fffcf9">{i + 1}</text>}
                    </g>
                  ))}
                </g>
              );
            })}
          </svg>
          {!data?.rings.length && (
            <div className="absolute inset-0 grid place-items-center p-8 text-center">
              <div className="max-w-xs text-paper/80">
                <ShieldAlert className="mx-auto size-10 text-[#7fd1c6]" />
                <p className="mt-3">No copied codes yet. Load the demo ring, or scan pack codes from a few phones.</p>
              </div>
            </div>
          )}
          <p className="relative mt-2 text-[11px] text-paper/50">Locations are rounded to about 1 km. City dots are for reference.</p>
        </div>

        {/* Detail */}
        <div className="space-y-4">
          {ring ? <RingCard r={ring} /> : (
            <div className="card rounded-[2rem] p-6 text-sm text-muted">
              <p className="text-lg font-medium text-espresso">How a copy is caught</p>
              <ul className="mt-3 list-disc space-y-1.5 pl-5">
                <li>The same serial scanned more than 50 km apart within 24 hours, on different phones</li>
                <li>The same serial printed with a different batch or expiry</li>
                <li>One pack&apos;s serial scanned on many different phones</li>
              </ul>
            </div>
          )}
          {data && data.rings.length > 1 && (
            <div className="card rounded-3xl p-4">
              <p className="text-sm font-medium">All flagged serials</p>
              <div className="mt-2 divide-y divide-line text-sm">
                {data.rings.map((r) => (
                  <button key={r.serial} onClick={() => setSel(r.serial)} className={`flex w-full items-center justify-between gap-2 py-2 text-left ${r.serial === sel ? "font-semibold" : ""}`}>
                    <span className="font-mono">{r.serial}</span>
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${r.level === "clone" ? "bg-danger text-paper" : "bg-warn-soft text-warn"}`}>{r.level}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
          <div className="clinical rounded-3xl p-5 text-sm">
            <p className="flex items-center gap-2 font-medium text-teal-2"><Sparkles className="size-4" /> Stage demo</p>
            <p className="mt-1 text-muted">
              Loads a labelled, simulated ring on the <b>QR test code</b> from Scan (Telma H, batch 05240198, a real CDSCO spurious batch).
              Then scan that test code with your own phone at <Link href="/scan" className="underline">Scan → QR</Link>: it warns you.
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <button onClick={() => act(seedRadarDemo)} disabled={busy} className="inline-flex items-center gap-1.5 rounded-full bg-teal px-4 py-2 text-xs font-semibold text-paper disabled:opacity-50">
                {busy ? <Loader2 className="size-3.5 animate-spin" /> : <QrCode className="size-3.5" />} Load demo ring
              </button>
              <button onClick={() => act(clearRadarDemo)} disabled={busy} className="inline-flex items-center gap-1.5 rounded-full border border-line bg-paper px-4 py-2 text-xs font-semibold">
                <RotateCcw className="size-3.5" /> Clear
              </button>
              <Link href="/scan" className="inline-flex items-center gap-1.5 rounded-full border border-line bg-paper px-4 py-2 text-xs font-semibold"><ScanLine className="size-3.5" /> Scan a pack</Link>
            </div>
            {error && <p className="mt-2 text-xs text-danger">{error}</p>}
          </div>
        </div>
      </div>
    </main>
  );
}

function RingCard({ r }: { r: RadarRing }) {
  return (
    <motion.div key={r.serial} initial={{ y: 8 }} animate={{ y: 0 }}
      className={`rounded-[2rem] p-6 ${r.level === "clone" ? "bg-danger text-paper" : "bg-warn-soft text-warn"}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-wider opacity-80">{r.level === "clone" ? "Copied pack code" : "Worth a look"}</p>
        {r.simulated && <span className="rounded-full border border-current px-2 py-0.5 text-[10px] font-semibold">SIMULATED DEMO</span>}
      </div>
      <p className="mt-2 font-mono text-3xl font-semibold">{r.serial}</p>
      <p className="text-sm opacity-85">{[r.gtin && `GTIN ${r.gtin}`, r.batch && `batch ${r.batch}`].filter(Boolean).join(" · ")}</p>
      <div className="mt-4 space-y-1.5 text-sm">
        {r.reasons.map((x) => <p key={x.kind} className="flex gap-2"><ShieldAlert className="mt-0.5 size-4 shrink-0" /> {x.text}</p>)}
      </div>
      <div className="mt-4 grid grid-cols-3 gap-2 text-center">
        {[[r.scans, "scans"], [r.phones, "phones"], [r.cities.length, "cities"]].map(([v, l]) => (
          <div key={l as string} className="rounded-2xl bg-paper/15 p-2"><p className="font-mono text-2xl font-semibold">{v}</p><p className="text-[11px] opacity-80">{l}</p></div>
        ))}
      </div>
      <ol className="mt-4 space-y-1 text-xs opacity-90">
        {r.points.map((p, i) => <li key={i}><b>{i + 1}.</b> {p.city ?? "Unknown place"} · {formatIST(p.at)}{p.batch && p.batch !== r.batch ? ` · printed batch ${p.batch}` : ""}</li>)}
      </ol>
      <p className="mt-4 text-xs opacity-80">Next step: report the serial to the state drug controller and the brand owner; pharmacies holding this batch get the recall flow.</p>
    </motion.div>
  );
}
