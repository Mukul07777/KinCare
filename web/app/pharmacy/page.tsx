"use client";

import { RoleGate } from "@/components/RoleGate";
import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { BellRing, ClipboardCheck, Download, ExternalLink, FileSpreadsheet, History, Loader2, PackageX, RotateCcw, Store, Upload, Users, Volume2 } from "lucide-react";
import { Eyebrow, Heading } from "@/components/Heading";
import { CheckinQueue } from "@/components/CheckinQueue";
import { formatIST, formatMonth, getSales, notifyBuyers, putSales, speak, type Sale } from "@/lib/api";
import {
  auditCsv,
  checkInventory,
  EMPTY,
  loadState,
  parseCsv,
  saveState,
  STATUS_FLOW,
  type PharmacyState,
  type Task,
  type TaskStatus,
} from "@/lib/pharmacy";

const STAFF = ["Pharmacist on duty", "Store manager", "Inventory staff"];

function Pharmacy() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [state, setState] = useState<PharmacyState>(EMPTY);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [who, setWho] = useState(STAFF[0]);

  useEffect(() => {
    loadState().then(setState).catch((e) => setError(e.message));
  }, []);

  const commit = (next: PharmacyState) => {
    setState(next);
    saveState(next).catch(() => setError("Could not save to the server. Changes may be lost."));
  };

  const log = (s: PharmacyState, action: string): PharmacyState => ({
    ...s,
    audit: [{ at: new Date().toISOString(), who, action }, ...s.audit],
  });

  const runCheck = async (csv: string, label: string) => {
    setBusy(true);
    setError(null);
    try {
      const rows = parseCsv(csv);
      if (!rows.length) throw new Error("No stock rows found in the file.");
      const r = await checkInventory(rows);
      const tasks: Task[] = r.rows
        .filter((row) => row.matches.length)
        .map((row, i) => ({
          id: `${row.batch}-${i}`,
          row: { product: row.product, batch: row.batch, maker: row.maker, qty: row.qty },
          alert: row.matches[0].alert,
          level: row.matches[0].score.level,
          status: "open",
          assignee: STAFF[0],
          note: "",
        }));
      commit(log({ ...state, checkedAt: r.checked_at, total: r.total, tasks }, `Checked ${r.total} stock rows from ${label}: ${r.flagged} flagged`));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const loadSample = async () => runCheck(await (await fetch("/sample-inventory.csv")).text(), "sample inventory");

  const onFile = async (f?: File) => {
    if (f) runCheck(await f.text(), f.name);
  };

  const updateTask = (id: string, patch: Partial<Task>, action: string) =>
    commit(log({ ...state, tasks: state.tasks.map((t) => (t.id === id ? { ...t, ...patch } : t)) }, action));

  const exportReport = () => {
    const blob = new Blob([auditCsv(state)], { type: "text/csv" });
    const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(blob), download: "kincare-recall-report.csv" });
    a.click();
    commit(log(state, "Exported recall report"));
  };

  // ---- customer sales: who bought which batch ----
  const salesRef = useRef<HTMLInputElement>(null);
  const [sales, setSales] = useState<(Sale & { id: number })[]>([]);
  const [demoPhone, setDemoPhone] = useState("");
  const [sent, setSent] = useState<Record<string, { channel: string; customer: string; status: string; message: string; language: string }[]>>({});

  useEffect(() => {
    getSales().then(setSales).catch(() => {});
  }, []);

  const loadSales = async (csv: string, label: string) => {
    const lines = csv.split(/\r?\n/).filter((l) => l.trim());
    const head = lines[0].toLowerCase().split(",").map((h) => h.trim());
    const rows: Sale[] = lines.slice(1).map((l) => {
      const c = l.split(",").map((x) => x.trim());
      const get = (k: string) => c[head.indexOf(k)] || undefined;
      return { pharmacy: get("pharmacy"), city: get("city"), customer: get("customer"), phone: get("phone") || demoPhone || undefined,
               language: get("language") ?? "hi", product: get("product"), batch: get("batch") ?? "", sold_at: get("sold_at") };
    }).filter((r) => r.batch);
    try {
      await putSales(rows);
      setSales(await getSales());
      commit(log(state, `Loaded ${rows.length} customer sales from ${label}`));
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const notify = async (t: Task) => {
    try {
      const r = await notifyBuyers(t.row.batch);
      setSent((s) => ({ ...s, [t.id]: r.notifications }));
      commit(log(state, `Notified ${r.buyers} customer(s) who bought ${t.row.batch}`));
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const buyersOf = (batch: string) => sales.filter((s) => s.batch.replace(/[\s\-/.]/g, "").toUpperCase() === batch.replace(/[\s\-/.]/g, "").toUpperCase());

  const units = state.tasks.reduce((n, t) => n + t.row.qty, 0);
  const resolved = state.tasks.filter((t) => t.status === "resolved").length;

  return (
    <main className="blush mx-auto max-w-6xl px-4 pt-12 sm:px-6 sm:pt-16">
      <div className="flex flex-wrap items-end justify-between gap-6">
        <div>
          <Eyebrow>For pharmacies</Eyebrow>
          <Heading as="h1" lead="A recall desk" tail="for your store." className="mt-4 text-4xl sm:text-6xl" />
          <p className="mt-4 max-w-lg text-muted">
            Upload your stock export. KinCare flags batches named in official alerts and gives your staff a tracked workflow. Works alongside your billing software.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <input ref={fileRef} type="file" accept=".csv,text/csv" className="hidden" onChange={(e) => onFile(e.target.files?.[0])} />
          <button onClick={() => fileRef.current?.click()} disabled={busy} className="inline-flex items-center gap-2 rounded-full bg-brown px-5 py-3 text-sm font-medium text-paper transition hover:bg-brown-2 disabled:opacity-50">
            {busy ? <Loader2 className="size-4 animate-spin" /> : <Upload className="size-4" />} Upload stock CSV
          </button>
          <button onClick={loadSample} disabled={busy} className="inline-flex items-center gap-2 rounded-full border border-espresso/15 bg-paper px-5 py-3 text-sm font-medium transition hover:border-brown hover:text-brown disabled:opacity-50">
            <FileSpreadsheet className="size-4" /> Use sample inventory
          </button>
        </div>
      </div>

      {error && <p className="mt-6 rounded-2xl border border-danger/20 bg-danger/5 px-5 py-4 text-sm text-danger">{error}</p>}

      {!state.checkedAt ? (
        <div className="card mt-10 grid gap-8 rounded-[2rem] p-8 sm:p-12 md:grid-cols-[1fr_1.2fr] md:items-center">
          <div>
            <span className="grid size-16 place-items-center rounded-full bg-sand text-brown"><Store className="size-7" /></span>
            <p className="mt-5 text-2xl font-medium tracking-tight">No inventory checked yet</p>
            <p className="mt-2 text-sm text-muted">Any CSV with a batch column works. Product, manufacturer and quantity columns are picked up if present.</p>
            <a href="/sample-inventory.csv" download className="mt-4 inline-block text-sm font-medium text-brown underline">Download the CSV template</a>
          </div>
          <ol className="space-y-3 text-sm">
            {["Export stock from your billing software (Marg, GoFrugal, Excel…)", "Upload it here, nothing to install", "Flagged batches become review tasks for staff", "Every action is logged; export the report for your records"].map((s, i) => (
              <li key={s} className="flex items-start gap-3 rounded-2xl bg-cream/60 p-4">
                <span className="grid size-6 shrink-0 place-items-center rounded-full bg-brown text-xs font-semibold text-paper">{i + 1}</span>
                {s}
              </li>
            ))}
          </ol>
        </div>
      ) : (
        <>
          {/* Summary */}
          <div className="mt-10 grid grid-cols-2 gap-3 lg:grid-cols-4">
            {[
              { label: "Stock rows checked", v: state.total },
              { label: "Flagged batches", v: state.tasks.length, hot: state.tasks.length > 0 },
              { label: "Units affected", v: units },
              { label: "Tasks resolved", v: `${resolved}/${state.tasks.length}` },
            ].map((c) => (
              <div key={c.label} className={`card rounded-3xl p-5 ${c.hot ? "bg-danger text-paper" : ""}`}>
                <p className={`text-sm ${c.hot ? "text-paper/80" : "text-muted"}`}>{c.label}</p>
                <p className="mt-2 text-4xl font-medium tracking-tight">{c.v}</p>
              </div>
            ))}
          </div>

          <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm text-muted">
            <span>Last checked {formatIST(state.checkedAt)}</span>
            <div className="flex flex-wrap items-center gap-2">
              <label className="flex items-center gap-2">
                Acting as
                <select value={who} onChange={(e) => setWho(e.target.value)} className="rounded-full border border-line bg-paper px-3 py-1.5 text-espresso outline-none">
                  {STAFF.map((s) => <option key={s}>{s}</option>)}
                </select>
              </label>
              <button onClick={exportReport} className="inline-flex items-center gap-1.5 rounded-full border border-line bg-paper px-3 py-1.5 font-medium text-espresso transition hover:border-brown hover:text-brown">
                <Download className="size-3.5" /> Export report
              </button>
              <button onClick={() => commit(EMPTY)} className="inline-flex items-center gap-1.5 rounded-full border border-line bg-paper px-3 py-1.5 font-medium text-espresso transition hover:border-danger hover:text-danger">
                <RotateCcw className="size-3.5" /> Reset
              </button>
            </div>
          </div>

          <div className="mt-6 grid gap-5 lg:grid-cols-[1.6fr_1fr]">
            {/* Tasks */}
            <div className="space-y-3">
              <p className="flex items-center gap-2 font-medium"><ClipboardCheck className="size-4 text-brown" /> Review tasks</p>
              {state.tasks.length === 0 && (
                <div className="card rounded-3xl p-8 text-center text-muted">No stock batch matches a published alert as of this check.</div>
              )}
              <AnimatePresence>
                {state.tasks.map((t) => {
                  const step = STATUS_FLOW.findIndex((s) => s.id === t.status);
                  return (
                    <motion.div key={t.id} layout initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="card relative overflow-hidden rounded-3xl p-6">
                      <span className={`absolute inset-y-0 left-0 w-1.5 ${t.status === "resolved" ? "bg-safe" : "bg-danger"}`} />
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <p className="text-lg font-medium tracking-tight">{t.row.product || t.alert.product_name}</p>
                          <p className="font-mono text-sm text-muted">Batch {t.row.batch} · {t.row.qty} units{t.row.maker && ` · ${t.row.maker}`}</p>
                        </div>
                        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${t.alert.category === "spurious" ? "bg-danger/10 text-danger" : "bg-sand text-brown"}`}>
                          {t.alert.category === "spurious" ? "Spurious" : "NSQ"} · {formatMonth(t.alert.alert_month)}
                        </span>
                      </div>
                      <p className="mt-3 text-sm text-muted">
                        {t.alert.reason}.{t.level === "possible" && " Batch matches but manufacturer differs: verify the label."}{" "}
                        <a href={t.alert.alert_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-medium text-brown">Notice <ExternalLink className="size-3" /></a>
                      </p>

                      {/* Progress */}
                      <div className="mt-5 flex gap-1">
                        {STATUS_FLOW.map((s, i) => (
                          <div key={s.id} className={`h-1.5 flex-1 rounded-full ${i <= step ? (t.status === "resolved" ? "bg-safe" : "bg-brown") : "bg-sand"}`} />
                        ))}
                      </div>
                      <div className="mt-4 grid gap-2 sm:grid-cols-3">
                        <select
                          value={t.status}
                          onChange={(e) => {
                            const st = e.target.value as TaskStatus;
                            updateTask(t.id, { status: st }, `${t.row.product || t.row.batch} (${t.row.batch}) → ${STATUS_FLOW.find((s) => s.id === st)!.label}`);
                          }}
                          className="rounded-xl border border-line bg-cream/60 px-3 py-2 text-sm outline-none"
                        >
                          {STATUS_FLOW.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
                        </select>
                        <select
                          value={t.assignee}
                          onChange={(e) => updateTask(t.id, { assignee: e.target.value }, `Assigned ${t.row.batch} to ${e.target.value}`)}
                          className="rounded-xl border border-line bg-cream/60 px-3 py-2 text-sm outline-none"
                        >
                          {STAFF.map((s) => <option key={s}>{s}</option>)}
                        </select>
                        <input
                          defaultValue={t.note}
                          placeholder="Add a note…"
                          onBlur={(e) => e.target.value !== t.note && updateTask(t.id, { note: e.target.value }, `Note on ${t.row.batch}: “${e.target.value}”`)}
                          className="rounded-xl border border-line bg-cream/60 px-3 py-2 text-sm outline-none placeholder:text-clay"
                        />
                      </div>
                      {(() => {
                        const buyers = buyersOf(t.row.batch);
                        if (!buyers.length) return <p className="mt-3 text-xs text-muted">No recorded customer sales for this batch.</p>;
                        return (
                          <div className="mt-4 rounded-2xl bg-cream/60 p-3">
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <p className="text-sm"><b>{buyers.length}</b> customer{buyers.length > 1 ? "s" : ""} bought this batch: {buyers.map((b) => b.customer).join(", ")}</p>
                              <button onClick={() => notify(t)} className="inline-flex items-center gap-1.5 rounded-full bg-danger px-3.5 py-1.5 text-xs font-medium text-paper transition hover:brightness-110">
                                <BellRing className="size-3.5" /> Notify customers
                              </button>
                            </div>
                            {sent[t.id] && (
                              <div className="mt-3 space-y-2">
                                {sent[t.id].length === 0 && <p className="text-xs text-muted">No customer has a phone number on record.</p>}
                                {sent[t.id].filter((n) => n.channel === "whatsapp").map((n, i) => (
                                  <div key={i} className="flex items-start gap-2 text-xs">
                                    <span className="mt-0.5 rounded-full bg-safe/15 px-2 py-0.5 font-medium text-safe">{n.status === "sent" ? "Sent" : "Outbox"}</span>
                                    <p className="whitespace-pre-line text-muted"><b className="text-espresso">{n.customer}</b> · WhatsApp + voice call ({n.language === "hi" ? "Hindi" : "English"})</p>
                                    <button onClick={() => speak(sent[t.id].find((x) => x.channel === "voice" && x.customer === n.customer)?.message ?? "", n.language)} className="ml-auto shrink-0 rounded-full border border-line px-2 py-0.5 hover:border-brown"><Volume2 className="inline size-3" /> Hear call</button>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        );
                      })()}
                    </motion.div>
                  );
                })}
              </AnimatePresence>
            </div>

            {/* Audit log */}
            <div className="space-y-4 lg:sticky lg:top-24 lg:h-fit">
            <div className="card rounded-3xl p-5">
              <p className="flex items-center gap-2 font-medium"><Users className="size-4 text-brown" /> Customer sales</p>
              <p className="mt-1 text-xs text-muted">Who bought which batch, from your billing export. Used to reach customers when a batch is flagged.</p>
              <p className="mt-3 text-sm"><b>{sales.length}</b> sales on record{sales.filter((s) => s.phone).length ? ` · ${sales.filter((s) => s.phone).length} with phone` : ""}</p>
              <input value={demoPhone} onChange={(e) => setDemoPhone(e.target.value)} placeholder="Your phone, for the demo customers" className="mt-3 w-full rounded-xl border border-line bg-cream/60 px-3 py-2 text-sm outline-none focus:border-brown/40" />
              <input ref={salesRef} type="file" accept=".csv" className="hidden" onChange={async (e) => { const f = e.target.files?.[0]; if (f) loadSales(await f.text(), f.name); }} />
              <div className="mt-2 flex gap-2">
                <button onClick={async () => loadSales(await (await fetch("/sample-sales.csv")).text(), "sample sales")} className="flex-1 rounded-xl bg-sand px-3 py-2 text-xs font-medium text-brown hover:bg-clay/60">Use sample sales</button>
                <button onClick={() => salesRef.current?.click()} className="flex-1 rounded-xl border border-line px-3 py-2 text-xs font-medium hover:border-brown">Upload CSV</button>
              </div>
            </div>
            <div className="card h-fit rounded-3xl p-5">
              <p className="flex items-center gap-2 font-medium"><History className="size-4 text-brown" /> Audit trail</p>
              <p className="mt-1 text-xs text-muted">Every check and action, with who and when.</p>
              <div className="mt-4 max-h-[460px] space-y-3 overflow-y-auto pr-1">
                {state.audit.map((a, i) => (
                  <div key={i} className="border-l-2 border-sand pl-3">
                    <p className="text-sm">{a.action}</p>
                    <p className="text-[11px] text-muted">{a.who} · {formatIST(a.at)}</p>
                  </div>
                ))}
              </div>
            </div>
            </div>
          </div>

          <p className="mt-6 flex items-center gap-2 text-xs text-muted">
            <PackageX className="size-3.5" /> KinCare flags batches named in published alerts. Follow your official recall procedure for any action on stock.
          </p>
        </>
      )}
      <CheckinQueue />
    </main>
  );
}

export default function PharmacyPage() {
  return <RoleGate perm="sales.manage" role="pharmacist" what="Pharmacy recall desk"><Pharmacy /></RoleGate>;
}
