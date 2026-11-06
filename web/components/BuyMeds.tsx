"use client";

import { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, BellRing, Check, Loader2, ShoppingBag } from "lucide-react";
import { getPlans, recordPurchase, type Plan, type PurchaseResult } from "@/lib/api";

type Med = Plan["medicines"][number] & { member: string };

/** Prescribed medicines the patient still has to buy. Recording a purchase checks the batch and sends "take it now" on WhatsApp. */
export function BuyMeds({ onBought }: { onBought: () => void }) {
  const [meds, setMeds] = useState<Med[]>([]);
  const [open, setOpen] = useState<number | null>(null);

  const load = useCallback(() => getPlans().then((ps) => setMeds(ps.flatMap((p) => p.medicines.map((m) => ({ ...m, member: p.member }))))).catch(() => {}), []);
  useEffect(() => { load(); }, [load]);

  if (!meds.length) return null;
  const left = meds.filter((m) => !m.bought_at).length;
  // Bought ones open as a refill form.

  return (
    <div className="card rounded-3xl p-5">
      <p className="flex items-center gap-2 font-medium"><ShoppingBag className="size-4 text-brown" /> Buy your medicines</p>
      <p className="mt-1 text-sm text-muted">{left ? `${left} still to buy. Enter the batch from the strip when you buy it.` : "All prescribed medicines bought."}</p>
      <div className="mt-4 space-y-2">
        {meds.map((m) => (
          <div key={m.id} className="rounded-2xl border border-line bg-cream/50">
            <button onClick={() => setOpen(open === m.id ? null : m.id)} className="flex w-full items-center gap-3 px-4 py-3 text-left">
              <div className="flex-1">
                <p className="font-medium">{m.name} <span className="font-normal text-muted">{m.strength}</span></p>
                <p className="text-xs text-muted">{m.member}{m.batch && m.bought_at ? ` · batch ${m.batch}` : ""}</p>
              </div>
              {m.bought_at
                ? <span className="inline-flex items-center gap-1 rounded-full bg-safe/15 px-3 py-1 text-xs font-medium text-safe"><Check className="size-3.5" /> {open === m.id ? "Bought more" : "Bought"}</span>
                : <span className="rounded-full bg-brown px-3 py-1 text-xs font-medium text-paper">I bought it</span>}
            </button>
            <AnimatePresence>
              {open === m.id && (
                <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                  <PurchaseForm med={m} onDone={() => { load(); onBought(); }} />
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        ))}
      </div>
    </div>
  );
}

function PurchaseForm({ med, onDone }: { med: Med; onDone: () => void }) {
  const [f, setF] = useState({ batch: "", maker: "", expiry: "", pharmacy: "", phone: "", language: "hi", qty: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [res, setRes] = useState<PurchaseResult | null>(null);

  useEffect(() => { try { setF((x) => ({ ...x, phone: localStorage.getItem("kincare_phone") || "" })); } catch {} }, []);

  const submit = async () => {
    if (!f.batch.trim()) return setError("Batch number is printed on the strip, usually after “B.No.”");
    setBusy(true);
    setError(null);
    try {
      try { if (f.phone) localStorage.setItem("kincare_phone", f.phone); } catch {}
      const qty = f.qty ? Number(f.qty) : undefined;
      if (qty !== undefined && !(qty > 0 && qty <= 1000)) throw new Error("Tablets bought should be a number, e.g. 10 or 15");
      setRes(await recordPurchase({ med_id: med.id, ...f, phone: f.phone || undefined, qty }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  if (res) {
    const flagged = res.verdict === "alert_found";
    return (
      <div className={`mx-3 mb-3 rounded-2xl p-4 text-sm ${flagged ? "bg-danger/10 text-danger" : "bg-safe/10"}`}>
        <p className="flex items-center gap-2 font-medium">
          {flagged ? <AlertTriangle className="size-4" /> : <BellRing className="size-4 text-safe" />}
          {flagged ? "This batch is on a regulator alert list. Don’t take it; speak to your pharmacist." : res.due_now ? "Take your dose now." : res.next_time ? `Next dose at ${res.next_time}.` : "No more doses today."}
        </p>
        <p className="mt-1 text-muted">{waNote(res)}</p>
        <button onClick={onDone} className="mt-3 rounded-full bg-brown px-4 py-1.5 text-xs font-medium text-paper">Done</button>
      </div>
    );
  }

  const field = (k: keyof typeof f, label: string, ph: string) => (
    <label className="block">
      <span className="text-xs font-medium text-muted">{label}</span>
      <input value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })} placeholder={ph} className="mt-1 w-full rounded-xl border border-line bg-paper px-3 py-2 text-sm outline-none focus:border-brown/40" />
    </label>
  );

  return (
    <div className="space-y-3 px-4 pb-4">
      <div className="grid grid-cols-2 gap-2">
        {field("batch", "Batch no. *", "e.g. PCM2304")}
        {field("expiry", "Expiry", "e.g. 08/2027")}
        {field("maker", "Manufacturer", "From the strip")}
        {field("pharmacy", "Pharmacy", "Where you bought it")}
        {field("qty", "Tablets bought", "Blank = one strip")}
      </div>
      {med.bought_at && <p className="text-xs text-muted">Refill: tablets still at home are added to these.</p>}
      <div className="grid grid-cols-[1fr_auto] gap-2">
        {field("phone", "WhatsApp number", "98xxxxxxxx")}
        <label className="block">
          <span className="text-xs font-medium text-muted">Language</span>
          <select value={f.language} onChange={(e) => setF({ ...f, language: e.target.value })} className="mt-1 w-full rounded-xl border border-line bg-paper px-3 py-2 text-sm">
            <option value="hi">हिंदी</option>
            <option value="en">English</option>
          </select>
        </label>
      </div>
      {error && <p className="text-xs text-danger">{error}</p>}
      <button onClick={submit} disabled={busy} className="inline-flex w-full items-center justify-center gap-2 rounded-full bg-brown px-4 py-2.5 text-sm font-medium text-paper hover:bg-brown-2">
        {busy && <Loader2 className="size-4 animate-spin" />} Check batch & set reminders
      </button>
    </div>
  );
}

// What happens on WhatsApp after a purchase, in plain words. Recall alerts are free on every plan.
function waNote(res: PurchaseResult) {
  const w = res.whatsapp ?? "";
  if (res.verdict === "alert_found") return res.message_status === "sent" ? "The alert was sent to your WhatsApp too." : "Show this screen to your pharmacist.";
  if (w.startsWith("sponsored:")) return `WhatsApp reminders are free for you, covered by ${w.slice(10)}. Reply 1 after each dose.`;
  if (w === "upgrade") return "Dose reminders will come as phone notifications (free). WhatsApp reminders are in Basic, ₹29/month. Recall alerts always reach your WhatsApp free.";
  if (res.message_status === "sent") return "Sent to your WhatsApp. You’ll get a reminder at every dose: reply 1 once taken.";
  return "Reminders are set. Turn on notifications to get them on this phone.";
}
