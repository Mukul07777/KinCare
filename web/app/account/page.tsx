"use client";

import Link from "next/link";
import { PlanBadge } from "@/components/PlanBadge";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { BadgeCheck, Check, CreditCard, Download, Laptop, Loader2, LogOut, ShieldCheck, Trash2, UserCheck } from "lucide-react";
import { Eyebrow, Heading } from "@/components/Heading";
import { RequestRole } from "@/components/RoleGate";
import { authMe, confirmPayment, endSession, eraseMyData, exportMyData, formatIST, getPlansBilling, getSessions, rupees, signOut, signOutOthers, startCheckout, type ActivePlan, type Me, type PlanInfo, type SessionInfo } from "@/lib/api";

function Account() {
  const params = useSearchParams();
  const [plans, setPlans] = useState<PlanInfo[]>([]);
  const [billing, setBilling] = useState<"month" | "year">("month");
  const [ready, setReady] = useState(true);
  const [test, setTest] = useState(false);
  const [active, setActive] = useState<ActivePlan>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getPlansBilling().then((b) => { setPlans(b.plans); setReady(b.ready); setTest(b.test_mode); setActive(b.active); }).catch((e) => setError(e.message));
    const sid = params.get("session_id");
    if (sid) {
      setNote("Confirming your payment with Stripe…");
      confirmPayment(sid)
        .then((r) => { setActive(r.active); setNote(r.paid ? "Payment received. Your plan is active." : "Payment not completed yet."); })
        .catch((e) => setError(e.message));
    } else if (params.get("cancelled")) setNote("Checkout cancelled. You were not charged.");
  }, [params]);

  const buy = async (id: string) => {
    setBusy(id);
    setError(null);
    try {
      window.location.href = (await startCheckout(id)).url;
    } catch (e) {
      setError((e as Error).message);
      setBusy(null);
    }
  };

  const current = plans.find((p) => p.id === active?.plan);
  return (
    <main className="blush mx-auto max-w-6xl px-4 pt-12 sm:px-6 sm:pt-16">
      <div className="grid items-end gap-6 md:grid-cols-2">
        <div>
          <Eyebrow>Plans</Eyebrow>
          <Heading as="h1" lead="Free for patients," tail="paid for by families and pharmacies." className="mt-4 text-4xl sm:text-6xl" />
        </div>
        <p className="max-w-sm text-muted md:ml-auto">Scanning a medicine and checking a batch is always free. Plans add family care and the pharmacy recall desk.</p>
      </div>

      {note && <p className="mt-6 rounded-2xl bg-sand px-4 py-3 text-sm">{note}</p>}
      {error && <p className="mt-6 rounded-2xl bg-danger/10 px-4 py-3 text-sm text-danger">{error}</p>}
      {!ready && <p className="mt-6 text-sm text-muted">Payments are not switched on yet (no Stripe key on the server).</p>}
      {test && <p className="mt-6 text-sm text-muted">Stripe <b>test mode</b>: use card 4242 4242 4242 4242, any future date, any CVC. No real money moves.</p>}

      {current && (
        <div className="mt-6 flex items-center gap-3 rounded-3xl bg-brown p-5 text-paper">
          <BadgeCheck className="size-6" />
          <p>You are on <b>{current.name}</b> since {formatIST(active!.paid_at)}{active!.email ? ` · ${active!.email}` : ""}</p>
        </div>
      )}

      <div className="mt-6 flex flex-wrap items-center gap-3"><PlanBadge /><SignedIn /></div>
      <p className="mt-3 max-w-2xl text-sm text-muted">
        Every new account gets <b className="text-espresso">14 days of Family free</b>, no card. Pharmacies get <b className="text-espresso">the first month free</b>.
        Customers of a paying pharmacy get WhatsApp reminders free. Batch checks and recall alerts are free for everyone, always.
      </p>
      <div className="mt-6 inline-flex rounded-full border border-line bg-paper p-1 text-sm">
        {(["month", "year"] as const).map((v) => (
          <button key={v} onClick={() => setBilling(v)} className={`rounded-full px-4 py-1.5 font-medium ${billing === v ? "bg-brown text-paper" : "text-muted"}`}>
            {v === "month" ? "Monthly" : "Yearly · 2 months free"}
          </button>
        ))}
      </div>
      <div className="mt-4 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {/* Yearly tab: yearly plans, plus monthly-only plans (no `<id>_year` twin) so nothing disappears. */}
        {plans.filter((p) => p.interval === billing || (billing === "year" && !plans.some((q) => q.id === `${p.id}_year`))).map((p, i) => (
          <div key={p.id} className={`card flex flex-col rounded-[2rem] p-7 ${i === 1 ? "ring-2 ring-brown" : ""}`}>
            <p className="flex items-center justify-between text-lg font-medium">{p.name}
              {p.id === "pharmacy_pro" && <span className="rounded-full bg-teal px-2.5 py-0.5 text-[11px] font-medium text-paper">All features</span>}
            </p>
            <p className="text-sm text-muted">{p.who}</p>
            <p className="mt-5 text-5xl font-medium tracking-tight">{rupees(p.amount)}<span className="text-base text-muted">/{p.interval}</span></p>
            {p.interval === "year" && <p className="mt-1 text-xs text-safe">{rupees(Math.round(p.amount / 12))} a month, billed yearly</p>}
            <ul className="mt-6 flex-1 space-y-2 text-sm">
              {p.features.map((f) => f.endsWith(":")
                ? <li key={f} className="text-xs font-semibold uppercase tracking-wide text-teal">{f}</li>
                : <li key={f} className="flex gap-2"><Check className="mt-0.5 size-4 shrink-0 text-brown" />{f}</li>)}
            </ul>
            <button onClick={() => buy(p.id)} disabled={!!busy || !ready || active?.plan === p.id}
              className="mt-6 inline-flex items-center justify-center gap-2 rounded-full bg-espresso py-3 text-sm font-medium text-paper transition hover:bg-brown disabled:opacity-40">
              {busy === p.id ? <Loader2 className="size-4 animate-spin" /> : <CreditCard className="size-4" />}
              {active?.plan === p.id ? "Current plan" : "Subscribe with Stripe"}
            </button>
          </div>
        ))}
      </div>
      <p className="mt-6 text-xs text-muted">Billed in INR through Stripe. Cancel any time. Recall alerts, scans and phone notifications stay free for everyone. Prices come from the server, not this page.</p>
      <Roles />
      <Devices />
      <YourData />
    </main>
  );
}

// Professional roles. Everyone is a patient; a pharmacist or regulator asks here and an admin checks the licence.
function Roles() {
  const [me, setMe] = useState<Me | null>(null);
  const [ask, setAsk] = useState<"pharmacist" | "regulator" | null>(null);
  const load = () => authMe().then(setMe).catch(() => setMe(null));
  useEffect(() => { load(); }, []);
  if (!me?.phone) return null;
  const pro = me.roles.filter((r) => r !== "patient");
  return (
    <section className="mt-12 rounded-[2rem] border border-line bg-paper p-6">
      <h2 className="flex items-center gap-2 text-xl font-semibold"><UserCheck className="size-5 text-teal" /> Your role</h2>
      <p className="mt-1 text-sm text-muted">
        You are a <b className="text-espresso">patient</b>{pro.length > 0 && <> and <b className="text-espresso">{pro.join(", ")}</b></>}.
        Pharmacists see their own shop&apos;s customers; regulators see who holds a flagged batch. Caregivers and doctors don&apos;t need a role: the patient shares with them.
      </p>
      <div className="mt-4 flex flex-wrap gap-2">
        {(["pharmacist", "regulator"] as const).filter((r) => !pro.includes(r)).map((r) => (
          <button key={r} onClick={() => setAsk(ask === r ? null : r)}
            className={`rounded-full border px-4 py-2 text-sm font-medium ${ask === r ? "border-espresso bg-espresso text-paper" : "border-line bg-cream hover:bg-mint"}`}>
            I&apos;m a {r === "pharmacist" ? "pharmacist" : "drug regulator"}
          </button>
        ))}
      </div>
      {ask && <div className="max-w-md"><RequestRole key={ask} role={ask} onActive={load} /></div>}
    </section>
  );
}

// Every browser or phone holding a session for this account. A lost phone is signed out from here.
function Devices() {
  const [list, setList] = useState<SessionInfo[] | null>(null);
  const load = () => getSessions().then(setList).catch(() => setList([]));
  useEffect(() => { load(); }, []);
  if (!list || list.length === 0) return null;
  const others = list.filter((x) => !x.current).length;
  return (
    <section className="mt-12 rounded-[2rem] border border-line bg-paper p-6">
      <h2 className="flex items-center gap-2 text-xl font-semibold"><Laptop className="size-5 text-teal" /> Signed-in devices</h2>
      <p className="mt-1 text-sm text-muted">Lost a phone? Sign it out here. Sessions also end by themselves after 30 days without use.</p>
      <ul className="mt-4 divide-y divide-line">
        {list.map((d) => (
          <li key={d.id} className="flex items-center justify-between gap-3 py-3 text-sm">
            <span>
              <b>{d.label}</b>{d.current && <span className="ml-2 rounded-full bg-mint px-2 py-0.5 text-xs font-medium text-teal">This device</span>}
              <span className="block text-xs text-muted">{d.kind === "user" ? "Signed in" : "Guest"} · last used {formatIST(d.last_seen)}</span>
            </span>
            {!d.current && (
              <button onClick={async () => { await endSession(d.id).catch(() => {}); load(); }} className="rounded-full border border-line px-3 py-1.5 text-xs font-medium hover:border-danger hover:text-danger">Sign out</button>
            )}
          </li>
        ))}
      </ul>
      {others > 0 && (
        <button onClick={async () => { await signOutOthers().catch(() => {}); load(); }}
          className="mt-3 inline-flex items-center gap-2 rounded-full border border-danger/30 px-4 py-2 text-sm font-medium text-danger hover:bg-danger hover:text-paper">
          <LogOut className="size-4" /> Sign out all other devices
        </button>
      )}
    </section>
  );
}

// DPDP Act 2023: see everything KinCare holds about you, or erase it.
function YourData() {
  const [busy, setBusy] = useState<"" | "export" | "erase">("");
  const [msg, setMsg] = useState("");
  const download = async () => {
    setBusy("export"); setMsg("");
    try {
      const d = await exportMyData();
      const url = URL.createObjectURL(new Blob([JSON.stringify(d, null, 2)], { type: "application/json" }));
      Object.assign(document.createElement("a"), { href: url, download: `kincare-my-data-${d.generated_at.slice(0, 10)}.json` }).click();
      URL.revokeObjectURL(url);
    } catch (e) { setMsg((e as Error).message); } finally { setBusy(""); }
  };
  const erase = async () => {
    if (!confirm("Delete everything KinCare holds about you? Prescriptions, doses, vitals, chats, caregiver links and your login. This cannot be undone.")) return;
    setBusy("erase"); setMsg("");
    try {
      const r = await eraseMyData();
      await signOut();
      setMsg(`Deleted ${Object.values(r.deleted).reduce((a, b) => a + b, 0)} records. This browser now starts fresh.`);
    } catch (e) { setMsg((e as Error).message); } finally { setBusy(""); }
  };
  return (
    <section className="mt-12 rounded-[2rem] border border-line bg-paper p-6">
      <h2 className="flex items-center gap-2 text-xl font-semibold"><ShieldCheck className="size-5 text-teal" /> Your data</h2>
      <p className="mt-1 max-w-2xl text-sm text-muted">
        Your health data belongs to you. Download a copy of everything KinCare holds, or delete all of it. <Link href="/privacy" className="font-medium text-teal">How we handle your data →</Link>
      </p>
      <div className="mt-4 flex flex-wrap gap-2">
        <button onClick={download} disabled={!!busy} className="inline-flex items-center gap-2 rounded-full border border-line bg-cream px-5 py-2.5 text-sm font-medium hover:bg-mint disabled:opacity-50">
          {busy === "export" ? <Loader2 className="size-4 animate-spin" /> : <Download className="size-4" />} Download my data
        </button>
        <button onClick={erase} disabled={!!busy} className="inline-flex items-center gap-2 rounded-full border border-danger/30 px-5 py-2.5 text-sm font-medium text-danger hover:bg-danger hover:text-paper disabled:opacity-50">
          {busy === "erase" ? <Loader2 className="size-4 animate-spin" /> : <Trash2 className="size-4" />} Delete all my data
        </button>
      </div>
      {msg && <p className="mt-3 text-sm text-teal">{msg}</p>}
    </section>
  );
}

// Who is signed in, with sign in / sign out. Signing out gives this browser a fresh, empty identity.
function SignedIn() {
  const [me, setMe] = useState<string | null | undefined>(undefined);
  useEffect(() => { authMe().then((m) => setMe(m.masked)).catch(() => setMe(null)); }, []);
  if (me === undefined) return null;
  if (!me) return <Link href="/login?next=/account" className="rounded-full bg-espresso px-4 py-1.5 text-xs font-medium text-paper hover:bg-brown">Sign in with your phone</Link>;
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-line bg-paper px-4 py-1.5 text-xs">
      Signed in as <b className="font-mono">{me}</b>
      <button onClick={async () => { await signOut(); window.location.href = "/"; }} className="font-medium text-danger hover:underline">Sign out</button>
    </span>
  );
}

export default function AccountPage() {
  return <Suspense><Account /></Suspense>;
}
