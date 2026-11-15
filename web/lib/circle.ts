// Care circle client: the elder uses their normal session; family and caretakers send the X-Circle-Token they got
// by unlocking the profile with its passcode (kept in this browser only).
import { request } from "@/lib/api";

export type Med = { id: number; name: string; strength: string | null; food: string | null; morning: number; noon: number; night: number; days: number | null; as_needed: number };
export type Dose = { slot: "morning" | "noon" | "night"; time: string; med_id: number; name: string; strength: string | null; food: string | null; taken_at: string | null; state: "taken" | "missed" | "due" | "upcoming" };
export type Adherence = { pct_7: number | null; pct_30: number | null; streak_days: number; days: { day: string; due: number; taken: number; pct: number | null }[]; medicines: { med_id: number; name: string; due: number; taken: number; pct: number | null }[] };
export type Appt = { id: number; doctor: string; specialty: string | null; place: string | null; at: string; notes: string | null; status: string; gcal: string };
export type Change = { id: number; action: string; summary: string; member_name: string | null; at: string };
export type Activity = { who: string; action: string; detail: string | null; at: string };
export type Member = { id: number; name: string; email: string | null; role: string; can_edit: number; last_seen: string | null };
export type View = {
  profile: { code: string; elder_name: string; approve_changes: number };
  you: { name: string; role: "elder" | "family" | "caretaker"; can_edit: boolean };
  medicines: Med[]; today: Dose[]; adherence: Adherence; appointments: Appt[]; pending: Change[];
  circle: { name: string; role: string }[]; activity: Activity[];
};
export type OwnProfile = { code: string; member: string; elder_name: string; elder_email: string | null; approve_changes: number; members: Member[]; pending: Change[]; activity: Activity[] };

const KEY = (code: string) => `kincare:circle:${code.toUpperCase()}`;
export const getToken = (code: string) => { try { return localStorage.getItem(KEY(code)); } catch { return null; } };
export const setToken = (code: string, t: string | null) => { try { if (t) localStorage.setItem(KEY(code), t); else localStorage.removeItem(KEY(code)); } catch { /* private mode */ } };

async function call<T>(path: string, init: RequestInit = {}, code?: string): Promise<T> {
  const tok = code ? getToken(code) : null;
  const res = await request(path, { ...init, headers: { ...(tok ? { "X-Circle-Token": tok } : {}), ...init.headers } });
  if (!res.ok) throw new Error((await res.json().catch(() => null))?.detail ?? `Request failed (${res.status})`);
  return res.json();
}
const json = (method: string, body: unknown): RequestInit => ({ method, body: JSON.stringify(body) });

export const myProfiles = () => call<OwnProfile[]>("/api/circle/profiles");
export const createProfile = (b: { member: string; elder_name: string; elder_email?: string; passcode: string; approve_changes: boolean }) => call<OwnProfile>("/api/circle/profiles", json("POST", b));
export const updateProfile = (code: string, b: Partial<{ elder_email: string; approve_changes: boolean; passcode: string; sign_out_all: boolean }>) => call(`/api/circle/profiles/${code}`, json("PUT", b));
export const setMemberEdit = (code: string, id: number, can_edit: boolean) => call(`/api/circle/profiles/${code}/members/${id}`, json("PUT", { can_edit }));
export const removeMember = (code: string, id: number) => call(`/api/circle/profiles/${code}/members/${id}`, { method: "DELETE" });
export const decide = (code: string, id: number, approve: boolean) => call(`/api/circle/profiles/${code}/changes/${id}`, json("POST", { approve }));

export async function unlock(b: { code: string; passcode: string; name: string; email?: string; role: string }) {
  const r = await call<{ token: string; profile: string }>("/api/circle/unlock", json("POST", b));
  setToken(r.profile, r.token);
  return r.profile;
}
export const view = (code: string) => call<View>(`/api/circle/p/${code}`, {}, code);
export const note = (code: string, lang: string) => call<{ text: string; source: string }>(`/api/circle/p/${code}/note?lang=${lang}`, {}, code);
export const tick = (code: string, b: { med_id: number; slot: string; taken: boolean }) => call(`/api/circle/p/${code}/doses`, json("POST", b), code);
export const saveMed = (code: string, b: Partial<Med> & Record<string, unknown>, id?: number) =>
  call<{ status: "applied" | "pending"; summary: string }>(`/api/circle/p/${code}/meds${id ? `/${id}` : ""}`, json(id ? "PUT" : "POST", b), code);
export const deleteMed = (code: string, id: number) => call<{ status: string }>(`/api/circle/p/${code}/meds/${id}`, { method: "DELETE" }, code);
export const saveAppt = (code: string, b: Partial<Appt>, id?: number) => call(`/api/circle/p/${code}/appointments${id ? `/${id}` : ""}`, json(id ? "PUT" : "POST", b), code);
export const leave = (code: string) => call(`/api/circle/p/${code}/leave`, { method: "POST" }, code).finally(() => setToken(code, null));
