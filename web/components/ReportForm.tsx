"use client";

import { useEffect, useState } from "react";
import { Check, Megaphone } from "lucide-react";
import { getSignals, sendReport } from "@/lib/api";

type Sym = { key: string; en: string; hi: string };

// "I felt something was wrong after this batch." Feeds Early Signal. Never gives medical advice.
export function ReportForm({ batch = "", brand = "", maker = "", compact = false, onSent }: { batch?: string; brand?: string; maker?: string; compact?: boolean; onSent?: () => void }) {
  const [syms, setSyms] = useState<Sym[]>([]);
  const [f, setF] = useState({ batch, brand, maker, city: "", onset: "" });
  const [picked, setPicked] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getSignals().then((s) => setSyms(s.symptoms)).catch(() => {});
  }, []);

  const toggle = (k: string) => setPicked((p) => (p.includes(k) ? p.filter((x) => x !== k) : [...p, k]));
  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      const r = await sendReport({ batch: f.batch, brand: f.brand || undefined, maker: f.maker || undefined, city: f.city || undefined, symptoms: picked, onset_days: f.onset ? Number(f.onset) : undefined });
      setDone(r.reports_for_batch);
      onSent?.();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  if (done !== null)
    return (
      <div className="rounded-2xl border border-line bg-paper p-5 text-sm">
        <p className="flex items-center gap-2 font-medium"><Check className="size-4 text-brown" /> Report saved, thank you.</p>
        <p className="mt-1 text-muted">{done} {done === 1 ? "person has" : "people have"} reported batch {f.batch.toUpperCase()}. Please also show your pharmacist or doctor today.</p>
      </div>
    );

  const input = "w-full rounded-xl border border-line bg-cream/60 px-3 py-2 text-sm outline-none focus:border-brown/40";
  return (
    <div className={compact ? "" : "card rounded-3xl p-6"}>
      {!compact && (
        <p className="flex items-center gap-2 font-medium"><Megaphone className="size-4 text-brown" /> Felt something wrong after a medicine?</p>
      )}
      <div className="mt-3 grid gap-2 sm:grid-cols-2">
        <input className={`${input} font-mono uppercase`} placeholder="Batch number *" value={f.batch} onChange={(e) => setF({ ...f, batch: e.target.value })} />
        <input className={input} placeholder="Brand" value={f.brand} onChange={(e) => setF({ ...f, brand: e.target.value })} />
        <input className={input} placeholder="City" value={f.city} onChange={(e) => setF({ ...f, city: e.target.value })} />
        <input className={input} type="number" min={0} max={90} placeholder="Started how many days after?" value={f.onset} onChange={(e) => setF({ ...f, onset: e.target.value })} />
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {syms.map((s) => (
          <button key={s.key} onClick={() => toggle(s.key)} className={`rounded-full border px-3 py-1.5 text-xs transition ${picked.includes(s.key) ? "border-brown bg-brown text-paper" : "border-line bg-paper hover:border-brown/40"}`}>
            {s.en} <span className="opacity-60">· {s.hi}</span>
          </button>
        ))}
      </div>
      {error && <p className="mt-3 text-sm text-danger">{error}</p>}
      <button onClick={submit} disabled={busy || !f.batch || !picked.length} className="mt-4 rounded-full bg-brown px-5 py-2.5 text-sm font-medium text-paper transition hover:bg-mocha disabled:opacity-40">
        {busy ? "Sending…" : "Send anonymous report"}
      </button>
      <p className="mt-2 text-xs text-muted">Anonymous. Only batch, symptoms and city are stored. Chest pain, fainting or breathlessness: go to a doctor now.</p>
    </div>
  );
}
