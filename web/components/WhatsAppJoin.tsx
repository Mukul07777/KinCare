"use client";

import { useEffect, useState } from "react";
import { MessageCircle } from "lucide-react";
import { getWhatsAppInfo } from "@/lib/api";

/** "Say hi to KinCare" link. The first message opens WhatsApp's free 24-hour window; each "1" reply keeps it open. */
export function WhatsAppJoin({ compact = false }: { compact?: boolean }) {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => { getWhatsAppInfo().then((i) => setUrl(i.join_url)).catch(() => {}); }, []);
  if (!url) return null;

  if (compact) {
    return (
      <a href={url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 rounded-full bg-[#25d366] px-4 py-2.5 text-sm font-medium text-white hover:brightness-95">
        <MessageCircle className="size-4" /> Say hi to KinCare on WhatsApp
      </a>
    );
  }
  return (
    <div className="rounded-3xl bg-[#e7f8ee] p-5 text-sm">
      <p className="flex items-center gap-2 font-medium text-[#0b6b3a]"><MessageCircle className="size-4" /> Reminders on WhatsApp</p>
      <p className="mt-1 text-[#2f5d45]">Tap, then press send. Reply <b>1</b> after each dose and KinCare ticks it for you. Send any batch number to check it.</p>
      <a href={url} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-2 rounded-full bg-[#25d366] px-4 py-2 font-medium text-white hover:brightness-95">
        <MessageCircle className="size-4" /> Start KinCare on WhatsApp
      </a>
    </div>
  );
}
