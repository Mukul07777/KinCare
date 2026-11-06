"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertTriangle, Bot, Check, CheckCircle2, Clock, FileText, Home, ListChecks, Loader2, MessagesSquare, Pill, Play,
  RotateCcw, ScanLine, ShieldCheck, Stethoscope, Store, Users, Waypoints,
} from "lucide-react";
import { Eyebrow, Heading } from "@/components/Heading";
import { formatMonth, getSwitchNetwork, type NetFlagged, type NetOption, type SwitchNetwork } from "@/lib/api";

type Approval = { option: NetOption; pharmacist: boolean; doctor: boolean };
type Msg = { who: string; kind: "human" | "agent" | "pharmacist" | "doctor"; text: string };

const AGENT_ICON: Record<string, typeof Bot> = {
  "kincare-recall-watcher": Waypoints, "kincare-scan": ScanLine, "kincare-pharmacist": Pill, "kincare-dose": Clock,
};
const short = (name: string) => name.split(/\s+/).slice(0, 2).join(" ");
const now = () => new Date().toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

export default function NetworkPage() {
  const [net, setNet] = useState<SwitchNetwork | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [approvals, setApprovals] = useState<Record<string, Approval>>({});
  const [decisions, setDecisions] = useState<{ family: string; text: string; fresh?: boolean }[]>([]);
  const [tasks, setTasks] = useState<{ family: string; text: string; done: boolean; fresh?: boolean }[]>([]);
  const [family, setFamily] = useState<string>("Sharma");

  useEffect(() => {
    // The documents start empty: every approval on this page writes its own lines, so the record visibly
    // grows from the decisions made here (the terminal demo's documents stay in switch/demo_out).
    getSwitchNetwork().then((n) => {
      setNet(n);
      setFamily(n.families.find((f) => f.default)?.name ?? n.families[0]?.name ?? "");
    }).catch((e) => setError((e as Error).message));
  }, []);

  const log = (b: NetFlagged, a: Approval) => {
    const by = `${net?.pharmacist || "the pharmacist"}${b.doctor.required ? " + the family's doctor" : ""}`;
    setDecisions((d) => [
      ...b.holders.map((h) => ({ family: h.family, fresh: true,
        text: `${now()} | ${h.person} | ${b.brand} batch ${b.batch} (CDSCO ${b.alert.category.toUpperCase()}) -> ${a.option.name} | approved by ${by}` })),
      ...d,
    ]);
    setTasks((t) => [
      ...b.holders.map((h) => ({ family: h.family, done: false, fresh: true,
        text: `${h.caregiver || "Caregiver"}: buy ${short(a.option.name)} for ${h.person}; keep the old strip for return` })),
      ...t,
    ]);
  };

  const approve = (b: NetFlagged, option: NetOption, who: "pharmacist" | "doctor") => {
    const prev = approvals[b.batch];
    const cur = prev?.option.id === option.id ? prev : { option, pharmacist: false, doctor: false };
    const next = { ...cur, [who]: true };
    const isDone = (a: Approval) => a.pharmacist && (!b.doctor.required || a.doctor);
    setApprovals((s) => ({ ...s, [b.batch]: next }));
    if (isDone(next) && !isDone(cur)) log(b, next);
  };

  const reset = () => { setApprovals({}); setDecisions([]); setTasks([]); };

  if (error) return <Shell><p className="rounded-2xl border border-line bg-paper p-6 text-danger">Couldn&apos;t load the care network: {error}. Is the KinCare API running?</p></Shell>;
  if (!net) return <Shell><div className="flex items-center gap-2 text-muted"><Loader2 className="size-4 animate-spin" /> Checking every family&apos;s batches against CDSCO…</div></Shell>;

  const homes = new Set(net.flagged.flatMap((b) => b.holders.map((h) => `${h.family}|${h.person}`))).size;

  return (
    <Shell>
      {/* Hero */}
      <section className="grid gap-8 lg:grid-cols-[1.3fr_1fr] lg:items-end">
        <div>
          <Eyebrow>Built on Switch · people and agents in one room</Eyebrow>
          <Heading as="h1" lead="One recall reaches" tail="every home, and a human decides." className="mt-4 text-4xl sm:text-5xl" />
          <p className="mt-4 max-w-xl text-brown-2/80">
            Each family&apos;s Telegram group is a Switch room. {net.pharmacy || "The pharmacy"}&apos;s Pharmacy Desk is linked to all of them.
            Four agents do the legwork; the pharmacist, and the doctor for critical medicines, approve. Families never see each other.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-3">
          <Stat n={net.checked} label="batches checked" />
          <Stat n={net.flagged.length} label="recalls found" tone="danger" />
          <Stat n={homes} label="people affected" tone="warn" />
        </div>
      </section>

      {/* Agents */}
      <section className="mt-12">
        <h2 className="mb-4 flex items-center gap-2 text-sm font-medium uppercase tracking-wider text-muted"><Bot className="size-4" /> The agents in every room</h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {net.agents.map((a, i) => {
            const Icon = AGENT_ICON[a.name] ?? Bot;
            const custom = a.kind.startsWith("Custom");
            return (
              <motion.div key={a.name} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.06 }}
                className="rounded-2xl border border-line bg-paper p-4">
                <div className="flex items-center justify-between">
                  <span className="grid size-9 place-items-center rounded-xl bg-mint text-teal"><Icon className="size-4" /></span>
                  <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${custom ? "bg-warn-soft text-warn" : "bg-sand text-brown"}`}>
                    {custom ? "Switch protocol" : "Claude Code"}
                  </span>
                </div>
                <p className="mt-3 font-medium">@{a.name}</p>
                <p className="mt-1 text-sm text-brown-2/75">{a.job}</p>
              </motion.div>
            );
          })}
        </div>
      </section>

      {/* Pharmacy desk + family rooms */}
      <section className="mt-12 grid gap-6 lg:grid-cols-[1.35fr_1fr]">
        <div>
          <RoomTitle icon={Store} title={`${net.pharmacy || "Pharmacy"} · Pharmacy Desk`} sub="Linked to every family room. Only this room sees the whole list." />
          <div className="space-y-4">
            {net.flagged.map((b) => <Recall key={b.batch} b={b} approval={approvals[b.batch]} onApprove={approve} pharmacist={net.pharmacist} />)}
            {!net.flagged.length && <p className="rounded-2xl border border-line bg-paper p-6 text-safe">No family holds a flagged batch right now.</p>}
          </div>
        </div>
        <div>
          <RoomTitle icon={Home} title="Family rooms" sub="Each family's own Telegram group, with its own record." />
          <div className="space-y-3">
            {net.families.map((f) => {
              const flagged = f.medicines.filter((m) => m.flagged);
              const resolved = flagged.every((m) => { const b = net.flagged.find((x) => x.batch.toUpperCase().replace(/[^A-Z0-9]/g, "") === m.batch.toUpperCase().replace(/[^A-Z0-9]/g, "")); const a = b && approvals[b.batch]; return a && a.pharmacist && (!b.doctor.required || a.doctor); });
              return (
                <button key={f.name} onClick={() => setFamily(f.name)}
                  className={`w-full rounded-2xl border p-4 text-left transition ${family === f.name ? "border-teal bg-mint/50" : "border-line bg-paper hover:border-clay"}`}>
                  <div className="flex items-center justify-between">
                    <p className="font-medium">{f.name} Family Care</p>
                    {flagged.length ? (
                      resolved ? <Badge tone="safe" icon={CheckCircle2}>resolved</Badge> : <Badge tone="danger" icon={AlertTriangle}>{flagged.length} flagged</Badge>
                    ) : <Badge tone="safe" icon={ShieldCheck}>all clear</Badge>}
                  </div>
                  <p className="mt-1 text-xs text-muted">caregiver {f.caregiver || "—"}</p>
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {f.medicines.map((m) => (
                      <span key={m.person + m.batch} className={`rounded-full px-2 py-0.5 text-xs ${m.flagged ? "bg-danger/10 text-danger" : "bg-sand text-brown-2"}`}>
                        {m.person}: {m.brand}
                      </span>
                    ))}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </section>

      {/* Chat replay + documents */}
      <section className="mt-12 grid gap-6 lg:grid-cols-[1fr_1.1fr]">
        <ChatReplay key={family + JSON.stringify(approvals)} net={net} family={family} approvals={approvals} />
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="flex items-center gap-2 text-sm font-medium uppercase tracking-wider text-muted"><FileText className="size-4" /> Room documents</h2>
            <button onClick={reset} className="inline-flex items-center gap-1 text-xs text-muted hover:text-brown"><RotateCcw className="size-3" /> reset</button>
          </div>
          <Doc title="KinCare Decisions" icon={ShieldCheck} empty="No decision yet. Approve a replacement on the Pharmacy Desk.">
            {decisions.map((d, i) => (
              <Line key={d.text + i} fresh={d.fresh}><span className="mr-2 rounded bg-sand px-1.5 py-0.5 text-[11px] text-brown">{d.family}</span>{d.text}</Line>
            ))}
          </Doc>
          <Doc title="KinCare Tasks" icon={ListChecks} empty="No open tasks.">
            {tasks.map((t, i) => (
              <Line key={t.text + i} fresh={t.fresh}>
                <button onClick={() => setTasks((all) => all.map((x, j) => (j === i ? { ...x, done: !x.done } : x)))}
                  className={`mr-2 inline-grid size-4 place-items-center rounded border align-[-3px] ${t.done ? "border-safe bg-safe text-white" : "border-clay"}`}>
                  {t.done && <Check className="size-3" />}
                </button>
                <span className="mr-2 rounded bg-sand px-1.5 py-0.5 text-[11px] text-brown">{t.family}</span>
                <span className={t.done ? "text-muted line-through" : ""}>{t.text}</span>
              </Line>
            ))}
          </Doc>
          <p className="text-xs text-muted">
            Real: the CDSCO alerts, OCR and medicine data. Simulated: the families, the pharmacist and the doctor.
            In Switch these documents live in each room, so everyone reads the same record.
          </p>
        </div>
      </section>
    </Shell>
  );
}

function Recall({ b, approval, onApprove, pharmacist }: {
  b: NetFlagged; approval?: Approval; pharmacist: string;
  onApprove: (b: NetFlagged, o: NetOption, who: "pharmacist" | "doctor") => void;
}) {
  const done = approval && approval.pharmacist && (!b.doctor.required || approval.doctor);
  return (
    <motion.article layout className={`rounded-2xl border bg-paper p-5 ${done ? "border-safe/40" : "border-danger/30"}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-danger">
            <AlertTriangle className="size-3.5" /> CDSCO {b.alert.category === "nsq" ? "Not of Standard Quality" : "spurious"} · {formatMonth(b.alert.alert_month)}
          </p>
          <p className="mt-1 text-xl font-medium">{b.brand} <span className="font-mono text-base text-brown">{b.batch}</span></p>
          <p className="mt-1 text-sm text-brown-2/75">{b.alert.reason}</p>
        </div>
        {b.doctor.required && <Badge tone="warn" icon={Stethoscope}>doctor must approve</Badge>}
      </div>

      <div className="mt-4">
        <p className="mb-2 text-xs font-medium text-muted">Blast radius: {b.holders.length} home{b.holders.length > 1 ? "s" : ""}, earliest dose first</p>
        <div className="flex flex-wrap gap-2">
          {b.holders.map((h, i) => (
            <motion.span key={h.family + h.person} initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ delay: i * 0.08 }}
              className={`inline-flex items-center gap-1.5 rounded-xl border px-2.5 py-1.5 text-sm ${done ? "border-safe/30 bg-safe/5" : "border-line bg-cream"}`}>
              <Users className="size-3.5 text-muted" /> {h.family}: {h.person}
              <span className="font-mono text-xs text-muted">{h.times.join(", ")}</span>
            </motion.span>
          ))}
        </div>
      </div>

      {b.doctor.required && <p className="mt-3 rounded-xl bg-warn-soft px-3 py-2 text-sm text-warn">🩺 {b.doctor.why}: a different maker&apos;s tablet can need a dose check.</p>}

      <div className="mt-4">
        <p className="mb-2 text-xs font-medium text-muted">{b.note}</p>
        {b.options.length ? (
          <div className="space-y-2">
            {b.options.map((o, i) => {
              const picked = approval?.option.id === o.id;
              return (
                <div key={o.id} className={`flex flex-wrap items-center justify-between gap-2 rounded-xl border px-3 py-2 ${picked ? "border-teal bg-mint/40" : "border-line"}`}>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{i + 1}) {o.name}</p>
                    <p className="text-xs text-muted">{o.maker} · no CDSCO alerts on record · ₹{o.unit_price.toFixed(2)}/unit</p>
                  </div>
                  <div className="flex gap-1.5">
                    <ApproveBtn on={picked && approval?.pharmacist} onClick={() => onApprove(b, o, "pharmacist")} label={`${pharmacist || "Pharmacist"}: approve`} />
                    {b.doctor.required && <ApproveBtn on={picked && approval?.doctor} disabled={!(picked && approval?.pharmacist)} onClick={() => onApprove(b, o, "doctor")} label="Doctor: approve" />}
                  </div>
                </div>
              );
            })}
          </div>
        ) : <p className="text-sm text-muted">No exact same-salt, same-strength option from a clean maker. The pharmacist sources one.</p>}
      </div>

      <AnimatePresence>
        {done && (
          <motion.p initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0 }}
            className="mt-4 flex items-center gap-2 rounded-xl bg-safe/10 px-3 py-2 text-sm text-safe">
            <CheckCircle2 className="size-4" /> One approval, {b.holders.length} home{b.holders.length > 1 ? "s" : ""}: decision and task posted in each family&apos;s room.
          </motion.p>
        )}
      </AnimatePresence>
    </motion.article>
  );
}

function ChatReplay({ net, family, approvals }: { net: SwitchNetwork; family: string; approvals: Record<string, Approval> }) {
  const script = useMemo<Msg[]>(() => {
    const fam = net.families.find((f) => f.name === family);
    if (!fam) return [];
    const msgs: Msg[] = [];
    const flagged = net.flagged.filter((b) => b.holders.some((h) => h.family === family));
    const first = fam.medicines.find((m) => m.flagged) ?? fam.medicines[0];
    if (first) msgs.push({ who: first.person, kind: "human", text: `📷 [strip photo: ${first.brand}]  @kincare-scan यह दवा ठीक है?` });
    if (!flagged.length) msgs.push({ who: "KinCare Scan", kind: "agent", text: "✅ यह बैच किसी सरकारी अलर्ट सूची में नहीं है। Not on any CDSCO alert list." });
    for (const b of flagged) {
      const h = b.holders.find((x) => x.family === family)!;
      msgs.push({ who: "Recall Watcher", kind: "agent",
        text: `⚠️ ${h.person}'s ${b.brand}, batch ${b.batch} is on the CDSCO list: ${b.alert.reason}\nहिंदी: दवा अपने आप बंद न करें, फार्मासिस्ट से पूछें।\n@kincare-pharmacist please find a replacement.` });
      if (b.doctor.required) msgs.push({ who: "Recall Watcher", kind: "agent", text: `🩺 ${b.doctor.why}: the doctor must approve any change too.` });
      const o = b.options[0];
      msgs.push({ who: "KinCare Pharmacist", kind: "agent",
        text: o ? `Same salts, form${b.strengths?.length ? " and strength" : ""}, maker with no alerts: ${o.name} (₹${o.unit_price.toFixed(2)}/unit).\n@Pharmacist reply approve 1 or reject. Nothing changes until you do.`
                : "No exact match from a clean maker. @Pharmacist please source one." });
      msgs.push({ who: h.caregiver || "Family", kind: "human", text: "approve 1" });
      msgs.push({ who: "KinCare Pharmacist", kind: "agent", text: `Thanks ${h.caregiver || ""}. Only the pharmacist can approve a change. @Pharmacist please confirm.` });
      const a = approvals[b.batch];
      if (a?.pharmacist) msgs.push({ who: net.pharmacist || "Pharmacist", kind: "pharmacist", text: "approve 1" });
      if (b.doctor.required && a?.doctor) msgs.push({ who: h.caregiver || "Family", kind: "doctor", text: "Dr. Rao says OK, recheck TSH in 6 weeks" });
      if (a && a.pharmacist && (!b.doctor.required || a.doctor)) {
        msgs.push({ who: "KinCare Pharmacist", kind: "agent", text: `✅ Decision logged. Task for @${h.caregiver}: buy ${short(a.option.name)} today, keep the old strip.` });
        msgs.push({ who: "KinCare Dose Buddy", kind: "agent", text: `${h.person}, कल से नई दवा: ${short(a.option.name)}, 1 गोली। Schedule updated.` });
      } else {
        msgs.push({ who: "Switch", kind: "agent", text: "⏳ Waiting for approval on the Pharmacy Desk →" });
      }
    }
    return msgs;
  }, [net, family, approvals]);

  const [shown, setShown] = useState(0);
  const [playing, setPlaying] = useState(true);
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!playing || shown >= script.length) return;
    const t = setTimeout(() => setShown((n) => n + 1), shown === 0 ? 300 : 1100);
    return () => clearTimeout(t);
  }, [shown, playing, script.length]);
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }); }, [shown]);

  return (
    <div className="overflow-hidden rounded-[28px] border border-line bg-[#0e1621] shadow-xl">
      <div className="flex items-center justify-between bg-[#17212b] px-4 py-3 text-white">
        <div className="flex items-center gap-3">
          <span className="grid size-9 place-items-center rounded-full bg-teal text-sm font-medium">{family[0]}</span>
          <div>
            <p className="text-sm font-medium">{family} Family Care</p>
            <p className="text-[11px] text-white/50">Telegram group · Switch room · 4 agents</p>
          </div>
        </div>
        <button onClick={() => { setShown(0); setPlaying(true); }} className="inline-flex items-center gap-1 rounded-full bg-white/10 px-2.5 py-1 text-xs hover:bg-white/20">
          <Play className="size-3" /> replay
        </button>
      </div>
      <div className="h-[460px] space-y-2 overflow-y-auto p-4">
        <AnimatePresence initial={false}>
          {script.slice(0, shown).map((m, i) => {
            const mine = m.kind !== "agent";
            return (
              <motion.div key={i} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className={`flex ${mine ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[85%] rounded-2xl px-3 py-2 text-[13px] leading-snug text-white ${
                  m.kind === "agent" ? "rounded-bl-sm bg-[#182533]" : m.kind === "pharmacist" ? "rounded-br-sm bg-teal" : m.kind === "doctor" ? "rounded-br-sm bg-[#8a5a1c]" : "rounded-br-sm bg-[#2b5278]"}`}>
                  <p className={`mb-0.5 text-[11px] font-medium ${m.kind === "agent" ? "text-[#6ab3f3]" : "text-white/70"}`}>{m.who}</p>
                  <p className="whitespace-pre-line">{m.text}</p>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
        {shown < script.length && <p className="flex items-center gap-1 text-xs text-white/40"><MessagesSquare className="size-3" /> typing…</p>}
        <div ref={end} />
      </div>
    </div>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return <main className="mx-auto max-w-6xl px-5 pb-24 pt-10 sm:px-8">{children}</main>;
}

function Stat({ n, label, tone }: { n: number; label: string; tone?: "danger" | "warn" }) {
  return (
    <div className="rounded-2xl border border-line bg-paper p-4 text-center">
      <p className={`text-3xl font-medium tracking-tight ${tone === "danger" ? "text-danger" : tone === "warn" ? "text-warn" : "text-espresso"}`}>{n}</p>
      <p className="mt-1 text-xs text-muted">{label}</p>
    </div>
  );
}

function RoomTitle({ icon: Icon, title, sub }: { icon: typeof Store; title: string; sub: string }) {
  return (
    <div className="mb-4">
      <h2 className="flex items-center gap-2 text-lg font-medium"><Icon className="size-5 text-teal" /> {title}</h2>
      <p className="text-sm text-muted">{sub}</p>
    </div>
  );
}

function Badge({ tone, icon: Icon, children }: { tone: "safe" | "danger" | "warn"; icon: typeof Check; children: React.ReactNode }) {
  const c = tone === "safe" ? "bg-safe/10 text-safe" : tone === "danger" ? "bg-danger/10 text-danger" : "bg-warn-soft text-warn";
  return <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${c}`}><Icon className="size-3" /> {children}</span>;
}

function ApproveBtn({ on, disabled, onClick, label }: { on?: boolean; disabled?: boolean; onClick: () => void; label: string }) {
  return (
    <button onClick={onClick} disabled={disabled || on}
      className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium transition ${
        on ? "bg-safe text-white" : disabled ? "cursor-not-allowed bg-sand text-muted" : "bg-espresso text-cream hover:bg-brown-2"}`}>
      {on && <Check className="size-3" />} {label}
    </button>
  );
}

function Doc({ title, icon: Icon, empty, children }: { title: string; icon: typeof Check; empty: string; children: React.ReactNode[] }) {
  return (
    <div className="rounded-2xl border border-line bg-paper">
      <p className="flex items-center gap-2 border-b border-line px-4 py-2.5 text-sm font-medium"><Icon className="size-4 text-teal" /> {title}</p>
      <div className="max-h-56 space-y-1.5 overflow-y-auto px-4 py-3 text-sm">
        {children.length ? children : <p className="text-muted">{empty}</p>}
      </div>
    </div>
  );
}

function Line({ fresh, children }: { fresh?: boolean; children: React.ReactNode }) {
  return (
    <motion.p initial={fresh ? { backgroundColor: "rgba(15,118,110,0.18)" } : false} animate={{ backgroundColor: "rgba(15,118,110,0)" }}
      transition={{ duration: 2 }} className="rounded px-1 py-0.5 text-brown-2">
      {children}
    </motion.p>
  );
}
