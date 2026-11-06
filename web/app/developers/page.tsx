import Link from "next/link";
import { ArrowUpRight, Code2, Webhook } from "lucide-react";
import { Eyebrow, Heading } from "@/components/Heading";
import { PUBLIC_API_URL as API_URL } from "@/lib/api";

const ENDPOINTS = [
  { method: "GET", path: "/api/check?batch=05240198&brand=Telma H", what: "Is this batch named in any regulator alert? Returns verdict, sources, match scores and a plain-language explanation." },
  { method: "POST", path: "/api/inventory/check", what: "Check a whole stock list at once (JSON array of {product, batch, maker, qty}). For pharmacy software and e-pharmacies." },
  { method: "POST", path: "/api/scan", what: "Upload a strip photo; returns batch, brand, maker and expiry read by OCR." },
  { method: "POST", path: "/api/scan/bill", what: "Upload a pharmacy bill; every batch on it is checked." },
  { method: "GET", path: "/api/alerts?q=paracetamol&category=nsq", what: "Search every published NSQ / spurious finding since 2019, with source links." },
  { method: "GET", path: "/api/manufacturer?name=Cipla", what: "A manufacturer's alert history, with every spelling variant grouped and shown." },
  { method: "GET", path: "/api/insights", what: "National breakdown by failure type, drug group, dosage form and testing state." },
  { method: "POST", path: "/api/recall/run", what: "Run a recall: read sources, match holders, notify. Stream progress from /api/recall/stream/{run_id} (SSE)." },
];

export default function DevelopersPage() {
  return (
    <main className="blush mx-auto max-w-5xl px-4 pt-12 sm:px-6 sm:pt-16">
      <Eyebrow>For developers</Eyebrow>
      <Heading as="h1" lead="The drug-alert API" tail="India never had." className="mt-4 text-4xl sm:text-6xl" />
      <p className="mt-4 max-w-2xl text-muted">
        Plug regulator alerts into pharmacy billing software, hospital procurement or e-pharmacy inventory. Every response links back to the regulator’s own source.
      </p>

      <div className="mt-8 flex flex-wrap gap-3">
        <a href={`${API_URL}/docs`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 rounded-full bg-brown px-5 py-3 text-sm font-medium text-paper hover:bg-brown-2">
          <Code2 className="size-4" /> Interactive API reference <ArrowUpRight className="size-4" />
        </a>
        <Link href="/pricing" className="rounded-full border border-espresso/15 bg-paper px-5 py-3 text-sm font-medium hover:border-brown hover:text-brown">API pricing</Link>
      </div>

      <div className="card mt-10 overflow-hidden rounded-[2rem]">
        {ENDPOINTS.map((e) => (
          <div key={e.path} className="grid gap-2 border-b border-line px-6 py-4 last:border-0 sm:grid-cols-[auto_1fr] sm:gap-6">
            <span className={`h-fit w-14 rounded-md py-1 text-center font-mono text-xs font-semibold ${e.method === "GET" ? "bg-safe/15 text-safe" : "bg-brown/10 text-brown"}`}>{e.method}</span>
            <div>
              <p className="break-all font-mono text-sm">{e.path}</p>
              <p className="mt-1 text-sm text-muted">{e.what}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <div className="rounded-3xl bg-espresso p-6 text-paper">
          <p className="text-sm text-paper/60">Example</p>
          <pre className="mt-3 overflow-x-auto text-xs leading-relaxed"><code>{`curl "${API_URL}/api/check?batch=05240198&brand=Telma%20H"

{
  "verdict": "alert_found",
  "matches": [{
    "alert": { "product_name": "Telma H ...",
               "category": "spurious",
               "alert_month": "2025-02",
               "alert_url": "https://cdsco.gov.in/..." },
    "score": { "level": "strong", "batch": 100 },
    "explain": [{ "label": "Possibly fake",
                  "severity": "critical" }]
  }]
}`}</code></pre>
        </div>
        <div className="card rounded-3xl p-6">
          <Webhook className="size-6 text-brown" />
          <p className="mt-4 text-lg font-medium tracking-tight">Recall webhooks (enterprise)</p>
          <p className="mt-2 text-sm leading-relaxed text-muted">
            Register your stock once. When a new regulator list names a batch you hold, KinCare calls your endpoint with the batch, the alert and the regulator link, so your POS can stop it at the counter.
          </p>
          <p className="mt-4 text-xs text-muted">Webhook delivery is on the roadmap; the matching engine behind it is live today.</p>
        </div>
      </div>
    </main>
  );
}
