import { getPushKey, savePushSub } from "@/lib/api";

export async function registerSw() {
  if (typeof navigator === "undefined" || !("serviceWorker" in navigator)) return null;
  try { return await navigator.serviceWorker.register("/sw.js"); } catch { return null; }
}

const toBytes = (b64: string) => {
  const s = atob((b64 + "=".repeat((4 - (b64.length % 4)) % 4)).replace(/-/g, "+").replace(/_/g, "/"));
  return Uint8Array.from(s, (c) => c.charCodeAt(0));
};

/** Ask permission, then subscribe this browser so the server can notify it with KinCare closed.
 *  Returns "push" (works when closed), "local" (only while open) or "denied". */
export async function enableNotifications(): Promise<"push" | "local" | "denied"> {
  if (typeof Notification === "undefined") return "denied";
  if ((await Notification.requestPermission()) !== "granted") return "denied";
  const reg = await registerSw();
  if (!reg || !("pushManager" in reg)) return "local";
  try {
    const { key } = await getPushKey();
    if (!key) return "local";
    await navigator.serviceWorker.ready;
    const sub = (await reg.pushManager.getSubscription()) ?? (await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: toBytes(key) }));
    await savePushSub(sub.toJSON());
    return "push";
  } catch {
    return "local";
  }
}

/** Show a notification now. Through the service worker when there is one, so the tag dedupes with server pushes. */
export async function notifyNow(title: string, body: string, tag: string) {
  try {
    const reg = await navigator.serviceWorker?.getRegistration();
    if (reg) return reg.showNotification(title, { body, tag, icon: "/icons/icon-192.png", data: { url: "/care" } });
    new Notification(title, { body, tag });
  } catch {}
}
