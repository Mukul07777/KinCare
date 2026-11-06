import { request, type Alert } from "./api";

export type StockRow = { product: string; batch: string; maker: string; qty: number };

export type TaskStatus = "open" | "verifying" | "quarantined" | "returned" | "resolved";

export const STATUS_FLOW: { id: TaskStatus; label: string }[] = [
  { id: "open", label: "Open" },
  { id: "verifying", label: "Verifying on shelf" },
  { id: "quarantined", label: "Quarantined" },
  { id: "returned", label: "Returned to supplier" },
  { id: "resolved", label: "Resolved" },
];

export type Task = {
  id: string;
  row: StockRow;
  alert: Alert;
  level: "strong" | "possible";
  status: TaskStatus;
  assignee: string;
  note: string;
};

export type AuditEntry = { at: string; who: string; action: string };

export type PharmacyState = {
  checkedAt: string | null;
  total: number;
  tasks: Task[];
  audit: AuditEntry[];
};

export const EMPTY: PharmacyState = { checkedAt: null, total: 0, tasks: [], audit: [] };

// Through lib/api's request(): the session cookie, the CSRF header and a fresh session if this one expired.
export async function loadState(): Promise<PharmacyState> {
  const res = await request("/api/pharmacy/state");
  if (!res.ok) throw new Error(`Could not load recall desk (${res.status})`);
  return { ...EMPTY, ...((await res.json()) ?? {}) };
}

export async function saveState(s: PharmacyState) {
  await request("/api/pharmacy/state", { method: "PUT", body: JSON.stringify(s) });
}

// Tolerant CSV parser: header names are matched loosely, quotes supported.
export function parseCsv(text: string): StockRow[] {
  const lines = text.split(/\r?\n/).filter((l) => l.trim());
  if (lines.length < 2) return [];
  const split = (l: string) => (l.match(/("([^"]|"")*"|[^,]*)(,|$)/g) ?? []).map((c) => c.replace(/,$/, "").replace(/^"|"$/g, "").replace(/""/g, '"').trim());
  const head = split(lines[0]).map((h) => h.toLowerCase());
  const col = (...names: string[]) => head.findIndex((h) => names.some((n) => h.includes(n)));
  const ci = { product: col("product", "item", "name", "medicine"), batch: col("batch", "lot"), maker: col("maker", "manufacturer", "mfr", "company"), qty: col("qty", "quantity", "stock") };
  if (ci.batch < 0) throw new Error("No batch column found. Add a column named “batch”.");
  return lines.slice(1).map((l) => {
    const c = split(l);
    return {
      product: ci.product >= 0 ? c[ci.product] ?? "" : "",
      batch: c[ci.batch] ?? "",
      maker: ci.maker >= 0 ? c[ci.maker] ?? "" : "",
      qty: ci.qty >= 0 ? Number(c[ci.qty]) || 0 : 0,
    };
  }).filter((r) => r.batch);
}

export async function checkInventory(rows: StockRow[]) {
  const res = await request("/api/inventory/check", { method: "POST", body: JSON.stringify(rows) });
  if (!res.ok) throw new Error(`Inventory check failed (${res.status})`);
  return (await res.json()) as {
    checked_at: string;
    total: number;
    flagged: number;
    rows: (StockRow & { matches: { alert: Alert; score: { level: "strong" | "possible" } }[] })[];
  };
}

export function auditCsv(s: PharmacyState) {
  const esc = (v: string | number) => `"${String(v).replace(/"/g, '""')}"`;
  const tasks = [
    ["product", "batch", "maker", "qty", "alert", "category", "alert_month", "status", "assignee", "note", "regulator_link"],
    ...s.tasks.map((t) => [t.row.product, t.row.batch, t.row.maker, t.row.qty, t.alert.product_name, t.alert.category, t.alert.alert_month, t.status, t.assignee, t.note, t.alert.alert_url]),
  ];
  const log = [["time", "who", "action"], ...s.audit.map((a) => [a.at, a.who, a.action])];
  return [`# KinCare recall report, checked ${s.checkedAt ?? ""}`, ...tasks.map((r) => r.map(esc).join(",")), "", "# Audit log", ...log.map((r) => r.map(esc).join(","))].join("\n");
}
