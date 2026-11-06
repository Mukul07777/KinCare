// Every call goes to this site's own /api (next.config.ts forwards it to the KinCare API), so the session cookie is
// first-party and HttpOnly. PUBLIC_API_URL is only for showing developers the public API address.
export const API_URL = "";
export const PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Alert = {
  id: number;
  source: "cdsco_nsq" | "cdsco_spurious" | "state_nsq";
  category: "nsq" | "spurious";
  product_name: string;
  brand: string;
  batch_no: string;
  mfg_date: string;
  expiry: string;
  manufacturer: string;
  manufacturer_full: string;
  reason: string;
  reported_by: string;
  remarks: string;
  alert_month: string;
  alert_url: string;
  pdf_page: number | null;
};

export type Score = { level: "strong" | "possible"; batch: number; lookalike?: boolean; maker: number | null; brand: number | null };

export type Failure = { key: string; label: string; severity: "critical" | "high" | "medium" | "low"; en: string; hi: string };

export type CheckResult = {
  verdict: "alert_found" | "no_alert_found";
  checked_at: string;
  sources: { id: string; name: string; status: "match" | "no_match" }[];
  matches: { alert: Alert; score: Score; explain: Failure[] }[];
};

type NameN = { name: string; n: number };
export type Insights = {
  total: number;
  critical_total: number;
  by_state: NameN[];
  by_failure: (NameN & { key: string; severity: Failure["severity"] })[];
  by_form: NameN[];
  by_group: NameN[];
  by_year: NameN[];
  critical_recent: { product_name: string; reason: string; month: string; type: string }[];
};
export const getInsights = () => call<Insights>("/api/insights");

export type ScanResult = {
  fields: { batch: string | null; expiry: string | null; mfg_date: string | null; maker: string | null; brand: string | null };
  confidence: Record<string, number>;
  lines: string[];
};

export type Stats = {
  total: number;
  spurious: number;
  manufacturers: number;
  documents: number;
  coverage: { start: string; end: string };
  by_month: { month: string; n: number }[];
  by_source: { source: string; n: number }[];
  top_manufacturers: { manufacturer: string; n: number }[];
  last_ingest: string | null;
};

export type WatchItem = {
  batch: string;
  brand: string | null;
  maker: string | null;
  member: string | null;
  expiry: string | null;
  phone: string | null;
  added_at: string;
  last_verdict: "alert_found" | "no_alert_found";
  last_checked_at: string;
};

// Identity is a server-issued session in an HttpOnly cookie: this code never sees or chooses an id.
// First call (or after it expires): ask the server for a fresh private session, then retry once.
let starting: Promise<unknown> | null = null;
export function ensureSession() {
  return (starting ??= fetch("/api/session", { method: "POST", headers: { "X-KinCare": "1" } }).finally(() => { starting = null; }));
}

// fetch() rejects with a bare "Failed to fetch" when the server can't be reached; say what that means instead.
export const OFFLINE = "Can't reach the KinCare server. Check the connection and try again.";

// X-KinCare marks a request as coming from this app: the API refuses cookie-authenticated changes without it (CSRF).
export async function request(path: string, init: RequestInit = {}, retry = true): Promise<Response> {
  const res = await fetch(`${API_URL}${path}`, {
    cache: "no-store",
    credentials: "same-origin",
    ...init,
    headers: { "X-KinCare": "1", ...(init.body && !(init.body instanceof FormData) ? { "Content-Type": "application/json" } : {}), ...init.headers },
  }).catch(() => { throw new Error(OFFLINE); });
  if (res.status === 401 && retry && path !== "/api/session") {
    await ensureSession().catch(() => {});
    return request(path, init, false);
  }
  return res;
}

async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await request(path, init);
  if (!res.ok) throw new Error((await res.json().catch(() => null))?.detail ?? `Request failed (${res.status})`);
  return res.json();
}

const qs = (o: Record<string, string | number | undefined | null>) =>
  new URLSearchParams(Object.entries(o).filter(([, v]) => v !== undefined && v !== null && v !== "") as [string, string][]).toString();

export const checkBatch = (p: { batch: string; maker?: string; brand?: string }) => call<CheckResult>(`/api/check?${qs(p)}`);

export function scanImage(file: File) {
  const form = new FormData();
  form.append("image", file);
  return call<ScanResult>("/api/scan", { method: "POST", body: form });
}

export type BillResult = {
  checked_at: string;
  flagged: number;
  lines: string[];
  items: { batch: string; line: string; conf: number; verdict: CheckResult["verdict"]; match: (CheckResult["matches"][number]) | null }[];
};
export function scanBill(file: File) {
  const form = new FormData();
  form.append("image", file);
  return call<BillResult>("/api/scan/bill", { method: "POST", body: form });
}

export const getStats = () => call<Stats>("/api/stats");

export const getAlerts = (p: { q?: string; category?: string; limit?: number; offset?: number }) =>
  call<{ total: number; items: Alert[] }>(`/api/alerts?${qs(p)}`);

export type MakerHistory = {
  name: string;
  total: number;
  spurious?: number;
  variants: string[];
  by_year: { year: string; n: number }[];
  alerts: Alert[];
};
export const getManufacturer = (name: string) => call<MakerHistory>(`/api/manufacturer?${qs({ name })}`);

export function whatsappShare(a: Alert, batch: string) {
  const text =
    `Medicine batch alert (via KinCare)\n${a.product_name}\nBatch ${batch} is listed as ${a.category === "spurious" ? "SPURIOUS" : "Not of Standard Quality"} ` +
    `in the ${formatMonth(a.alert_month)} regulator alert.\nReason: ${a.reason}\nSource: ${a.alert_url}\n` +
    `Do not stop any medicine on your own. Show this to your pharmacist or doctor.`;
  return `https://wa.me/?text=${encodeURIComponent(text)}`;
}

export type RecallConfig = { agents: "tinyfish" | "direct"; twilio: boolean; sources: { id: string; name: string; url: string }[] };
export const getRecallConfig = () => call<RecallConfig>("/api/recall/config");
export const startRecall = (b: { scope: string; demo_phone?: string; demo_name?: string; demo_language?: string; demo_city?: string }) =>
  call<{ run_id: string }>("/api/recall/run", { method: "POST", body: JSON.stringify(b) });
export const recallStreamUrl = (id: string) => `${API_URL}/api/recall/stream/${id}`;

export type AskResult = { answer: string; total: number; citations: Alert[]; understood: string[] };
export const askRegulator = (q: string) => call<AskResult>(`/api/ask?${qs({ q })}`);

export type Sale = { pharmacy?: string; city?: string; customer?: string; phone?: string; language?: string; product?: string; batch: string; sold_at?: string };
export const putSales = (s: Sale[]) => call<{ count: number }>("/api/sales", { method: "PUT", body: JSON.stringify(s) });
export const getSales = () => call<(Sale & { id: number })[]>("/api/sales");
export const notifyBuyers = (batch: string) =>
  call<{ buyers: number; notifications: { channel: string; customer: string; status: string; message: string; language: string }[] }>(
    `/api/pharmacy/notify?${qs({ batch })}`, { method: "POST" });

// Speak a voice script in the browser (used when no phone provider is configured).
export function speak(text: string, lang: string) {
  try {
    const u = new SpeechSynthesisUtterance(text);
    u.lang = lang === "hi" ? "hi-IN" : "en-IN";
    const v = speechSynthesis.getVoices().find((x) => x.lang.startsWith(u.lang.slice(0, 2)));
    if (v) u.voice = v;
    u.rate = 0.95;
    speechSynthesis.cancel();
    speechSynthesis.speak(u);
  } catch {
    /* speech not available */
  }
}

export type CheckinInfo = {
  name: string | null;
  batch: string;
  language: string;
  responded: boolean;
  alert: { product_name: string; brand: string; category: string; alert_month: string; reason: string; alert_url: string } | null;
  symptoms: { key: string; en: string; hi: string }[];
};
export type CheckinItem = {
  id: number; token: string; name: string | null; phone: string | null; batch: string; created_at: string; responded_at: string | null;
  feeling: string | null; symptoms: string | null; bp_sys: number | null; bp_dia: number | null; note: string | null;
  triage: "urgent" | "review" | "ok" | null; reviewed: number; product_name: string | null; brand: string | null;
};
export const getCheckin = (t: string) => call<CheckinInfo>(`/api/checkin/${encodeURIComponent(t)}`);
export const postCheckin = (t: string, b: { feeling: string; symptoms: string[]; bp_sys?: number; bp_dia?: number; note?: string }) =>
  call<{ triage: "urgent" | "review" | "ok" }>(`/api/checkin/${encodeURIComponent(t)}`, { method: "POST", body: JSON.stringify(b) });
export const getCheckins = () => call<{ items: CheckinItem[]; responded: number; urgent: number }>("/api/checkins");
export const markReviewed = (id: number) => call(`/api/checkins/${id}/reviewed`, { method: "POST" });
export const pvpiCsvUrl = () => `${API_URL}/api/checkins/pvpi.csv`;

// ---- care ----
export type Assessment = { level: "ok" | "doctor" | "urgent"; reasons: string[]; en: string; hi: string };
export type Vital = { id: number; member: string; at: string; temp_c: number | null; bp_sys: number | null; bp_dia: number | null; pulse: number | null; spo2: number | null; level: string };
export type RxMed = { name: string; strength: string; food: string; morning: number; noon: number; night: number; days: number | null; as_needed: boolean; batch?: string | null; line?: string };
export type Plan = { id: number; member: string; doctor: string | null; diagnosis: string | null; start_date: string; advice: string[]; medicines: (RxMed & { id: number; bought_at?: string | null; pharmacy?: string | null })[] };
export type Dose = { slot: "morning" | "noon" | "night"; time: string; med_id: number; name: string; strength: string; food: string; member: string; taken_at: string | null };

export const addVitals = (v: { member: string; temp_c?: number; bp_sys?: number; bp_dia?: number; pulse?: number; spo2?: number }) =>
  call<Assessment>("/api/care/vitals", { method: "POST", body: JSON.stringify(v) });
export const getVitals = (member?: string) => call<Vital[]>(`/api/care/vitals?${qs({ member })}`);
export function scanPrescription(file: File) {
  const form = new FormData();
  form.append("image", file);
  return call<{ medicines: RxMed[]; advice: { en: string; hi: string }[]; lines: string[] }>("/api/care/prescription/scan", { method: "POST", body: form });
}
export const savePlan = (p: { member: string; doctor?: string; diagnosis?: string; advice: string[]; medicines: RxMed[] }) =>
  call<{ id: number; flagged_batches: string[] }>("/api/care/plans", { method: "POST", body: JSON.stringify(p) });
export const getPlans = () => call<Plan[]>("/api/care/plans");
export const deletePlan = (id: number) => call(`/api/care/plans/${id}`, { method: "DELETE" });
export const getToday = () => call<{ day: string; doses: Dose[]; advice: string[] }>("/api/care/today");
export type PurchaseResult = { verdict: "alert_found" | "no_alert_found"; due_now: boolean; next_time: string | null; message_status: "sent" | "outbox" | "failed" | "capped"; whatsapp?: string };
export type Entitlement = { tier: "free" | "basic" | "family" | "pharmacy" | "pharmacy_pro"; plan: string; trial_days_left: number | null; members: number; wa: number };
export const getEntitlement = () => call<Entitlement>("/api/account/entitlement");
export const recordPurchase = (p: { med_id: number; batch: string; maker?: string; expiry?: string; pharmacy?: string; phone?: string; language: string; qty?: number }) =>
  call<PurchaseResult>("/api/care/purchase", { method: "POST", body: JSON.stringify(p) });
export const markDose = (med_id: number, slot: string, taken: boolean) =>
  call("/api/care/doses", { method: "POST", body: JSON.stringify({ med_id, slot, taken }) });
export const getReport = (member: string) =>
  call<{ member: string; generated_at: string; vitals: Vital[]; plans: Plan[]; adherence: { name: string; due: number; taken: number }[] }>(`/api/care/report?${qs({ member })}`);

export const getWatchlist = () => call<WatchItem[]>("/api/watchlist");
export const addWatch = (w: { batch: string; brand?: string; maker?: string; phone?: string; name?: string; language?: string; member?: string; expiry?: string }) =>
  call<{ verdict: string }>("/api/watchlist", { method: "POST", body: JSON.stringify(w) });
export const recheckWatchlist = () => call<{ changed: string[]; items: WatchItem[] }>("/api/watchlist/recheck", { method: "POST" });
export const removeWatch = (batch: string) => call(`/api/watchlist/${encodeURIComponent(batch)}`, { method: "DELETE" });

export const SOURCE_LABEL: Record<Alert["source"], string> = {
  cdsco_nsq: "CDSCO NSQ",
  cdsco_spurious: "CDSCO spurious",
  state_nsq: "State NSQ",
};

export function formatIST(iso: string) {
  return (
    new Date(iso.endsWith("Z") || iso.includes("+") ? iso : iso.replace(" ", "T") + "Z").toLocaleString("en-IN", {
      timeZone: "Asia/Kolkata",
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }) + " IST"
  );
}

// Empty database (fresh install, before the first ingest): no month yet, so nothing to show rather than a crash.
export function formatMonth(ym: string | null | undefined) {
  if (!ym) return "";
  const [y, m] = ym.split("-").map(Number);
  return new Date(y, m - 1).toLocaleString("en-IN", { month: "long", year: "numeric" });
}

// ---- early signal ----
export type SignalSymptom = { key: string; en: string; hi: string; n: number; share: number; prr: number | null; chi2: number | null; flagged: boolean; red_flag: boolean };
export type Signal = {
  batch: string; batch_norm: string; brand: string | null; maker: string | null; reports: number; red_flag_reports: number;
  cities: string[]; first_report: string; last_report: string; level: "urgent" | "signal" | "watch"; method: "prr" | "cluster";
  symptoms: SignalSymptom[]; not_working: number; simulated: boolean;
  regulator: { alert_month: string; category: string; product_name: string } | null; ahead_of_regulator: boolean;
};
export type Signals = { reports: number; batches: number; cities: number; min_reports: number; signals: Signal[]; symptoms: { key: string; en: string; hi: string }[] };
export const getSignals = () => call<Signals>("/api/signals");
export const signalsCsvUrl = () => `${API_URL}/api/signals.csv`;
export const sendReport = (r: { batch: string; brand?: string; maker?: string; city?: string; symptoms: string[]; onset_days?: number }) =>
  call<{ ok: boolean; reports_for_batch: number }>("/api/reports", { method: "POST", body: JSON.stringify(r) });

// ---- billing ----
export type PlanInfo = { id: string; name: string; amount: number; interval: "month" | "year"; who: string; features: string[] };
export type ActivePlan = { plan: string; paid_at: string; email: string | null } | null;
export const getPlansBilling = () => call<{ ready: boolean; test_mode: boolean; currency: string; plans: PlanInfo[]; active: ActivePlan }>("/api/billing/plans");
export const startCheckout = (plan: string) => call<{ url: string }>("/api/billing/checkout", { method: "POST", body: JSON.stringify({ plan }) });
export const confirmPayment = (session_id: string) => call<{ paid: boolean; active: ActivePlan }>(`/api/billing/confirm?${qs({ session_id })}`);
export const rupees = (paise: number) => "₹" + (paise / 100).toLocaleString("en-IN");

// ---- SOS ----
export type Contact = { id: number; name: string; phone: string; relation: string | null };
export type SosCard = { member: string; medicines: { name: string; strength: string; morning: number; noon: number; night: number; batch: string | null; doctor: string | null }[]; last_vitals: Omit<Vital, "id" | "member"> | null };
export const getContacts = () => call<Contact[]>("/api/sos/contacts");
export const addContact = (c: { name: string; phone: string; relation?: string }) => call("/api/sos/contacts", { method: "POST", body: JSON.stringify(c) });
export const removeContact = (id: number) => call(`/api/sos/contacts/${id}`, { method: "DELETE" });
export const getSosCard = (member: string) => call<SosCard>(`/api/sos/card?${qs({ member })}`);
export const triggerSos = (b: { member: string; lat?: number; lng?: number }) =>
  call<{ id: number; message: string; deliveries: { name: string; phone: string; status: string; link: string | null }[] }>("/api/sos", { method: "POST", body: JSON.stringify(b) });

// ---- admin ----
export type AdminOverview = {
  users: number;
  payments: { ready: boolean; test_mode: boolean; mrr: number; lifetime: number; active_by_plan: { plan: string; name: string; n: number; amount: number }[];
    recent: { plan: string; amount: number; currency: string; status: string; email: string | null; created_at: string; paid_at: string | null }[] };
  sos: { id: number; member: string; lat: number | null; lng: number | null; delivered: number; at: string; resolved_at: string | null }[];
  sos_open: number; vitals_urgent_7d: number; vitals_7d: number; checkins_urgent: number;
  signals: { flagged: number; reports: number }; watchlist: number; flagged_watch: number;
  data: { alerts: number; start: string; end: string; last_ingest: string | null }; recall_runs: number; notifications: number;
};
const adminHeaders = (token: string) => (token ? { "X-Admin-Token": token } : undefined);
export const getAdmin = (token: string) => call<AdminOverview>("/api/admin/overview", { headers: adminHeaders(token) });
export const resolveSos = (id: number, token: string) => call(`/api/admin/sos/${id}/resolve`, { method: "POST", headers: adminHeaders(token) });
export const adminIngest = (token: string) => call("/api/admin/ingest", { method: "POST", headers: adminHeaders(token) });

// ---- same medicine, lower price ----
export type MakerRecord = { alerts: number; spurious: number; last: string | null };
export type Medicine = {
  id: number; name: string; price: number | null; maker: string; pack: string; salts: string; salt_key: string; form: string;
  qty: number | null; unit: string; unit_price: number | null; maker_record: MakerRecord; saving_pct?: number | null;
};
export type Alternatives = {
  medicine: Medicine; brands: number; rank: number | null; unit_price: { min: number | null; median: number | null; max: number | null };
  cheapest_clean: Medicine | null; alternatives: Medicine[];
};
export type Savings = {
  items: { name: string; matched: Medicine | null; estimated?: boolean; cheapest?: Medicine; monthly_now?: number; monthly_cheapest?: number }[];
  monthly_now: number; monthly_cheapest: number; yearly_saving: number;
};
export const searchMedicines = (q: string) => call<Medicine[]>(`/api/medicines/search?${qs({ q })}`);
export const getAlternatives = (id: number) => call<Alternatives>(`/api/medicines/${id}/alternatives`);
export const getCareSavings = (member?: string) => call<Savings>(`/api/care/savings?${qs({ member })}`);

// ---- medicine info, refills, Jan Aushadhi, phone notifications ----
export type LabelText = Partial<Record<"uses" | "how_to_take" | "side_effects" | "warnings" | "do_not_take" | "pregnancy" | "label_name", string>>;
export type MedInfo = {
  medicine: Medicine;
  salts: { name: string; label_name: string; label: LabelText | null }[];
  alerts: { salt: string | null; total: number; spurious: number; recent: { id: number; product_name: string; batch_no: string; manufacturer: string | null; category: "nsq" | "spurious"; reason: string | null; alert_month: string }[] };
  price: { brands: number; rank: number | null; unit_price: Alternatives["unit_price"]; cheapest_clean: Medicine | null };
  source: string;
};
export const getMedicineInfo = (id: number) => call<MedInfo>(`/api/medicines/${id}/info`);

export type Refill = { med_id: number; name: string; strength: string; member: string; left: number; per_day: number; days_left: number; course_days_left: number | null; low: boolean; reminded_at: string | null };
export const getRefills = () => call<Refill[]>("/api/care/refills");

export type Store = { name: string; address: string | null; phone: string | null; hours: string | null; lat: number; lon: number; km: number; directions: string };
export const getJanAushadhi = (lat: number, lon: number) =>
  call<{ stores: Store[]; error: string | null; maps_search: string; source: string }>(`/api/stores/janaushadhi?${qs({ lat, lon })}`);

export const getWhatsAppInfo = () => call<{ provider: "meta" | "twilio" | null; join_url: string | null; template: boolean }>("/api/whatsapp/info");
export const getPushKey = () => call<{ key: string | null; subscribed: boolean }>("/api/push/key");
export const savePushSub = (sub: PushSubscriptionJSON) => call("/api/push/subscribe", { method: "POST", body: JSON.stringify(sub) });
export const testPush = () => call<{ sent: number }>("/api/push/test", { method: "POST" });
export const perUnit = (m: Pick<Medicine, "unit_price" | "unit">) =>
  m.unit_price == null ? "-" : `₹${m.unit_price < 10 ? m.unit_price.toFixed(2) : m.unit_price.toFixed(1)}/${m.unit === "ml" ? "ml" : m.unit === "gm" ? "g" : m.unit}`;

// ---- live vitals + doctor connect ----
export type LiveSource = "ble_hr" | "ble_oximeter" | "camera" | "replay";
export type ReferenceSummary = {
  id: string; age: number | null; gender: string | null; location: string | null; seconds: number;
  summary: { pulse_avg: number | null; pulse_min: number | null; pulse_max: number | null; spo2_min: number | null; spo2_avg: number | null; resp_avg: number | null; seconds_spo2_below_92: number; seconds_pulse_above_100: number };
  validation: { windows: number; estimated: number; mae: number | null; within5?: number };
};
export type ReferenceRecord = Omit<ReferenceSummary, "validation" | "seconds"> & {
  hz: number; worst_second: number; pleth: number[];
  numerics: { hr: number | null; pulse: number | null; resp: number | null; spo2: number | null }[];
};
export const getReferenceRecords = () =>
  call<{ dataset: { name: string; url: string; license: string; cite: string }; records: ReferenceSummary[];
    validation: { records: number; windows: number; estimated: number; mae: number | null; within5: number | null } | null }>("/api/reference/records");
export const getReferenceRecord = (id: string) => call<ReferenceRecord>(`/api/reference/records/${encodeURIComponent(id)}`);
export type LiveAck = { accepted: number; pulse: number | null; spo2: number | null; assessment: Assessment; saved_to_history: boolean };
export const sendLive = (member: string, source: LiveSource, samples: { pulse?: number; spo2?: number }[]) =>
  call<LiveAck>("/api/care/live", { method: "POST", body: JSON.stringify({ member, source, samples }) });

export type DoctorLink = { token: string; member: string; doctor: string | null; created_at?: string; expires_at: string; last_seen?: string | null; room?: string };
export type DoctorMessage = { id: number; token: string; member: string; author: "doctor" | "patient"; kind: "note" | "advice" | "followup" | "urgent" | "call"; text: string; at: string; read_at: string | null };
export type News2 = { score: number; risk: "low" | "low-medium" | "medium" | "high"; action: string; parts: Record<string, number>; partial: boolean; missing: string[] };
export type Latest = { temp_c: number | null; bp_sys: number | null; bp_dia: number | null; pulse: number | null; spo2: number | null; at: Record<string, string> };
export type LiveSample = { id: number; at: string; pulse: number | null; spo2: number | null; source: string };
export type DoctorView = {
  member: string; doctor: string | null; expires_at: string; room: string; latest: Latest; assessment: Assessment; news2: News2;
  stats_24h: { n: number; pmin: number | null; pmax: number | null; pavg: number | null; smin: number | null; savg: number | null; dips: number | null; tachy: number | null };
  vitals: (Vital & { source?: string })[]; plans: Plan[]; adherence: { name: string; due: number; taken: number }[];
  sos: { id: number; lat: number | null; lng: number | null; at: string; resolved_at: string | null }[]; messages: DoctorMessage[];
};
export const createDoctorLink = (b: { member: string; doctor?: string; hours: number }) =>
  call<DoctorLink & { room: string }>("/api/doctor/links", { method: "POST", body: JSON.stringify(b) });
export const getDoctorLinks = () => call<DoctorLink[]>("/api/doctor/links");
export const revokeDoctorLink = (token: string) => call(`/api/doctor/links/${encodeURIComponent(token)}`, { method: "DELETE" });
export const getDoctorView = (token: string) => call<DoctorView>(`/api/doctor/${encodeURIComponent(token)}`);
export const getDoctorLive = (token: string, since: number, msg_since: number) =>
  call<{ samples: LiveSample[]; online: boolean; source: string | null; latest: Latest; news2: News2; messages: DoctorMessage[] }>(
    `/api/doctor/${encodeURIComponent(token)}/live?${qs({ since, msg_since })}`);
export const getDoctorInteractions = (token: string) =>
  call<{ interactions: Interaction[]; no_label: string[]; source: string }>(`/api/doctor/${encodeURIComponent(token)}/interactions`);
export const doctorSend = (token: string, b: { kind: DoctorMessage["kind"]; text: string; doctor?: string }) =>
  call<{ id: number; added_to_plan: boolean }>(`/api/doctor/${encodeURIComponent(token)}/messages`, { method: "POST", body: JSON.stringify(b) });
export const getCareMessages = () => call<{ messages: DoctorMessage[]; unread: number }>("/api/care/messages");
export const patientSend = (b: { token: string; text: string; kind?: "note" | "call" }) =>
  call<{ id: number }>("/api/care/messages", { method: "POST", body: JSON.stringify(b) });
export const markMessagesRead = () => call("/api/care/messages/read", { method: "POST" });
export const videoUrl = (room: string) => `https://meet.jit.si/${room}`;

export type Interaction = { a: string; b: string; section: string; severity: "high" | "check"; evidence: string };
export const getInteractions = (names?: string[]) =>
  call<{ interactions: Interaction[]; no_label: string[]; source: string }>(`/api/care/interactions?${qs({ names: names?.join(",") })}`);
export const getNotifications = (limit = 10) =>
  call<{ id: number; channel: string; name: string; phone: string | null; message: string; status: string; created_at?: string }[]>(`/api/notifications?limit=${limit}`);

// ---- recall blast radius + body signal ----
export type VitalChange = { key: "pulse" | "spo2" | "bp_sys" | "temp_c"; label: string; unit: string; before: number; after: number; delta: number; flagged: boolean };
export type BodySignal = { enough: boolean; before: number; after: number; changes: VitalChange[]; flagged?: VitalChange[] };
export type Holder = {
  key: string; source: "care" | "pharmacy" | "watchlist"; name: string; phone: string | null; city: string | null; medicine: string | null;
  since: string | null; doses_taken: number | null; next_dose: string | null; next_slot: string | null; minutes: number | null;
  body: BodySignal | null; simulated: boolean; alert: { status: string; at: string } | null;
};
export type BlastView = {
  alert: Alert; explain: Failure[]; batch: string; holders: Holder[];
  summary: { holders: number; due_1h: number; due_6h: number; due_24h: number; alerted: number; doses_taken: number; with_vitals: number; reacting: number; top_change: string | null; simulated: number };
};
export type BlastInboxItem = { batch_norm: string; batch_no: string; medicine: string; maker: string | null; category: "nsq" | "spurious"; month: string; reason: string | null };
export const getBlastInbox = () => call<BlastInboxItem[]>("/api/blast");
export const getBlast = (batch: string) => call<BlastView>(`/api/blast/${encodeURIComponent(batch)}`);
export const blastAlert = (batch: string) => call<{ alerted: { key: string; status: string; minutes: number | null }[]; count: number }>(`/api/blast/${encodeURIComponent(batch)}/alert`, { method: "POST" });
export const blastDemo = (batch: string, holders = 24) => call<{ seeded: number }>(`/api/blast/${encodeURIComponent(batch)}/demo?holders=${holders}`, { method: "POST" });
export const clearBlastDemo = (batch: string) => call(`/api/blast/${encodeURIComponent(batch)}/demo`, { method: "DELETE" });
export type BatchEffect = BodySignal & { med_id: number; name: string; member: string; batch: string; since: string };
export const getBatchEffects = () => call<BatchEffect[]>("/api/care/batch-effects");

// ---- phone login ----
export type Role = "patient" | "pharmacist" | "regulator" | "admin";
export type Me = { phone: string | null; masked: string | null; roles: Role[]; permissions: string[] };
export const authMe = () => call<Me>("/api/auth/me");
export const authStart = (phone: string) => call<{ sent: boolean; channel: "whatsapp" | "demo"; demo_code?: string }>("/api/auth/start", { method: "POST", body: JSON.stringify({ phone }) });
export const authVerify = (phone: string, code: string) => call<{ signed_in: boolean; new: boolean; merged: number; masked: string }>("/api/auth/verify", { method: "POST", body: JSON.stringify({ phone, code }) });
export type SessionInfo = { id: string; kind: "guest" | "user"; label: string; created_at: string; last_seen: string; current: boolean };
export const getSessions = () => call<SessionInfo[]>("/api/auth/sessions");
export const endSession = (id: string) => call(`/api/auth/sessions/${encodeURIComponent(id)}`, { method: "DELETE" });
export const signOutOthers = () => call<{ ended: number }>("/api/auth/logout-others", { method: "POST" });
// ---- your data (DPDP Act 2023) ----
export const exportMyData = () => call<{ generated_at: string; data: Record<string, unknown[]> }>("/api/account/export");
export const eraseMyData = () => call<{ deleted: Record<string, number>; sessions_ended: number }>("/api/account", { method: "DELETE" });

/** Ends this session on the server; the next request starts a fresh, empty guest session. */
export async function signOut() {
  await request("/api/auth/logout", { method: "POST" }, false).catch(() => {});
}

// ---- WhatsApp bot, simulated phone (same code as the real webhook; nothing is sent) ----
export type WaRead = { batch: string | null; brand: string | null; maker: string | null; expiry: string | null; verdict?: string };
export const waSimulateText = (text: string) =>
  call<{ reply: string }>(`/api/whatsapp/simulate?${qs({ text })}`, { method: "POST" });
export function waSimulatePhoto(file: Blob) {
  const form = new FormData();
  form.append("image", file, "photo.png");
  return call<{ reply: string; read: WaRead }>("/api/whatsapp/simulate", { method: "POST", body: form });
}

// ---- fake-pack radar ----
export type PackVerdict = { level: "ok" | "watch" | "clone"; reasons: { kind: "mismatch" | "far" | "phones"; text: string }[]; scans: number; phones: number;
  cities: string[]; first_at: string; last_at: string; seen_before: boolean; you_before: boolean };
export type RadarRing = Omit<PackVerdict, "seen_before" | "you_before"> & { serial: string; gtin: string | null; batch: string | null; simulated: boolean;
  points: { lat: number; lng: number; city: string | null; at: string; batch: string | null }[] };
export type Radar = { scans: number; packs: number; phones: number; clones: number; rings: RadarRing[]; cities: { name: string; lat: number; lng: number }[] };
export const packScan = (b: { serial: string; gtin?: string | null; batch?: string | null; expiry?: string | null; lat?: number; lng?: number }) =>
  call<PackVerdict>("/api/packs/scan", { method: "POST", body: JSON.stringify(b) });
export const getRadar = () => call<Radar>("/api/packs/radar");
export const seedRadarDemo = () => call<{ seeded: number }>("/api/packs/demo", { method: "POST" });
export const clearRadarDemo = () => call<{ cleared: number }>("/api/packs/demo", { method: "DELETE" });

// ---- drug-controller dashboard ----
type NameN2 = { name: string; n: number };
export type ControllerAction = { kind: "recall" | "counterfeit" | "signal" | "checkin"; severity: number; title: string; detail: string; href: string; simulated: boolean };
export type Controller = {
  state: string | null; states: NameN2[]; as_of: string;
  kpis: { alerts_12m: number; alerts_prev_12m: number; spurious_12m: number; critical_24m: number; median_lag_months: number | null; lag_sample: number;
    batches_in_homes: number; people_holding: number; people_alerted: number; copied_codes: number; signals: number; urgent_checkins: number };
  trend: { month: string; n: number }[]; failures: NameN2[]; groups: NameN2[]; makers: NameN2[];
  held: { batch_norm: string; batch_no: string; medicine: string; maker: string; category: string; month: string; holders: number; alerted: number; due_24h: number; reacting: number; simulated: number }[];
  actions: ControllerAction[]; scope_note: string; generated_at: string;
};
export const getController = (state?: string) => call<Controller>(`/api/controller?${qs({ state })}`);
export type IngestRun = { trigger: string; started_at: string; finished_at: string | null; status: string; alerts_before: number | null; alerts_after: number | null; error: string | null };
export type Quality = {
  alerts_in_db: number; sampled_alerts: number; positive_probes: number; recall_pct: number; near_miss_probes: number; clean_probes: number;
  false_alarms: number; precision_pct: number; wrong_maker_probes: number; wrong_maker_marked_strong: number; right_maker_probes: number;
  right_maker_strong_pct: number; check_ms_p50: number; check_ms_p95: number; seed: number;
};
export type SystemStatus = {
  ok: boolean; uptime_s: number; tests: number;
  data: { alerts: number; spurious: number; documents: number; makers: number; medicines: number; latest_list: string; first_list: string; db_mb: number; journal: string };
  ingest: { next_nightly: string; runs: IngestRun[] };
  quality: Quality;
  strip_ocr: { generated_at: string; sets: Record<string, { photos: number; batch_pct: number; expiry_pct: number; brand_pct: number; median_ms: number }> } | null;
  latency: { requests: number; p50_ms: number | null; p95_ms: number | null; p99_ms: number | null; server_errors: number; routes: { path: string; n: number; p50_ms: number; p95_ms: number }[] };
};
export const getStatus = (refreshQuality = false) => call<SystemStatus>(`/api/status${refreshQuality ? "?refresh_quality=true" : ""}`);
export const demoReset =() => call<{ ok: boolean; copied_code_scans: number; symptom_reports: number }>("/api/admin/demo-reset", { method: "POST" });

// ---- Dadi mode: one conversation, spoken or typed (also on Telegram) ----
export type DadiKind = "emergency" | "hello" | "batch_alert" | "batch_clean" | "doses" | "price" | "uses" | "help" | "taken" | "nothing_due"
  | "vitals_ok" | "vitals_doctor" | "vitals_urgent" | "family" | "family_none" | "nudge";
export type DadiAnswer = {
  kind: DadiKind; say: string; show: string;
  data: { medicine?: Medicine; cheapest?: Medicine | null; batch?: string; common_use?: string | null; salt_alerts?: number; told?: string[];
    dose?: { name: string; member: string; time: string } | null; pending?: Dose[] };
};
export type DadiMsg = { id: number; member: string; role: "me" | "kincare" | "family"; text: string; kind: DadiKind | null; data: DadiAnswer["data"]; channel: "app" | "telegram"; at: string };
export const dadiChat = (text: string, lang: "hi" | "en", member = "Me") =>
  call<DadiAnswer>("/api/dadi/chat", { method: "POST", body: JSON.stringify({ text, lang, member }) });
export const dadiHistory = () => call<DadiMsg[]>("/api/dadi/history");
export const dadiMe = () => call<{ member: string; members: string[] }>("/api/dadi/me");
export const dadiClear = () => call("/api/dadi/history", { method: "DELETE" });

// ---- Telegram: the free chat + alert channel ----
export const getTelegramInfo = () => call<{ ready: boolean; bot: string | null; linked: number }>("/api/telegram/info");
export const telegramLink = (role: "self" | "caregiver") => call<{ url: string; code: string }>(`/api/telegram/link?${qs({ role })}`, { method: "POST" });
export const telegramUnlink = () => call<{ removed: number }>("/api/telegram/link", { method: "DELETE" });

// ---- caregivers: consent-based family view ----
export type Scope = "doses" | "vitals" | "sos";
export type CareLink = { id: number; member: string; elder_name: string | null; caregiver_name: string; relation: string | null; scopes: Scope[]; created_at: string; last_seen?: string | null };
export type CgDose = Dose & { state: "taken" | "due" | "missed" };
export type ElderView = {
  link: CareLink;
  doses: null | { today: CgDose[]; adherence: number | null; week: { day: string; due: number; taken: number; missed: string[] }[];
    medicines: { name: string; strength: string; food: string; doctor: string | null; diagnosis: string | null; schedule: string; as_needed: boolean }[] };
  vitals: null | { latest: (Vital & { source: string }) | null; history: (Vital & { source: string })[] };
  sos: null | { last: { at: string; lat: number | null; lng: number | null; resolved_at: string | null } | null };
};
export type AccessEntry = { action: "viewed" | "nudged" | "linked" | "revoked" | "alerted"; detail: string | null; at: string; caregiver_name: string; relation: string | null };
export const getScopes = () => call<{ key: Scope; label: string }[]>("/api/caregiver/scopes");
export const createInvite = (b: { member: string; elder_name?: string; scopes: Scope[] }) =>
  call<{ code: string; url: string; expires_at: string; scopes: Scope[] }>("/api/caregiver/invite", { method: "POST", body: JSON.stringify(b) });
export const previewInvite = (code: string) =>
  call<{ code: string; elder_name: string; member: string; scopes: { key: Scope; label: string }[]; expires_at: string }>(`/api/caregiver/invite/${encodeURIComponent(code.trim().toUpperCase())}`);
export const acceptInvite = (b: { code: string; name: string; relation?: string }) =>
  call<{ link_id: number; elder_name: string }>("/api/caregiver/accept", { method: "POST", body: JSON.stringify({ ...b, code: b.code.trim().toUpperCase() }) });
export const getCareLinks = () => call<{ caregivers: CareLink[]; watching: CareLink[] }>("/api/caregiver/links");
export const revokeLink = (id: number) => call<{ ok: boolean; by: string }>(`/api/caregiver/links/${id}`, { method: "DELETE" });
export const getAccessLog = () => call<AccessEntry[]>("/api/caregiver/access");
export const getElder = (id: number) => call<ElderView>(`/api/caregiver/elder/${id}`);
export const nudgeElder = (id: number, text?: string) =>
  call<{ phone: number; telegram: number; in_app: boolean }>(`/api/caregiver/elder/${id}/nudge`, { method: "POST", body: JSON.stringify({ text }) });

// ---- roles (pharmacist, regulator, admin) ----
export type RoleGrant = { id: number; role: Role; status: "pending" | "active" | "rejected" | "revoked"; org: string | null; licence: string | null; requested_at: string; decided_at: string | null };
export const myRoles = () => call<RoleGrant[]>("/api/roles/mine");
export const requestRole = (role: "pharmacist" | "regulator", org: string, licence: string) =>
  call<{ id: number; status: RoleGrant["status"] }>("/api/roles/request", { method: "POST", body: JSON.stringify({ role, org, licence }) });
export type RoleQueueItem = RoleGrant & { phone: string | null; decided_by: string | null };
export const adminRoles = (token: string) => call<RoleQueueItem[]>("/api/admin/roles", { headers: adminHeaders(token) });
export const adminDecideRole = (id: number, decision: "approve" | "reject" | "revoke", token: string) =>
  call(`/api/admin/roles/${id}/${decision}`, { method: "POST", headers: adminHeaders(token) });
export const adminGrantRole = (phone: string, role: Role, token: string) =>
  call<{ ok: boolean; already?: boolean }>("/api/admin/roles/grant", { method: "POST", headers: adminHeaders(token), body: JSON.stringify({ phone, role }) });
export type AuditEntry = { id: number; at: string; actor: string; role: string | null; action: string; target: string | null; detail: string | null };
export const adminAudit = (token: string) => call<AuditEntry[]>("/api/admin/audit", { headers: adminHeaders(token) });

// ---- Switch: the Care Network (family rooms + Pharmacy Desk), computed by the same logic the agents run ----

export type NetMedicine = { person: string; brand: string; batch: string; maker?: string; times: string[]; flagged: boolean };
export type NetFamily = { name: string; caregiver: string; default: boolean; medicines: NetMedicine[] };
export type NetHolder = { family: string; caregiver: string; person: string; times: string[]; room_id: string; default: boolean };
export type NetOption = { id: number; name: string; maker: string; price: number; pack: string; salts: string; unit_price: number };
export type NetFlagged = {
  batch: string; brand: string;
  doctor: { required: boolean; why: string };
  holders: NetHolder[];
  alert: { category: string; product_name: string; reason: string; manufacturer: string; reported_by: string;
           alert_month: string; mfg_date: string; expiry: string; alert_url: string };
  options: NetOption[]; salts: string[]; strengths: string[]; note: string;
};
export type NetAgent = { name: string; label: string; kind: string; job: string };
export type SwitchNetwork = {
  pharmacy: string; pharmacist: string; families: NetFamily[]; flagged: NetFlagged[]; checked: number;
  documents: { decisions: { family: string; text: string }[]; tasks: { family: string; text: string; done: boolean }[] };
  agents: NetAgent[];
};

export const getSwitchNetwork = () => call<SwitchNetwork>("/api/switch/network");
