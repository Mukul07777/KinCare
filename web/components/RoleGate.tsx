"use client";

import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";
import { Clock, Loader2, ShieldCheck } from "lucide-react";
import { authMe, myRoles, requestRole, type Me, type RoleGrant } from "@/lib/api";

const NAME = { pharmacist: "Pharmacist", regulator: "Drug regulator", admin: "KinCare admin" } as const;
const FIELDS = {
  pharmacist: { org: "Pharmacy name and city", licence: "Drug licence no. (Form 20/21)" },
  regulator: { org: "Office (e.g. State Drugs Control, Gujarat)", licence: "Employee / officer ID" },
} as const;

// Pages for professionals: shown only to accounts whose role carries `perm` (the server checks it again on every call).
// Everyone else sees why, and a way to ask for the role.
export function RoleGate({ perm, role, what, children }: { perm: string; role: keyof typeof NAME; what: string; children: ReactNode }) {
  const [me, setMe] = useState<Me | null | undefined>(undefined);
  useEffect(() => { authMe().then(setMe).catch(() => setMe(null)); }, []);
  if (me === undefined) return <main className="mx-auto max-w-6xl px-4 pt-16"><Loader2 className="size-5 animate-spin text-muted" /></main>;
  if (me?.permissions.includes(perm)) return <>{children}</>;
  return (
    <main className="mx-auto max-w-xl px-4 pt-16 sm:px-6">
      <div className="rounded-[2rem] border border-line bg-paper p-7">
        <p className="flex items-center gap-2 text-sm font-medium text-teal"><ShieldCheck className="size-4" /> For {NAME[role].toLowerCase()}s</p>
        <h1 className="mt-3 text-2xl font-semibold">{what}</h1>
        <p className="mt-2 text-sm text-muted">
          This page shows other people&apos;s medical or contact data, so it needs the <b className="text-espresso">{NAME[role]}</b> role on a
          phone-verified account. Every look here is recorded in an audit log.
        </p>
        {!me?.phone
          ? <Link href={`/login?next=${encodeURIComponent(typeof window === "undefined" ? "/" : window.location.pathname)}`}
              className="mt-5 inline-flex rounded-full bg-espresso px-5 py-2.5 text-sm font-medium text-paper hover:bg-brown">Sign in with your phone</Link>
          : role === "admin"
            ? <p className="mt-5 rounded-2xl bg-sand px-4 py-3 text-sm">Admin is granted by an existing KinCare admin, never requested.</p>
            : <RequestRole role={role} onActive={() => authMe().then(setMe)} />}
      </div>
    </main>
  );
}

export function RequestRole({ role, onActive }: { role: "pharmacist" | "regulator"; onActive?: () => void }) {
  const [mine, setMine] = useState<RoleGrant[] | null>(null);
  const [org, setOrg] = useState("");
  const [licence, setLicence] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const load = () => myRoles().then(setMine).catch(() => setMine([]));
  useEffect(() => { load(); }, []);
  const open = mine?.find((g) => g.role === role && (g.status === "pending" || g.status === "active"));

  const send = async () => {
    setBusy(true); setError("");
    try {
      const r = await requestRole(role, org, licence);
      await load();
      if (r.status === "active") onActive?.();
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };

  if (!mine) return null;
  if (open?.status === "pending") return (
    <p className="mt-5 flex items-start gap-2 rounded-2xl bg-sand px-4 py-3 text-sm">
      <Clock className="mt-0.5 size-4 shrink-0 text-brown" />
      Request sent for <b className="mx-1">{open.org}</b> ({open.licence}). A KinCare admin checks the licence and approves it.
    </p>
  );
  if (open?.status === "active") return <p className="mt-5 rounded-2xl bg-mint px-4 py-3 text-sm text-teal">You have the {NAME[role]} role for {open.org}.</p>;
  return (
    <div className="mt-5 space-y-2">
      <input value={org} onChange={(e) => setOrg(e.target.value)} placeholder={FIELDS[role].org} aria-label={FIELDS[role].org}
        className="w-full rounded-2xl border border-line bg-cream px-4 py-2.5 text-sm" />
      <input value={licence} onChange={(e) => setLicence(e.target.value)} placeholder={FIELDS[role].licence} aria-label={FIELDS[role].licence}
        className="w-full rounded-2xl border border-line bg-cream px-4 py-2.5 text-sm" />
      <button onClick={send} disabled={busy || org.trim().length < 2 || licence.trim().length < 3}
        className="inline-flex items-center gap-2 rounded-full bg-espresso px-5 py-2.5 text-sm font-medium text-paper hover:bg-brown disabled:opacity-40">
        {busy && <Loader2 className="size-4 animate-spin" />} Request {NAME[role].toLowerCase()} access
      </button>
      {error && <p className="text-sm text-danger">{error}</p>}
    </div>
  );
}
