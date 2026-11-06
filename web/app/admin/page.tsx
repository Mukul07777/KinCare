"use client";

import { useCallback, useEffect, useState } from "react";
import { Database, Lock, RefreshCw, ScrollText, Siren, UserCheck } from "lucide-react";
import { Eyebrow, Heading } from "@/components/Heading";
import { adminAudit, adminDecideRole, adminGrantRole, adminIngest, adminRoles, formatIST, formatMonth, getAdmin, resolveSos, rupees, type AdminOverview, type AuditEntry, type Role, type RoleQueueItem } from "@/lib/api";

function Kpi({ label, value, hot }: { label: string; value: string | number; hot?: boolean }) {
  return (
    <div className={`card rounded-3xl p-5 ${hot ? "bg-danger text-paper" : ""}`}>
      <p className={`text-xs ${hot ? "text-paper/80" : "text-muted"}`}>{label}</p>
      <p className="mt-2 text-3xl font-medium tracking-tight">{value}</p>
    </div>
  );
}

export default function AdminPage() {
  const [token, setToken] = useState("");
  const [d, setD] = useState<AdminOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  const load = useCallback((t: string) => {
    getAdmin(t).then((x) => { setD(x); setError(null); }).catch((e) => { setD(null); setError(e.message); });
  }, []);
  useEffect(() => {
    let t = "";
    try { t = sessionStorage.getItem("kincare.admin") ?? ""; } catch {}
    setToken(t);
    load(t);
  }, [load]);
  useEffect(() => {
    if (!d) return;
    const i = setInterval(() => load(token), 15000);
    return () => clearInterval(i);
  }, [d, token, load]);

  const unlock = () => {
    try { sessionStorage.setItem("kincare.admin", token); } catch {}
    load(token);
  };

  return (
    <main className="mx-auto max-w-6xl px-4 pt-12 sm:px-6 sm:pt-16">
      <Eyebrow>Admin</Eyebrow>
      <Heading as="h1" lead="Operations," tail="at a glance." className="mt-4 text-4xl sm:text-6xl" />

      {!d && (
        <div className="card mt-8 max-w-md rounded-3xl p-6">
          <p className="flex items-center gap-2 font-medium"><Lock className="size-4 text-brown" /> Admin token</p>
          {error && <p className="mt-2 text-sm text-danger">{error}</p>}
          <input type="password" value={token} onChange={(e) => setToken(e.target.value)} onKeyDown={(e) => e.key === "Enter" && unlock()}
            className="mt-3 w-full rounded-xl border border-line bg-cream/60 px-3 py-2 text-sm outline-none" placeholder="ADMIN_TOKEN" />
          <button onClick={unlock} className="mt-3 rounded-full bg-espresso px-5 py-2 text-sm font-medium text-paper">Open</button>
        </div>
      )}

      {d && (
        <>
          <div className="mt-8 grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Kpi label="Open SOS" value={d.sos_open} hot={d.sos_open > 0} />
            <Kpi label="Urgent check-ins to review" value={d.checkins_urgent} hot={d.checkins_urgent > 0} />
            <Kpi label="Urgent vitals, last 7 days" value={`${d.vitals_urgent_7d} / ${d.vitals_7d}`} />
            <Kpi label="Batches flagged by Early Signal" value={d.signals.flagged} />
            <Kpi label="Users (devices)" value={d.users} />
            <Kpi label="MRR" value={`₹${d.payments.mrr.toLocaleString("en-IN")}`} />
            <Kpi label="Revenue to date" value={`₹${d.payments.lifetime.toLocaleString("en-IN")}`} />
            <Kpi label="Watched batches (flagged)" value={`${d.watchlist} (${d.flagged_watch})`} />
          </div>

          <div className="mt-6 grid gap-6 lg:grid-cols-2">
            <div className="card rounded-3xl p-6">
              <p className="flex items-center gap-2 font-medium"><Siren className="size-4 text-danger" /> SOS events</p>
              <div className="mt-3 divide-y divide-line text-sm">
                {d.sos.length === 0 && <p className="py-4 text-muted">None.</p>}
                {d.sos.map((s) => (
                  <div key={s.id} className="flex flex-wrap items-center justify-between gap-2 py-2.5">
                    <span><b>{s.member}</b> · <span className="text-xs text-muted">{formatIST(s.at)}</span></span>
                    <span className="flex items-center gap-2">
                      {s.lat !== null && <a className="text-xs text-brown underline" target="_blank" rel="noreferrer" href={`https://maps.google.com/?q=${s.lat},${s.lng}`}>Map</a>}
                      {s.resolved_at ? <span className="text-xs text-safe">Resolved</span> : (
                        <button onClick={() => resolveSos(s.id, token).then(() => load(token))} className="rounded-full bg-danger px-3 py-1 text-xs font-medium text-paper">Mark resolved</button>
                      )}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="card rounded-3xl p-6">
              <p className="font-medium">Payments {d.payments.test_mode && <span className="ml-2 rounded-full bg-sand px-2 py-0.5 text-[10px] text-brown">TEST MODE</span>}{!d.payments.ready && <span className="ml-2 text-xs text-muted">Stripe key not set</span>}</p>
              <div className="mt-2 flex flex-wrap gap-2 text-xs">
                {d.payments.active_by_plan.map((p) => <span key={p.plan} className="rounded-full border border-line px-3 py-1">{p.name}: {p.n}</span>)}
              </div>
              <div className="mt-3 divide-y divide-line text-sm">
                {d.payments.recent.length === 0 && <p className="py-4 text-muted">No payments yet.</p>}
                {d.payments.recent.map((p, i) => (
                  <div key={i} className="flex items-center justify-between py-2">
                    <span>{p.plan} <span className="text-xs text-muted">{p.email ?? ""}</span></span>
                    <span className="font-mono text-xs">{rupees(p.amount)} · <span className={p.status === "paid" ? "text-safe" : "text-muted"}>{p.status}</span></span>
                  </div>
                ))}
              </div>
            </div>

            <div className="card rounded-3xl p-6 lg:col-span-2">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="flex items-center gap-2 font-medium"><Database className="size-4 text-brown" /> Regulator data</p>
                <button onClick={() => adminIngest(token).then(() => setNote("Fetching new CDSCO alerts in the background."))} className="inline-flex items-center gap-1.5 rounded-full border border-line px-4 py-2 text-xs font-medium hover:border-brown">
                  <RefreshCw className="size-3.5" /> Fetch new alerts now
                </button>
              </div>
              {note && <p className="mt-2 text-xs text-muted">{note}</p>}
              <p className="mt-3 text-sm text-muted">
                {d.data.alerts.toLocaleString("en-IN")} alerts · {formatMonth(d.data.start)} to {formatMonth(d.data.end)}
                {d.data.last_ingest && <> · last fetched {formatIST(d.data.last_ingest)}</>} · {d.recall_runs} recall runs · {d.notifications} notifications · {d.signals.reports} symptom reports
              </p>
            </div>
          </div>
          <Access token={token} />
        </>
      )}
    </main>
  );
}

// Role requests to check (licence / employee id), active roles to revoke, direct grants by phone, and the audit log.
function Access({ token }: { token: string }) {
  const [queue, setQueue] = useState<RoleQueueItem[]>([]);
  const [log, setLog] = useState<AuditEntry[]>([]);
  const [phone, setPhone] = useState("");
  const [role, setRole] = useState<Role>("pharmacist");
  const [msg, setMsg] = useState("");
  const load = useCallback(() => {
    adminRoles(token).then(setQueue).catch((e) => setMsg(e.message));
    adminAudit(token).then(setLog).catch(() => {});
  }, [token]);
  useEffect(() => { load(); }, [load]);
  const act = (id: number, d: "approve" | "reject" | "revoke") => adminDecideRole(id, d, token).then(load).catch((e) => setMsg(e.message));
  const grant = () => adminGrantRole(phone, role, token)
    .then((r) => { setMsg(r.already ? "They already have that role." : `Granted ${role}.`); setPhone(""); load(); })
    .catch((e) => setMsg(e.message));

  return (
    <div className="mt-6 grid gap-6 lg:grid-cols-2">
      <div className="card rounded-3xl p-6">
        <p className="flex items-center gap-2 font-medium"><UserCheck className="size-4 text-teal" /> Roles</p>
        <p className="mt-1 text-xs text-muted">Check the licence or officer ID before approving. A role only works on a phone-verified account.</p>
        <div className="mt-3 divide-y divide-line text-sm">
          {queue.length === 0 && <p className="py-4 text-muted">No requests or professional roles yet.</p>}
          {queue.map((g) => (
            <div key={g.id} className="flex flex-wrap items-center justify-between gap-2 py-2.5">
              <span>
                <b className="capitalize">{g.role}</b> · {g.org ?? "granted directly"} {g.licence && <span className="font-mono text-xs">({g.licence})</span>}
                <span className="block text-xs text-muted">{g.phone ?? "no phone"} · {g.status === "pending" ? `asked ${formatIST(g.requested_at)}` : `active since ${formatIST(g.decided_at ?? g.requested_at)}`}</span>
              </span>
              <span className="flex gap-2">
                {g.status === "pending" ? <>
                  <button onClick={() => act(g.id, "approve")} className="rounded-full bg-teal px-3 py-1 text-xs font-medium text-paper">Approve</button>
                  <button onClick={() => act(g.id, "reject")} className="rounded-full border border-line px-3 py-1 text-xs font-medium">Reject</button>
                </> : <button onClick={() => act(g.id, "revoke")} className="rounded-full border border-danger/30 px-3 py-1 text-xs font-medium text-danger">Revoke</button>}
              </span>
            </div>
          ))}
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="Phone of a signed-up user" aria-label="Phone to grant a role to"
            className="min-w-0 flex-1 rounded-xl border border-line bg-cream/60 px-3 py-2 text-sm outline-none" />
          <select value={role} onChange={(e) => setRole(e.target.value as Role)} aria-label="Role" className="rounded-xl border border-line bg-cream/60 px-3 py-2 text-sm">
            <option value="pharmacist">Pharmacist</option><option value="regulator">Regulator</option><option value="admin">Admin</option>
          </select>
          <button onClick={grant} disabled={phone.trim().length < 10} className="rounded-full bg-espresso px-4 py-2 text-xs font-medium text-paper disabled:opacity-40">Grant</button>
        </div>
        {msg && <p className="mt-2 text-xs text-muted">{msg}</p>}
      </div>

      <div className="card rounded-3xl p-6">
        <p className="flex items-center gap-2 font-medium"><ScrollText className="size-4 text-brown" /> Audit log</p>
        <p className="mt-1 text-xs text-muted">Every privileged action: role decisions, looks at who holds a flagged batch, alerts and recall runs.</p>
        <div className="mt-3 max-h-80 divide-y divide-line overflow-y-auto text-xs">
          {log.length === 0 && <p className="py-4 text-sm text-muted">Nothing yet.</p>}
          {log.map((a) => (
            <div key={a.id} className="flex justify-between gap-3 py-2">
              <span><b className="font-mono">{a.action}</b> {a.target && <span className="font-mono text-muted">{a.target}</span>} {a.detail && <span className="text-muted">· {a.detail}</span>}</span>
              <span className="shrink-0 text-muted">{a.actor === "admin-token" ? "admin token" : a.actor} · {formatIST(a.at)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
