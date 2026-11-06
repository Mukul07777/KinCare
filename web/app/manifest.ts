import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "KinCare: know the batch, not just the brand",
    short_name: "KinCare",
    description: "Check medicine batches against regulator alerts, dose and refill reminders, cheaper same-salt brands.",
    start_url: "/care",
    display: "standalone",
    background_color: "#f7f1ec",
    theme_color: "#0f766e",
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
      { src: "/icons/icon-maskable.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
    shortcuts: [
      { name: "Scan a strip", url: "/scan" },
      { name: "Today's doses", url: "/care" },
      { name: "SOS", url: "/sos" },
    ],
  };
}
