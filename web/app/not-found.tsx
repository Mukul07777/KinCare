import Link from "next/link";
import { ArrowRight, Play, ScanLine } from "lucide-react";
import { Eyebrow, Heading } from "@/components/Heading";

// Branded 404: a lost visitor (or judge) gets the two ways in, not a black Next.js screen.
export default function NotFound() {
  return (
    <main className="blush mx-auto flex min-h-[60dvh] max-w-3xl flex-col items-center justify-center px-4 py-20 text-center sm:px-6">
      <Eyebrow>404 · page not found</Eyebrow>
      <Heading as="h1" lead="This page isn't here." tail="Your medicines still are." className="mt-5 text-4xl sm:text-6xl" />
      <p className="mt-5 max-w-md text-muted">The link may be old or mistyped. Check a batch, or see how KinCare works.</p>
      <div className="mt-8 flex flex-wrap justify-center gap-3">
        <Link href="/scan" className="inline-flex items-center gap-2 rounded-full bg-brown px-6 py-3 text-sm font-medium text-paper transition hover:bg-brown-2">
          <ScanLine className="size-4" /> Check a batch <ArrowRight className="size-4" />
        </Link>
        <Link href="/how" className="inline-flex items-center gap-2 rounded-full bg-espresso px-6 py-3 text-sm font-medium text-paper transition hover:bg-teal-2">
          <Play className="size-3.5" /> How it works
        </Link>
        <Link href="/" className="inline-flex items-center rounded-full border border-line bg-paper px-6 py-3 text-sm font-medium transition hover:border-brown">
          Home
        </Link>
      </div>
    </main>
  );
}
