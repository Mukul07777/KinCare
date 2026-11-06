"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { CalendarRange, Database, FileText } from "lucide-react";
import { formatMonth, getStats, SOURCE_LABEL, type Alert, type Stats } from "@/lib/api";

const float = (d = 0) => ({
  animate: { y: [0, -8, 0] },
  transition: { duration: 5, repeat: Infinity, ease: "easeInOut" as const, delay: d },
});

export function HeroVisual() {
  const [stats, setStats] = useState<Stats | null>(null);
  useEffect(() => {
    getStats().then(setStats).catch(() => {});
  }, []);

  const months = stats?.by_month.slice(-6) ?? [];
  const maxN = Math.max(1, ...months.map((m) => m.n));
  const total = stats?.total ?? 0;

  return (
    <div className="relative mx-auto mt-14 h-[520px] w-full max-w-6xl sm:h-[460px]">
      <div className="dots pointer-events-none absolute inset-x-0 top-0 h-72 opacity-60 [mask-image:radial-gradient(ellipse_at_center,black_20%,transparent_70%)]" />

      {/* Medicine strip: centrepiece (batch from the real Feb 2025 CDSCO spurious list) */}
      <motion.div
        initial={{ opacity: 0, y: 40, rotate: -8 }}
        animate={{ opacity: 1, y: 0, rotate: -6 }}
        transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
        className="absolute left-1/2 top-0 z-20 w-[230px] -translate-x-1/2"
      >
        <motion.div {...float(0)}>
          <div className="relative overflow-hidden rounded-[22px] bg-gradient-to-br from-[#e9e4df] via-[#cfc6be] to-[#a99d93] p-4 shadow-[0_40px_80px_-20px_rgba(42,28,21,0.45)]">
            <div className="absolute inset-0 bg-[linear-gradient(115deg,transparent_30%,rgba(255,255,255,0.55)_45%,transparent_60%)]" />
            <div className="relative flex items-center justify-between text-[10px] font-semibold uppercase tracking-widest text-espresso/60">
              <span>Telma H</span>
              <span>Rx</span>
            </div>
            <div className="relative mt-3 grid grid-cols-2 gap-2.5">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="grid h-11 place-items-center rounded-full bg-gradient-to-b from-white/80 to-white/30 shadow-inner">
                  <div className="h-6 w-12 rounded-full bg-gradient-to-b from-[#fbf8f5] to-[#e4dbd3] shadow-[0_2px_6px_rgba(0,0,0,0.15)]" />
                </div>
              ))}
            </div>
            <div className="relative mt-3 rounded-lg bg-white/50 px-2.5 py-1.5 font-mono text-[10px] text-espresso/70">
              B.No. 05240198 · EXP JAN 2027
            </div>
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 1.2, type: "spring", stiffness: 260, damping: 16 }}
              className="absolute -right-1 top-10 rotate-6 rounded-full bg-danger px-3 py-1 text-[10px] font-bold text-white shadow-lg"
            >
              FLAGGED
            </motion.div>
          </div>
        </motion.div>
      </motion.div>

      {/* Bottom row: live numbers from the alert database */}
      <div className="absolute inset-x-0 bottom-0 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <motion.div {...float(0.4)} className="card rounded-2xl bg-mocha/90 p-4 text-paper">
          <div className="flex items-center justify-between text-sm">
            <span>Alerts indexed</span>
            <Database className="size-4 opacity-70" />
          </div>
          <p className="mt-3 text-3xl font-medium tracking-tight">{stats ? total.toLocaleString("en-IN") : "…"}</p>
          <p className="text-xs opacity-80">flagged batches, searchable</p>
          <div className="mt-3 flex h-6 gap-1 rounded-full bg-paper/25 p-1">
            {stats?.by_source.map((s) => (
              <div
                key={s.source}
                title={`${SOURCE_LABEL[s.source as Alert["source"]]}: ${s.n}`}
                className={`rounded-full ${s.source === "cdsco_spurious" ? "bg-danger" : s.source === "cdsco_nsq" ? "bg-paper/85" : "bg-paper/45"}`}
                style={{ width: `${Math.max(3, (s.n / total) * 100)}%` }}
              />
            ))}
          </div>
        </motion.div>

        <motion.div {...float(0.8)} className="card rounded-2xl p-4">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium">Flagged per month</span>
            <span className="text-[10px] text-muted">CDSCO + states</span>
          </div>
          <div className="mt-4 flex h-24 items-end justify-between gap-2">
            {months.map((b, i) => (
              <div key={b.month} className="flex flex-1 flex-col items-center gap-1">
                <span className="text-[10px] text-muted">{b.n}</span>
                <motion.div
                  initial={{ height: 0 }}
                  animate={{ height: `${(b.n / maxN) * 56}px` }}
                  transition={{ delay: 0.3 + i * 0.08, duration: 0.6 }}
                  className={`w-full rounded-full ${i === months.length - 1 ? "bg-brown" : "bg-clay"}`}
                />
                <span className="text-[10px] text-muted">{formatMonth(b.month).slice(0, 3)}</span>
              </div>
            ))}
          </div>
        </motion.div>

        <motion.div {...float(1.2)} className="card rounded-2xl p-4">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium">Sources</span>
            <FileText className="size-4 text-brown" />
          </div>
          <div className="mt-3 space-y-2">
            {stats?.by_source.map((s) => (
              <div key={s.source} className="flex items-center justify-between text-xs">
                <span className="text-muted">{SOURCE_LABEL[s.source as Alert["source"]]}</span>
                <span className={`font-medium ${s.source === "cdsco_spurious" ? "text-danger" : "text-espresso"}`}>{s.n}</span>
              </div>
            ))}
          </div>
        </motion.div>

        <motion.div {...float(1.6)} className="card rounded-2xl bg-clay/50 p-4">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium">Coverage</span>
            <CalendarRange className="size-4 text-brown" />
          </div>
          <p className="mt-3 text-3xl font-medium tracking-tight">{stats?.documents ?? "…"}</p>
          <p className="text-xs text-muted">regulator PDFs parsed</p>
          <p className="mt-3 text-xs">
            {stats?.coverage.start ? `${formatMonth(stats.coverage.start)} – ${formatMonth(stats.coverage.end)}` : ""}
          </p>
        </motion.div>
      </div>
    </div>
  );
}
