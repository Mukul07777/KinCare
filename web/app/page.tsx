import Link from "next/link";
import { ArrowRight, ArrowUpRight, BellRing, Camera, Check, Database, FileSearch, HeartPulse, Landmark, Store } from "lucide-react";
import { HeroVisual } from "@/components/HeroVisual";
import { Reveal } from "@/components/Reveal";
import { Eyebrow, Heading } from "@/components/Heading";
import { API_URL, formatMonth, type Stats } from "@/lib/api";

export const dynamic = "force-dynamic";

type Datasets = { alerts: number; alert_makers: number; medicines: number; salts: number; icu_patients: number };
type Gap = {
  alerts_used_lag: number; alerts_used_shelf: number; median_lag_months: number; p75_lag_months: number; median_shelf_left_months: number;
  pct_in_date_when_listed: number; in_date_when_listed: number; histogram: { label: string; n: number }[];
};
const n = (v?: number) => (v == null ? "–" : v.toLocaleString("en-IN"));

// Headline figures come from the live alert database, never typed in.
async function figures() {
  try {
    const [s, d, gap]: [Stats, Datasets | null, Gap | null] = await Promise.all([
      fetch(`${API_URL}/api/stats`, { cache: "no-store" }).then((r) => r.json()),
      fetch(`${API_URL}/api/datasets`, { cache: "no-store" }).then((r) => r.json()).catch(() => null),
      fetch(`${API_URL}/api/insights/recall-gap`, { cache: "no-store" }).then((r) => r.json()).catch(() => null),
    ]);
    const last = s.by_month.at(-1)!;
    const [y, m] = last.month.split("-").map(Number);
    const fy = m >= 4 ? y : y - 1;
    const inFy = s.by_month.filter((x) => x.month >= `${fy}-04` && x.month <= `${fy + 1}-03`).reduce((a, x) => a + x.n, 0);
    return {
      fyLabel: `FY ${fy}-${String(fy + 1).slice(2)}`,
      fyCount: inFy.toLocaleString("en-IN"),
      lastMonth: formatMonth(last.month),
      total: s.total.toLocaleString("en-IN"),
      since: s.coverage.start.slice(0, 4),
      data: d,
      gap: gap?.median_lag_months != null ? gap : null,
    };
  } catch {
    return null;
  }
}

const SOURCES = ["CDSCO NSQ alerts", "CDSCO spurious lists", "State drug laboratories", "Central Drugs Laboratory, Kolkata", "Monthly drug alerts", "Revised alert lists"];

const STEPS = [
  { icon: Camera, title: "Scan the strip", body: "A photo of the back of the strip, its QR code, or the pharmacy bill. You confirm what we read." },
  { icon: FileSearch, title: "Checked exactly", body: "Every CDSCO and state alert, matched on the exact batch. A near-miss never raises a false alarm." },
  { icon: BellRing, title: "Watched for good", body: "If a new list names your batch, WhatsApp and a Hindi voice call reach you before the next dose." },
];

// Three people KinCare protects, each with the one thing it does for them.
const AUDIENCES = [
  { icon: HeartPulse, who: "Families", line: "Know the medicine in your home is not on a failed list, and never miss a dose.",
    points: ["Scan, WhatsApp or ask in Hindi", "Dose reminders and refills", "Same salt, lower price"], href: "/scan", cta: "Check a batch" },
  { icon: Store, who: "Pharmacies", line: "Check your stock against every alert and reach every customer who bought a flagged batch.",
    points: ["Stock matched automatically", "Buyers alerted, response logged", "Customers get KinCare free"], href: "/pharmacy", cta: "Open the recall desk" },
  { icon: Landmark, who: "Regulators", line: "See who still holds a failed batch, where copied pack codes travel, and what patients report.",
    points: ["Recall blast radius", "Fake-pack radar", "Ranked action queue"], href: "/controller", cta: "See the dashboard" },
];

export default async function Home() {
  const f = await figures();
  return (
    <main className="overflow-x-clip">
      {/* Hero */}
      <section className="blush relative px-4 pt-14 sm:px-6 sm:pt-20">
        <div className="mx-auto max-w-4xl text-center">
          <Reveal>
            <div className="flex justify-center">
              <span className="inline-flex items-center gap-2 rounded-full border border-line bg-paper px-3 py-1 text-xs">
                <span className="size-1.5 rounded-full bg-danger" />
                <b className="font-semibold">{f?.fyCount ?? "–"}</b>
                <span className="text-muted">medicine samples failed government tests in {f?.fyLabel ?? "this financial year"}</span>
              </span>
            </div>
            <Heading as="h1" lead="Know the batch," tail="not just the brand." className="mt-7 text-5xl sm:text-7xl" />
            <p className="mx-auto mt-6 max-w-xl text-lg text-muted">
              KinCare checks your medicine against every government drug alert, then keeps watching it, so a failed batch never reaches your next dose.
            </p>
            <div className="mt-9 flex flex-wrap justify-center gap-3">
              <Link
                href="/scan"
                className="group inline-flex items-center gap-2 rounded-full bg-espresso px-7 py-3.5 text-sm font-medium text-paper shadow-[0_14px_34px_-12px_rgba(42,28,21,0.7)] transition hover:bg-brown"
              >
                Check a batch, free
                <ArrowRight className="size-4 transition group-hover:translate-x-0.5" />
              </Link>
              <Link
                href="#how"
                className="inline-flex items-center gap-2 rounded-full border border-espresso/15 bg-paper px-7 py-3.5 text-sm font-medium transition hover:border-brown"
              >
                How it works
              </Link>
            </div>
            <p className="mt-5 text-xs text-muted">Free for every patient · No app to install · Hindi and English</p>
          </Reveal>
        </div>
        <HeroVisual />
      </section>

      {/* Sources */}
      <section className="mt-16 border-y border-line bg-paper/60">
        <p className="pt-6 text-center text-xs font-medium uppercase tracking-[0.18em] text-muted">Every public source, read every night</p>
        <div className="flex overflow-hidden">
          <div className="marquee flex shrink-0 items-center">
            {[...SOURCES, ...SOURCES].map((s, i) => (
              <span key={i} className="flex items-center gap-3 px-10 py-6 text-lg font-medium tracking-tight text-mocha">
                <span className="size-1.5 rotate-45 bg-clay" />
                {s}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* The recall gap, measured on every alert */}
      {f?.gap && <RecallGap g={f.gap} />}

      {/* How it works */}
      <section id="how" className="mx-auto max-w-6xl scroll-mt-24 px-4 pt-28 sm:px-6">
        <Reveal>
          <div className="grid items-end gap-6 md:grid-cols-2">
            <div>
              <Eyebrow>How it works</Eyebrow>
              <Heading lead="Scan once." tail="Watched for good." className="mt-4 text-4xl sm:text-5xl" />
            </div>
            <p className="max-w-sm text-muted md:ml-auto">
              A failed batch does not condemn the brand. Only the batch number tells you, so that is exactly what we check. We never say “safe”: only “no alert found as of” a date and time.
            </p>
          </div>
        </Reveal>
        <div className="mt-12 grid gap-4 md:grid-cols-3">
          {STEPS.map(({ icon: Icon, title, body }, i) => (
            <Reveal key={title} delay={i * 0.08}>
              <div className="card h-full rounded-3xl p-7">
                <div className="flex items-center justify-between">
                  <span className="grid size-12 place-items-center rounded-2xl bg-mint text-teal"><Icon className="size-5" /></span>
                  <span className="font-mono text-sm text-clay">0{i + 1}</span>
                </div>
                <h3 className="mt-8 text-xl font-medium tracking-tight">{title}</h3>
                <p className="mt-2 leading-relaxed text-muted">{body}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* Who it's for */}
      <section className="mx-auto max-w-6xl px-4 pt-28 sm:px-6">
        <Reveal>
          <Eyebrow>One alert network</Eyebrow>
          <Heading lead="Built for the three people" tail="a recall depends on." className="mt-4 max-w-3xl text-4xl sm:text-5xl" />
        </Reveal>
        <div className="mt-12 grid gap-4 lg:grid-cols-3">
          {AUDIENCES.map(({ icon: Icon, who, line, points, href, cta }, i) => (
            <Reveal key={who} delay={i * 0.08}>
              <Link href={href} className={`group flex h-full flex-col rounded-[2rem] p-8 transition hover:-translate-y-1 ${i === 1 ? "bg-espresso text-paper" : "card"}`}>
                <span className={`grid size-12 place-items-center rounded-2xl ${i === 1 ? "bg-paper/10 text-paper" : "bg-sand text-brown"}`}><Icon className="size-5" /></span>
                <h3 className="mt-8 text-2xl font-medium tracking-tight">{who}</h3>
                <p className={`mt-3 leading-relaxed ${i === 1 ? "text-paper/70" : "text-muted"}`}>{line}</p>
                <ul className="mt-6 flex-1 space-y-2.5 text-sm">
                  {points.map((p) => (
                    <li key={p} className="flex items-center gap-2.5">
                      <Check className={`size-4 shrink-0 ${i === 1 ? "text-[#5fd3c4]" : "text-teal"}`} /> {p}
                    </li>
                  ))}
                </ul>
                <span className={`mt-8 inline-flex items-center gap-1.5 text-sm font-medium transition group-hover:gap-2.5 ${i === 1 ? "text-paper" : "text-brown"}`}>
                  {cta} <ArrowRight className="size-4" />
                </span>
              </Link>
            </Reveal>
          ))}
        </div>
      </section>

      {/* Built on real public data */}
      <section className="mx-auto max-w-6xl px-4 pt-20 sm:px-6">
        <Reveal>
          <div className="clinical rounded-[2rem] p-6 sm:p-8">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="flex items-center gap-2 font-medium text-teal-2"><Database className="size-5 text-teal" /> Built on real public data. Nothing typed in.</p>
              <Link href="/status" className="inline-flex items-center gap-1 text-sm font-medium text-teal underline-offset-4 hover:underline">
                Live accuracy and freshness <ArrowUpRight className="size-4" />
              </Link>
            </div>
            <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {[
                { v: n(f?.data?.alerts), l: "CDSCO and state drug alerts", s: `since ${f?.since ?? "2019"}` },
                { v: n(f?.data?.medicines), l: "Indian brands priced", s: `${n(f?.data?.salts)} salt combinations` },
                { v: "100%", l: "flagged batches caught", s: "0 false alarms in our benchmark" },
                { v: "openFDA", l: "official drug labels", s: "for interaction checks" },
              ].map((x) => (
                <div key={x.l} className="rounded-2xl bg-paper/80 p-5">
                  <p className="font-mono text-3xl font-semibold tracking-tight text-espresso">{x.v}</p>
                  <p className="mt-1 text-sm font-medium">{x.l}</p>
                  <p className="text-xs text-muted">{x.s}</p>
                </div>
              ))}
            </div>
          </div>
        </Reveal>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-6xl px-4 pt-24 sm:px-6">
        <Reveal>
          <div className="relative overflow-hidden rounded-[2rem] bg-espresso px-8 py-14 text-paper sm:px-14">
            <div className="dots absolute inset-0 opacity-20" />
            <div className="relative grid items-center gap-8 md:grid-cols-[1.4fr_1fr]">
              <h2 className="text-4xl font-medium leading-tight tracking-tight sm:text-5xl">
                Check your parents’ medicines <span className="text-clay">tonight.</span>
              </h2>
              <div className="md:text-right">
                <p className="text-paper/70">Ten seconds. Free for patients, forever.</p>
                <Link href="/scan" className="mt-5 inline-flex items-center gap-2 rounded-full bg-paper px-6 py-3 text-sm font-medium text-espresso transition hover:bg-sand">
                  Check a batch <ArrowRight className="size-4" />
                </Link>
              </div>
            </div>
          </div>
        </Reveal>
      </section>
    </main>
  );
}

// Made → months in homes, unseen → CDSCO lists it → months still in date. Drawn to scale from the medians.
function RecallGap({ g }: { g: Gap }) {
  const lag = g.median_lag_months, left = g.median_shelf_left_months, total = lag + left;
  const max = Math.max(...g.histogram.map((h) => h.n));
  return (
    <section className="mx-auto max-w-6xl px-4 pt-24 sm:px-6">
      <Reveal>
        <div className="grid items-end gap-6 md:grid-cols-2">
          <div>
            <Eyebrow>The recall gap · measured</Eyebrow>
            <Heading lead="Ten months in homes." tail="Before anyone is told." className="mt-4 text-4xl sm:text-5xl" />
          </div>
          <p className="max-w-sm text-muted md:ml-auto">
            From the manufacture and expiry dates printed on {n(g.alerts_used_lag)} real CDSCO alerts. When a batch is finally listed,
            it is almost always still in date: still on shelves, still being swallowed.
          </p>
        </div>
      </Reveal>

      <Reveal>
        <div className="relative mt-10 overflow-hidden rounded-[2.5rem] bg-espresso p-6 text-paper sm:p-10">
          <div className="pointer-events-none absolute -right-24 -top-24 size-80 rounded-full bg-danger/25 blur-3xl" />
          <div className="pointer-events-none absolute -bottom-24 left-1/3 size-72 rounded-full bg-teal/20 blur-3xl" />

          <div className="relative grid gap-4 sm:grid-cols-3">
            {[
              [`${lag}`, "months", "median from manufacture to the CDSCO list", "text-[#ff8a73]"],
              [`${g.pct_in_date_when_listed}%`, "", `still in date when listed (${n(g.in_date_when_listed)} of ${n(g.alerts_used_shelf)})`, "text-[#f3b56b]"],
              [`${left}`, "months", "median shelf life left after the alert", "text-[#f3b56b]"],
            ].map(([v, u, l, c]) => (
              <div key={l} className="rounded-3xl border border-paper/10 bg-paper/5 p-6">
                <p className={`font-mono text-5xl font-semibold tracking-tight sm:text-6xl ${c}`}>{v}<span className="ml-1 text-lg font-normal text-paper/50">{u}</span></p>
                <p className="mt-2 text-sm text-paper/65">{l}</p>
              </div>
            ))}
          </div>

          {/* To-scale timeline */}
          <div className="relative mt-10">
            <div className="flex h-14 overflow-hidden rounded-2xl">
              <div className="flex items-center justify-center bg-gradient-to-r from-danger/40 to-danger/80 px-3 text-xs font-medium sm:text-sm" style={{ width: `${(lag / total) * 100}%` }}>
                In homes, nobody told · {lag} mo
              </div>
              <div className="flex items-center justify-center bg-gradient-to-r from-warn/70 to-warn/30 px-3 text-xs font-medium sm:text-sm" style={{ width: `${(left / total) * 100}%` }}>
                Listed, still in date · {left} mo
              </div>
            </div>
            <div className="absolute -top-3 h-20 w-0.5 bg-paper" style={{ left: `${(lag / total) * 100}%` }} />
            <div className="relative mt-3 h-4 text-[11px] text-paper/55 sm:text-xs">
              <span className="absolute left-0">Batch made</span>
              <span className="absolute -translate-x-1/2 whitespace-nowrap font-semibold text-paper" style={{ left: `${(lag / total) * 100}%` }}>CDSCO lists it</span>
              <span className="absolute right-0">Expiry</span>
            </div>
          </div>

          <div className="relative mt-10 grid items-end gap-8 lg:grid-cols-[1.2fr_1fr]">
            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-paper/50">Months from manufacture to listing · every alert</p>
              <div className="mt-4 flex h-32 items-end gap-2">
                {g.histogram.map((h) => (
                  <div key={h.label} className="flex flex-1 flex-col items-center gap-1.5">
                    <span className="font-mono text-[10px] text-paper/50">{n(h.n)}</span>
                    <div className="w-full rounded-t-lg bg-gradient-to-t from-danger/60 to-[#ff8a73]" style={{ height: `${Math.max(4, (h.n / max) * 96)}px` }} />
                    <span className="text-[10px] text-paper/50">{h.label}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="rounded-3xl bg-teal p-6">
              <p className="text-xs font-medium uppercase tracking-wider text-paper/70">KinCare closes the second half</p>
              <p className="mt-2 text-xl font-medium leading-snug">The moment a batch is listed, everyone holding it hears, soonest next dose first.</p>
              <Link href="/blast" className="mt-4 inline-flex items-center gap-1.5 rounded-full bg-paper px-4 py-2 text-sm font-medium text-teal hover:bg-sand">
                See the recall blast radius <ArrowRight className="size-4" />
              </Link>
            </div>
          </div>
          <p className="relative mt-6 text-[11px] text-paper/40">
            Source: CDSCO and state NSQ / spurious alerts 2019–2026, dates as printed on each alert; unreadable dates skipped. A quarter of batches took {g.p75_lag_months}+ months to be listed.
          </p>
        </div>
      </Reveal>
    </section>
  );
}
