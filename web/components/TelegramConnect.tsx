"use client";

import { useEffect, useRef, useState } from "react";
import { Check, Copy, Globe, Loader2, Send, Smartphone, X } from "lucide-react";
import { getTelegramInfo, telegramLink } from "@/lib/api";

/** Free chat + alerts on Telegram: no per-message fee, no 24-hour window. Hidden when the server has no bot.
 *
 * t.me's "Start bot" button only works when the Telegram app is installed on that computer, so the panel offers
 * three ways that always work: scan a QR with the phone, Telegram Web in the browser, or type the code. */
export function TelegramConnect({ role, compact = false }: { role: "self" | "caregiver"; compact?: boolean }) {
  const [info, setInfo] = useState<{ ready: boolean; bot: string | null; linked: number } | null>(null);
  const [link, setLink] = useState<{ url: string; code: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [copied, setCopied] = useState(false);
  const qr = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const load = () => getTelegramInfo().then(setInfo).catch(() => {});
    load();
    window.addEventListener("focus", load); // back from Telegram after pressing Start
    return () => window.removeEventListener("focus", load);
  }, []);

  // While the panel is open, check every 3 s whether Start was pressed, then close it.
  useEffect(() => {
    if (!link) return;
    const id = setInterval(() => getTelegramInfo().then((i) => { setInfo(i); if (i.linked) setLink(null); }).catch(() => {}), 3000);
    return () => clearInterval(id);
  }, [link]);

  useEffect(() => {
    if (!link || !qr.current) return;
    const el = qr.current;
    import("@zxing/browser").then(({ BrowserQRCodeSvgWriter }) => {
      el.innerHTML = "";
      const svg = new BrowserQRCodeSvgWriter().write(link.url, 168, 168);
      el.appendChild(svg);
    }).catch(() => {});
  }, [link]);

  if (!info?.ready) return null;

  const connect = async () => {
    setBusy(true); setErr("");
    try { setLink(await telegramLink(role)); }
    catch (e) { setErr((e as Error).message); }
    finally { setBusy(false); }
  };

  if (info.linked && !link) {
    return (
      <p className={`inline-flex items-center gap-2 rounded-full bg-[#e6f3fb] px-4 py-2 font-medium text-[#1b6fa8] ${compact ? "text-sm" : "text-base"}`}>
        <Check className="size-4" /> Telegram connected
      </p>
    );
  }
  const label = role === "self" ? "Talk to KinCare on Telegram" : "Get alerts on Telegram";
  const startCmd = link ? `/start ${link.code}` : "";
  const web = link && info.bot ? `https://web.telegram.org/k/#?tgaddr=${encodeURIComponent(`tg://resolve?domain=${info.bot}&start=${link.code}`)}` : "";

  return (
    <div className={compact ? "" : "rounded-3xl bg-[#e6f3fb] p-5"}>
      {!compact && (
        <p className="text-sm text-[#21557a]">
          {role === "self" ? "Same chat on Telegram: strip photos, “1” after a dose, BP, prices, reminders. Free, no limits." : "Missed doses, worrying readings and SOS arrive as Telegram messages. Free."}
        </p>
      )}
      <button onClick={connect} disabled={busy}
        className={`${compact ? "" : "mt-3 "}inline-flex items-center gap-2 rounded-full bg-[#229ed9] px-4 py-2.5 text-sm font-medium text-white hover:brightness-95 disabled:opacity-60`}>
        {busy ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />} {label}
      </button>
      {err && <p className="mt-2 text-sm text-danger">{err}</p>}

      {link && (
        <div role="dialog" aria-label="Connect Telegram" className="fixed inset-0 z-[60] grid place-items-center bg-espresso/40 p-4" onClick={() => setLink(null)}>
          <div onClick={(e) => e.stopPropagation()} className="w-full max-w-md rounded-[2rem] bg-paper p-6 text-espresso shadow-2xl">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-lg font-semibold">Connect @{info.bot}</p>
                <p className="text-sm text-muted">Any one of these. This page turns green by itself once you press Start.</p>
              </div>
              <button onClick={() => setLink(null)} aria-label="Close" className="rounded-full p-1.5 hover:bg-cream"><X className="size-5" /></button>
            </div>

            <div className="mt-5 flex items-center gap-4 rounded-2xl bg-cream p-4">
              <div ref={qr} className="size-[168px] shrink-0 rounded-xl bg-white p-1 [&_svg]:size-full" aria-label="QR code" />
              <div className="text-sm">
                <p className="flex items-center gap-1.5 font-semibold"><Smartphone className="size-4 text-[#229ed9]" /> On your phone</p>
                <p className="mt-1 text-muted">Open the camera, scan this, tap the link. Telegram opens: press <b>Start</b>.</p>
              </div>
            </div>

            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              <a href={web} target="_blank" rel="noreferrer" className="inline-flex items-center justify-center gap-2 rounded-full bg-[#229ed9] px-4 py-3 text-sm font-medium text-white hover:brightness-95">
                <Globe className="size-4" /> Telegram Web
              </a>
              <a href={link.url} target="_blank" rel="noreferrer" className="inline-flex items-center justify-center gap-2 rounded-full border border-line px-4 py-3 text-sm font-medium hover:bg-cream">
                <Send className="size-4" /> Telegram app
              </a>
            </div>

            <div className="mt-4 rounded-2xl border border-dashed border-clay p-4 text-sm">
              <p className="text-muted">Or open <b>@{info.bot}</b> in Telegram and send:</p>
              <button onClick={async () => { await navigator.clipboard.writeText(startCmd).catch(() => {}); setCopied(true); setTimeout(() => setCopied(false), 1500); }}
                className="mt-2 flex w-full items-center justify-between rounded-xl bg-cream px-3 py-2.5 font-mono text-base">
                {startCmd} {copied ? <Check className="size-4 text-safe" /> : <Copy className="size-4 text-muted" />}
              </button>
              <p className="mt-2 flex items-center gap-1.5 text-xs text-muted"><Loader2 className="size-3 animate-spin" /> Waiting for Start… (code works for 24 hours, once)</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
