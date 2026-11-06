"use client";

import Link from "next/link";
import { RotateCcw, Siren } from "lucide-react";
import { Eyebrow, Heading } from "@/components/Heading";

// Any page crash lands here instead of Next's bare "Application error"; SOS stays one tap away.
export default function PageError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <main className="blush mx-auto flex min-h-[60dvh] max-w-3xl flex-col items-center justify-center px-4 py-20 text-center sm:px-6">
      <Eyebrow>Something went wrong</Eyebrow>
      <Heading as="h1" lead="This page hit a problem." tail="Nothing you did." className="mt-5 text-4xl sm:text-5xl" />
      <p className="mt-5 max-w-md text-muted">
        Usually the KinCare server is still starting or the connection dropped. Try again in a moment.
        {error.digest && <span className="mt-2 block font-mono text-xs">ref {error.digest}</span>}
      </p>
      <div className="mt-8 flex flex-wrap justify-center gap-3">
        <button onClick={reset} className="inline-flex items-center gap-2 rounded-full bg-brown px-6 py-3 text-sm font-medium text-paper transition hover:bg-brown-2">
          <RotateCcw className="size-4" /> Try again
        </button>
        <Link href="/" className="inline-flex items-center rounded-full border border-line bg-paper px-6 py-3 text-sm font-medium transition hover:border-brown">Home</Link>
        <Link href="/sos" className="inline-flex items-center gap-2 rounded-full bg-danger/10 px-6 py-3 text-sm font-semibold text-danger transition hover:bg-danger hover:text-paper">
          <Siren className="size-4" /> SOS
        </Link>
      </div>
    </main>
  );
}
