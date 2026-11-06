// KinCare service worker: phone notifications (doses, refills, recalls) and "install as app".
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));

self.addEventListener("push", (e) => {
  let d = {};
  try { d = e.data ? e.data.json() : {}; } catch { d = { body: e.data && e.data.text() }; }
  e.waitUntil(self.registration.showNotification(d.title || "KinCare", {
    body: d.body || "",
    tag: d.tag || undefined, // same tag replaces, so an open tab and a push never show twice
    icon: "/icons/icon-192.png",
    badge: "/icons/icon-192.png",
    data: { url: d.url || "/care" },
  }));
});

self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const url = new URL((e.notification.data && e.notification.data.url) || "/care", self.location.origin).href;
  e.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((tabs) => {
    const tab = tabs.find((t) => t.url.startsWith(self.location.origin));
    if (tab) { tab.navigate(url); return tab.focus(); }
    return self.clients.openWindow(url);
  }));
});
