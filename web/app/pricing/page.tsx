"use client";

import { useState } from "react";
import Link from "next/link";
import { Check, Info } from "lucide-react";
import { Eyebrow, Heading } from "@/components/Heading";

// Same prices and lists as api/billing.py (the server is the source of truth for checkout).
// Each plan includes everything in the one before it; Pharmacy Pro has every KinCare feature.
const TIERS: { name: string; who: string; price: string; per: string; featured?: boolean; badge?: string; cta: { label: string; href: string }; features: string[] }[] = [
  {
    name: "Free",
    who: "Anyone with a medicine strip",
    price: "₹0",
    per: "forever",
    cta: { label: "Scan a medicine", href: "/scan" },
    features: ["Starts with 14 days of Family free, no card", "Unlimited strip, bill and QR scans", "Batch check against every CDSCO and state alert", "Recall alerts on WhatsApp and a Hindi voice call",
      "Medicine info: uses, side effects, warnings", "Cheaper same-salt brands from makers with no alerts", "Jan Aushadhi store finder",
      "Phone notifications for doses and refills", "Watchlist for your batches", "SOS button with 112 / 108 and nearby hospitals"],
  },
  {
    name: "Basic",
    who: "One person on regular medicines",
    price: "₹29",
    per: "/month · ₹299/year",
    cta: { label: "Choose Basic", href: "/account" },
    features: ["Everything in Free, plus:", "WhatsApp dose reminders for 1 person (reply 1 to tick)", "Refill reminders with the cheapest clean brand",
      "Prescription scan into a dose schedule", "Drug-interaction check", "Private doctor link with live vitals and video consult", "Printable doctor report"],
  },
  {
    name: "Family",
    who: "A household caring for elders",
    price: "₹69",
    per: "/month · ₹699/year",
    featured: true,
    badge: "Most popular",
    cta: { label: "Choose Family", href: "/account" },
    features: ["Everything in Basic, plus:", "Up to 6 family members", "WhatsApp reminders on up to 3 numbers", "SOS alerts to family on WhatsApp with location",
      "Monthly medicine spend and savings for the whole family"],
  },
  {
    name: "Pharmacy",
    who: "One independent store",
    price: "₹499",
    per: "/month · ₹4,999/year",
    cta: { label: "Try the recall desk", href: "/pharmacy" },
    features: ["Everything in Family, plus:", "First month free", "Your customers get WhatsApp reminders free (Basic, on us)", "Stock CSV matched against every new alert", "Find customers who bought a flagged batch",
      "300 customer WhatsApp recall alerts a month", "Patient check-in queue after a recall", "Audit and PvPI exports"],
  },
  {
    name: "Pharmacy Pro",
    who: "Chains and hospital pharmacies",
    price: "₹1,499",
    per: "/month",
    badge: "All features",
    cta: { label: "Choose Pro", href: "/account" },
    features: ["Everything in Pharmacy, plus (all KinCare features):", "Multiple locations and staff logins", "2,000 customer WhatsApp alerts a month",
      "Early Signal reports: bad batches patients report before CDSCO lists them", "Live recall command screen", "Alert API access", "Priority support"],
  },
];

const ROADMAP = [
  ["0–30 days", "Prove the tech", "Scanner, alert database, source-linked matching, stock upload. Tested on known notices, including negative cases."],
  ["1–3 months", "Validate", "Pilots with 3–5 pharmacies. Aim for the first paying customers, not a large free-user count."],
  ["3–6 months", "Repeatable revenue", "Multi-branch support, scheduled monitoring, integrations with pharmacy software."],
  ["6–12 months", "Expand", "Hospital groups, distributors and the alert API, once coverage and match quality are proven."],
];

const inr = (n: number) => "₹" + Math.round(n).toLocaleString("en-IN");

function Slider({ label, value, set, max, step = 1, hint }: { label: string; value: number; set: (n: number) => void; max: number; step?: number; hint: string }) {
  return (
    <label className="block">
      <div className="flex items-baseline justify-between">
        <span className="text-sm">{label}</span>
        <span className="font-mono text-lg font-medium">{step >= 1000 ? inr(value) : value}</span>
      </div>
      <input type="range" min={0} max={max} step={step} value={value} onChange={(e) => set(Number(e.target.value))} className="mt-2 w-full accent-[#8a4b2c]" />
      <p className="text-xs text-muted">{hint}</p>
    </label>
  );
}

export default function PricingPage() {
  const [basic, setBasic] = useState(3000);
  const [fam, setFam] = useState(2000);
  const [starter, setStarter] = useState(50);
  const [pro, setPro] = useState(20);
  const [ent, setEnt] = useState(3);
  const [api, setApi] = useState(2);
  const [opex, setOpex] = useState(100000);

  const mrr = basic * 29 + fam * 69 + starter * 499 + pro * 1499 + ent * 30000 + api * 25000;
  const surplus = mrr - opex;
  const margin = mrr ? (surplus / mrr) * 100 : 0;

  return (
    <main className="blush mx-auto max-w-6xl px-4 pt-12 sm:px-6 sm:pt-16">
      <div className="grid items-end gap-6 md:grid-cols-2">
        <div>
          <Eyebrow>Business model</Eyebrow>
          <Heading as="h1" lead="Free for patients." tail="Paid for by pharmacies." className="mt-4 text-4xl sm:text-6xl" />
        </div>
        <p className="max-w-sm text-muted md:ml-auto">
          The same alert database powers a free consumer check and paid recall software for organisations. We charge for workflow, never for a patient’s safety check.
        </p>
      </div>

      {/* Tiers */}
      <div className="mt-12 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {TIERS.map((t) => (
          <div key={t.name} className={`card flex flex-col rounded-3xl p-6 ${t.featured ? "bg-brown text-paper ring-4 ring-brown/15" : ""}`}>
            <div className="flex items-center justify-between">
              <p className="font-medium">{t.name}</p>
              {t.badge && <span className={`rounded-full px-2.5 py-0.5 text-[11px] ${t.featured ? "bg-paper/20" : "bg-teal text-paper"}`}>{t.badge}</span>}
            </div>
            <p className={`text-sm ${t.featured ? "text-paper/70" : "text-muted"}`}>{t.who}</p>
            <p className="mt-6 text-4xl font-medium tracking-tight">
              {t.price}
              <span className={`ml-1 text-sm font-normal ${t.featured ? "text-paper/70" : "text-muted"}`}>{t.per}</span>
            </p>
            <ul className="mt-6 flex-1 space-y-2.5 text-sm">
              {t.features.map((f) => f.endsWith(":") ? (
                <li key={f} className={`text-xs font-semibold uppercase tracking-wide ${t.featured ? "text-paper/80" : "text-teal"}`}>{f}</li>
              ) : (
                <li key={f} className="flex gap-2">
                  <Check className={`mt-0.5 size-4 shrink-0 ${t.featured ? "text-paper" : "text-brown"}`} /> {f}
                </li>
              ))}
            </ul>
            <Link
              href={t.cta.href}
              className={`mt-6 rounded-full px-4 py-3 text-center text-sm font-medium transition ${t.featured ? "bg-paper text-brown hover:bg-sand" : "border border-espresso/15 hover:border-brown hover:text-brown"}`}
            >
              {t.cta.label}
            </Link>
          </div>
        ))}
      </div>
      <p className="mt-3 flex items-center gap-1.5 text-xs text-muted">
        <Info className="size-3.5" /> Starting prices to test with pilot customers, not validated market rates. Plus one-time onboarding (₹2k–10k) and integration fees.
      </p>

      {/* Growth loop */}
      <section className="mt-24">
        <Heading lead="How KinCare" tail="grows." className="text-3xl sm:text-5xl" />
        <div className="mt-8 grid gap-4 md:grid-cols-4">
          {[
            ["1", "A pharmacy subscribes", "₹499/month, first month free. Its stock is checked against every new alert."],
            ["2", "Its customers join free", "Phone numbers on the store's sales get WhatsApp reminders, paid for by the pharmacy."],
            ["3", "A batch gets flagged", "KinCare finds who bought it and alerts them before the next dose. The store looks responsible, and customers come back."],
            ["4", "Families upgrade", "Customers add parents and grandparents with Family (₹69). Patients' reports feed Early Signal for every store."],
          ].map(([n, t, d]) => (
            <div key={n} className="card rounded-3xl p-6">
              <span className="grid size-8 place-items-center rounded-full bg-teal font-mono text-sm text-paper">{n}</span>
              <p className="mt-4 font-medium">{t}</p>
              <p className="mt-1 text-sm text-muted">{d}</p>
            </div>
          ))}
        </div>
        <p className="mt-4 max-w-3xl text-sm text-muted">
          Pharmacies pay because one avoided recall complaint is worth more than a year of KinCare. Patients never pay for safety.
          No ads, and no selling of health data, ever.
        </p>
      </section>

      {/* Calculator */}
      <section className="mt-24">
        <Heading lead="Revenue" tail="calculator." className="text-3xl sm:text-5xl" />
        <div className="mt-8 grid gap-5 lg:grid-cols-[1.1fr_1fr]">
          <div className="card space-y-6 rounded-3xl p-6 sm:p-8">
            <Slider label="Basic users" value={basic} set={setBasic} max={100000} step={500} hint="₹29 / month each" />
            <Slider label="Family households" value={fam} set={setFam} max={50000} step={100} hint="₹69 / month each" />
            <Slider label="Pharmacies" value={starter} set={setStarter} max={500} hint="₹499 / month each" />
            <Slider label="Pro pharmacies" value={pro} set={setPro} max={200} hint="₹1,499 / month each" />
            <Slider label="Enterprise contracts" value={ent} set={setEnt} max={30} hint="₹30,000 / month each (mid-range)" />
            <Slider label="API customers" value={api} set={setApi} max={20} hint="₹25,000 / month each" />
            <Slider label="Monthly operating cost" value={opex} set={setOpex} max={1000000} step={5000} hint="Hosting, agents, messaging, sales" />
          </div>
          <div className="space-y-4">
            <div className="card rounded-3xl bg-espresso p-7 text-paper">
              <p className="text-sm text-paper/60">Monthly recurring revenue</p>
              <p className="mt-2 text-5xl font-medium tracking-tight">{inr(mrr)}</p>
              <p className="mt-4 text-sm text-paper/60">Annualised</p>
              <p className="text-2xl font-medium">{inr(mrr * 12)}</p>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className={`card rounded-3xl p-5 ${surplus < 0 ? "bg-danger/5" : ""}`}>
                <p className="text-sm text-muted">Monthly surplus</p>
                <p className={`mt-1 text-2xl font-medium ${surplus < 0 ? "text-danger" : "text-safe"}`}>{inr(surplus)}</p>
              </div>
              <div className="card rounded-3xl p-5">
                <p className="text-sm text-muted">Margin proxy</p>
                <p className="mt-1 text-2xl font-medium">{margin.toFixed(1)}%</p>
              </div>
            </div>
            <div className="card rounded-3xl p-5 text-sm">
              <p className="font-medium">Unit economics, worst case (every message paid)</p>
              <div className="mt-3 space-y-1.5 text-muted">
                <div className="flex justify-between"><span>Basic subscription</span><span className="text-espresso">₹29</span></div>
                <div className="flex justify-between"><span>50 paid WhatsApp reminders × ₹0.136 (cap)</span><span>−₹7</span></div>
                <div className="flex justify-between"><span>Infra + payment fee</span><span>−₹4</span></div>
                <div className="flex justify-between border-t border-line pt-1.5 font-medium text-espresso"><span>Contribution (~62%)</span><span>₹18</span></div>
                <div className="flex justify-between pt-2"><span>Family subscription</span><span className="text-espresso">₹69</span></div>
                <div className="flex justify-between"><span>3 numbers × 50 paid reminders × ₹0.136 (cap)</span><span>−₹20</span></div>
                <div className="flex justify-between"><span>Infra + payment fee</span><span>−₹5</span></div>
                <div className="flex justify-between border-t border-line pt-1.5 font-medium text-espresso"><span>Contribution (~64%)</span><span>₹44</span></div>
                <div className="flex justify-between pt-2"><span>Pharmacy subscription</span><span className="text-espresso">₹499</span></div>
                <div className="flex justify-between"><span>300 recall alerts × ₹0.136, infra, support</span><span>−₹141</span></div>
                <div className="flex justify-between border-t border-line pt-1.5 font-medium text-espresso"><span>Contribution (~72%)</span><span>₹358</span></div>
              </div>
              <p className="mt-3 text-xs text-muted">
                Paid WhatsApp messages are capped at 50 per number per month; past that, reminders arrive as free phone notifications, and recall alerts are never capped.
                Typical case is far cheaper: every reminder asks “reply 1 when taken”, and a reply keeps WhatsApp&apos;s 24-hour window open, inside which replies are free or near-free
                (Meta Cloud API, India Utility rate ~₹0.115 + GST outside it). Break-even at {inr(opex)} fixed cost ≈ {Math.ceil(opex / 358)} pharmacies.
              </p>
            </div>
          </div>
        </div>
        <p className="mt-3 text-xs text-muted">Illustrative planning model, excludes GST, taxes and one-off fees. Not a forecast.</p>
      </section>

      {/* Positioning */}
      <section className="mt-24 grid gap-4 md:grid-cols-3">
        {[
          ["Not another billing system", "KinCare sits beside Marg, GoFrugal or Excel. Pharmacies keep their software; we add alert monitoring and recall workflow."],
          ["Complements government QR", "A QR code shows the pack came from the maker. KinCare shows whether a regulator flagged that batch. Different questions."],
          ["The moat is the data", "A normalised, source-linked database of every alert, plus integrations and a network of pharmacies acting on it."],
        ].map(([t, b]) => (
          <div key={t} className="card rounded-3xl p-6">
            <p className="text-lg font-medium tracking-tight">{t}</p>
            <p className="mt-2 text-sm leading-relaxed text-muted">{b}</p>
          </div>
        ))}
      </section>

      {/* Roadmap */}
      <section className="mt-24">
        <Heading lead="From hackathon" tail="to company." className="text-3xl sm:text-5xl" />
        <div className="mt-8 grid gap-4 md:grid-cols-4">
          {ROADMAP.map(([when, title, body], i) => (
            <div key={when} className={`rounded-3xl p-6 ${i === 0 ? "bg-brown text-paper" : "card"}`}>
              <p className={`font-mono text-xs ${i === 0 ? "text-paper/70" : "text-muted"}`}>Phase {i + 1} · {when}</p>
              <p className="mt-3 text-lg font-medium">{title}</p>
              <p className={`mt-2 text-sm leading-relaxed ${i === 0 ? "text-paper/80" : "text-muted"}`}>{body}</p>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
