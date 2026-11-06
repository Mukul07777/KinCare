"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Camera, CheckCheck, ImageUp, Loader2, MessageCircle, Send } from "lucide-react";
import { Eyebrow, Heading } from "@/components/Heading";
import { waSimulatePhoto, waSimulateText } from "@/lib/api";

type Msg = { id: number; me: boolean; text?: string; img?: string; at: string };

// Test strips in public/test-strips: real flagged batches (and one clean one), labelled "DEMO PRINT".
const STRIPS = [
  { file: "namik-mr.png", label: "Namik-MR strip" },
  { file: "chymoral-forte.png", label: "Chymoral Forte strip" },
  { file: "amlodipine-clean.png", label: "Clean strip" },
];
const SAY = ["hi", "1", "AT25-0938A"];

const time = () => new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", hour12: false });

/** WhatsApp's *bold* and line breaks. */
function Rich({ text }: { text: string }) {
  return (
    <>
      {text.split("\n").map((line, i) => (
        <p key={i} className="min-h-[1em]">
          {line.split(/(\*[^*]+\*)/g).map((part, j) => (part.startsWith("*") && part.endsWith("*") && part.length > 2 ? <b key={j}>{part.slice(1, -1)}</b> : part))}
        </p>
      ))}
    </>
  );
}

export default function WhatsAppPage() {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const nextId = useRef(1);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [msgs, busy]);

  const add = (m: Omit<Msg, "id" | "at">) => setMsgs((x) => [...x, { ...m, id: nextId.current++, at: time() }]);

  const sendText = async (t: string) => {
    const body = t.trim();
    if (!body || busy) return;
    setText("");
    add({ me: true, text: body });
    setBusy(true);
    try { add({ me: false, text: (await waSimulateText(body)).reply }); }
    catch (e) { add({ me: false, text: `⚠️ ${(e as Error).message}` }); }
    finally { setBusy(false); }
  };

  const sendPhoto = async (blob: Blob) => {
    if (busy) return;
    add({ me: true, img: URL.createObjectURL(blob) });
    setBusy(true);
    try { add({ me: false, text: (await waSimulatePhoto(blob)).reply }); }
    catch (e) { add({ me: false, text: `⚠️ ${(e as Error).message}` }); }
    finally { setBusy(false); }
  };

  const sendStrip = async (file: string) => sendPhoto(await (await fetch(`/test-strips/${file}`)).blob());

  return (
    <main className="blush mx-auto max-w-6xl px-4 pb-20 pt-12 sm:px-6 sm:pt-16">
      <div className="grid items-start gap-10 lg:grid-cols-[1fr_420px]">
        <div>
          <Eyebrow>KinCare on WhatsApp</Eyebrow>
          <Heading as="h1" lead="No app." tail="Just send a photo." className="mt-4 text-4xl sm:text-6xl" />
          <p className="mt-4 max-w-xl text-muted">
            Most families will never install a health app, but everyone has WhatsApp. Photograph the back of a strip and send it to KinCare.
            The batch is read, checked against every CDSCO and state alert, and the answer comes back in Hindi or English.
          </p>
          <div className="mt-8 grid gap-3 sm:grid-cols-3">
            {[
              ["📷", "Send a strip photo", "Batch, brand and expiry are read from the photo"],
              ["⚠️", "Get the verdict", "Flagged, clean, or expired, with what to do next"],
              ["✅", "Reply 1 after a dose", "Ticks the reminder and keeps the chat free"],
            ].map(([icon, t, s]) => (
              <div key={t} className="card rounded-3xl p-5">
                <p className="text-2xl">{icon}</p>
                <p className="mt-2 font-medium">{t}</p>
                <p className="mt-1 text-sm text-muted">{s}</p>
              </div>
            ))}
          </div>
          <div className="clinical mt-6 rounded-3xl p-5 text-sm">
            <p className="font-medium text-teal-2">Try it on the phone →</p>
            <p className="mt-1 text-muted">Tap a test strip to send its photo, or upload your own. Then try “1” or type a batch number.</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {STRIPS.map((s) => (
                <button key={s.file} onClick={() => sendStrip(s.file)} disabled={busy}
                  className="inline-flex items-center gap-1.5 rounded-full bg-paper px-3 py-1.5 text-xs font-medium text-teal-2 shadow-sm disabled:opacity-50">
                  <Camera className="size-3.5" /> {s.label}
                </button>
              ))}
            </div>
          </div>
          <p className="mt-6 text-[11px] text-muted">
            This phone runs the same bot code as KinCare&apos;s real WhatsApp number (Meta Cloud API); here nothing is sent to anyone.
            Test strips are demo prints of real flagged batches.
          </p>
        </div>

        {/* Phone */}
        <div className="mx-auto w-full max-w-[400px] rounded-[3rem] border-[10px] border-espresso bg-espresso shadow-2xl">
          <div className="overflow-hidden rounded-[2.3rem] bg-[#efe7dd]">
            <div className="flex items-center gap-3 bg-[#075e54] px-4 py-3 text-white">
              <span className="grid size-9 place-items-center rounded-full bg-white/15"><MessageCircle className="size-5" /></span>
              <div className="leading-tight">
                <p className="font-semibold">KinCare</p>
                <p className="text-[11px] text-white/70">{busy ? "typing…" : "Business account"}</p>
              </div>
            </div>
            <div className="h-[520px] space-y-2 overflow-y-auto px-3 py-4 text-[14px]">
              {msgs.length === 0 && <p className="mx-auto mt-40 w-56 rounded-xl bg-[#fff5c4] px-3 py-2 text-center text-xs text-[#54471f]">Send a strip photo or say hi to start.</p>}
              {msgs.map((m) => (
                <motion.div key={m.id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
                  className={`max-w-[82%] rounded-xl px-2.5 py-1.5 shadow-sm ${m.me ? "ml-auto rounded-tr-sm bg-[#d9fdd3]" : "rounded-tl-sm bg-white"}`}>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  {m.img && <img src={m.img} alt="Strip photo sent" className="mb-1 max-h-44 rounded-lg object-cover" />}
                  {m.text && <div className="whitespace-pre-wrap break-words text-[#111b21]"><Rich text={m.text} /></div>}
                  <p className="mt-0.5 flex items-center justify-end gap-1 text-[10px] text-[#667781]">{m.at}{m.me && <CheckCheck className="size-3.5 text-[#53bdeb]" />}</p>
                </motion.div>
              ))}
              {busy && <div className="w-16 rounded-xl bg-white px-3 py-2 shadow-sm"><Loader2 className="size-4 animate-spin text-[#667781]" /></div>}
              <div ref={endRef} />
            </div>
            <div className="flex flex-wrap gap-1.5 px-3 pb-2">
              {SAY.map((s) => <button key={s} onClick={() => sendText(s)} disabled={busy} className="rounded-full bg-white px-3 py-1 text-xs text-[#075e54] shadow-sm disabled:opacity-50">{s}</button>)}
            </div>
            <div className="flex items-center gap-2 bg-[#f0f2f5] px-3 py-2.5">
              <input ref={fileRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) sendPhoto(f); e.target.value = ""; }} />
              <button onClick={() => fileRef.current?.click()} disabled={busy} aria-label="Send a photo" className="grid size-10 place-items-center rounded-full text-[#54656f] hover:bg-black/5"><ImageUp className="size-5" /></button>
              <input value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === "Enter" && sendText(text)} placeholder="Message"
                className="min-w-0 flex-1 rounded-full bg-white px-4 py-2.5 text-sm outline-none" />
              <button onClick={() => sendText(text)} disabled={busy || !text.trim()} aria-label="Send" className="grid size-10 place-items-center rounded-full bg-[#00a884] text-white disabled:opacity-50"><Send className="size-4" /></button>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
