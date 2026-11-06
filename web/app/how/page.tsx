import Link from "next/link";
import { ArrowRight, Bot, Camera, Database, FileSearch, MessageCircle, PhoneCall } from "lucide-react";
import { Eyebrow, Heading } from "@/components/Heading";
import { Reveal } from "@/components/Reveal";

const PIPELINE = [
  { icon: Camera, title: "Scan", body: "Vision OCR reads brand, batch, maker and expiry from the strip or the pharmacy bill. You confirm before anything runs." },
  { icon: Bot, title: "Agents fan out", body: "One TinyFish web agent per source reads CDSCO, state regulator and manufacturer pages live and returns structured rows." },
  { icon: Database, title: "Alert store", body: "A nightly run refreshes every source into one database, so each scan answers instantly from fresh data." },
  { icon: FileSearch, title: "Match in our code", body: "Exact batch number plus manufacturer. Fuzzy matching only on names. Every score is shown, so every verdict is auditable." },
  { icon: MessageCircle, title: "Watch", body: "Saved batches are re-checked whenever a new list is published." },
  { icon: PhoneCall, title: "Recall", body: "A new match triggers a WhatsApp message and a voice call in Hindi, linked to the regulator’s notice." },
];

const LIMITS = [
  ["False reassurance", "We never say safe. Only “no alert found as of” a time, with the sources checked."],
  ["Fakes that copy a real batch", "A list cannot catch these. We say so plainly, and add visual pack hints later."],
  ["OCR mistakes", "You confirm the batch and brand before the check runs."],
  ["Stale lists", "Every result shows when it was last verified."],
  ["Liability", "We only repeat regulator statements, always linked to the source."],
];

export default function HowPage() {
  return (
    <main className="blush mx-auto max-w-6xl px-4 pt-12 sm:px-6 sm:pt-16">
      <div className="grid items-end gap-6 md:grid-cols-2">
        <div>
          <Eyebrow>How it works</Eyebrow>
          <Heading as="h1" lead="From a government PDF" tail="to your phone." className="mt-4 text-4xl sm:text-6xl" />
        </div>
        <p className="max-w-sm text-muted md:ml-auto">
          Regulator alerts are PDFs and portals with no API. KinCare reads them, matches your exact batch and tells you, with the source.
        </p>
      </div>

      <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {PIPELINE.map(({ icon: Icon, title, body }, i) => (
          <Reveal key={title} delay={i * 0.05}>
            <div className="card h-full rounded-3xl p-6">
              <div className="flex items-center justify-between">
                <span className="grid size-11 place-items-center rounded-2xl bg-sand text-brown"><Icon className="size-5" /></span>
                <span className="font-mono text-sm text-clay">0{i + 1}</span>
              </div>
              <h3 className="mt-6 text-lg font-medium">{title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted">{body}</p>
            </div>
          </Reveal>
        ))}
      </div>

      <section id="limits" className="mt-24 scroll-mt-24">
        <Reveal>
          <div className="overflow-hidden rounded-[2rem] bg-brown text-paper">
            <div className="grid gap-10 p-8 sm:p-12 md:grid-cols-[1fr_1.4fr]">
              <div>
                <p className="text-sm text-paper/70">Honest by design</p>
                <h2 className="mt-3 text-4xl font-medium leading-tight tracking-tight">What we can and cannot tell you.</h2>
              </div>
              <div className="divide-y divide-paper/15">
                {LIMITS.map(([k, v]) => (
                  <div key={k} className="grid gap-1 py-4 sm:grid-cols-[180px_1fr] sm:gap-6">
                    <p className="font-medium">{k}</p>
                    <p className="text-sm text-paper/75">{v}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Reveal>
      </section>

      <div className="mt-12 text-center">
        <Link href="/scan" className="inline-flex items-center gap-2 rounded-full bg-espresso px-6 py-3.5 text-sm font-medium text-paper transition hover:bg-brown-2">
          Try it now <ArrowRight className="size-4" />
        </Link>
      </div>
    </main>
  );
}
