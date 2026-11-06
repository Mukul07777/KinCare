import type { NextConfig } from "next";

// The browser only ever talks to this site. /api/* is forwarded to the KinCare API, so the session cookie is first-party,
// HttpOnly and SameSite, and the API needs no cross-origin access at all. KINCARE_API_URL is read on the server only.
const API = (process.env.KINCARE_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
const dev = process.env.NODE_ENV !== "production";

const CSP = [
  "default-src 'self'",
  // Next.js inlines its bootstrap scripts; dev mode also needs eval for fast refresh.
  `script-src 'self' 'unsafe-inline'${dev ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "font-src 'self' data:",
  "connect-src 'self'",                                   // every API call goes through /api on this origin
  "media-src 'self' blob:",
  "worker-src 'self'",
  "frame-src https://*.tinyfish.ai https://tinyfish.ai",  // live view of the recall agents on /live
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "object-src 'none'",
  ...(dev ? [] : ["upgrade-insecure-requests"]),
].join("; ");

const nextConfig: NextConfig = {
  poweredByHeader: false,
  // Test and preview servers build into their own folder (NEXT_DIST_DIR) so they never overwrite the running site in .next.
  distDir: process.env.NEXT_DIST_DIR || ".next",
  // OCR on a full phone photo can take longer than the 30 s default before /api/scan answers.
  experimental: { proxyTimeout: 120_000 },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API}/api/:path*` }];
  },
  async headers() {
    return [{
      source: "/:path*",
      headers: [
        { key: "Content-Security-Policy", value: CSP },
        { key: "X-Content-Type-Options", value: "nosniff" },
        { key: "X-Frame-Options", value: "DENY" },
        { key: "Referrer-Policy", value: "no-referrer" },  // doctor and check-in links carry their token in the URL
        { key: "Permissions-Policy", value: "camera=(self), microphone=(self), geolocation=(self), payment=()" },
        { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
        ...(dev ? [] : [{ key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains; preload" }]),
      ],
    }];
  },
};

export default nextConfig;
