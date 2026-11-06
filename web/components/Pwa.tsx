"use client";

import { useEffect } from "react";
import { registerSw } from "@/lib/push";

/** Registers the service worker (phone notifications for doses, refills and recalls). KinCare stays a website:
 *  the browser's own "Install app" banner is suppressed so nothing pushes an app download. */
export function ServiceWorker() {
  useEffect(() => {
    registerSw();
    const quiet = (e: Event) => e.preventDefault();
    window.addEventListener("beforeinstallprompt", quiet);
    return () => window.removeEventListener("beforeinstallprompt", quiet);
  }, []);
  return null;
}
