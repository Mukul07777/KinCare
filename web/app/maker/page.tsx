"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ArrowLeft, ArrowUpRight, Building2, Info } from "lucide-react";
import { Heading } from "@/components/Heading";
import { formatMonth, getManufacturer, SOURCE_LABEL, type MakerHistory } from "@/lib/api";

function MakerView() {
  const name = useSearchParams().get("name") ?? "";
  const [data, setData] = useState<MakerHistory | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (name) getManufacturer(name).then(setData).catch((e) => setError(e.message));
  }, [name]);

  const maxYear = Math.max(1, ...(data?.by_year.map((y) => y.n) ?? [1]));

  return (
    <main className="blush mx-auto max-w-6xl px-4 pt-10 sm:px-6 sm:pt-14">
      <Link href="/alerts" className="inline-flex items-center gap-1.5 text-sm text-muted transition hover:text-brown">
        <ArrowLeft className="size-4" /> All alerts
      </Link>

      <div className="mt-6 flex items-start gap-4">
        <span className="grid size-14 shrink-0 place-items-center rounded-2xl bg-sand text-brown"><Building2 className="size-6" /></span>
        <div>
          <p className="text-sm text-muted">Manufacturer history</p>
          <Heading as="h1" lead={data?.name ?? name} className="mt-1 text-3xl sm:text-5xl" />
        </div>
      </div>

      {error && <p className="mt-6 text-danger">{error}</p>}
      {data && data.total === 0 && <p className="card mt-8 rounded-3xl p-8 text-center text-muted">No published alert names this manufacturer.</p>}

      {data && data.total > 0 && (
        <>
          <div className="mt-8 grid gap-3 md:grid-cols-[1fr_1fr_2fr]">
            <div className="card rounded-3xl p-5">
              <p className="text-sm text-muted">Alert rows</p>
              <p className="mt-1 text-5xl font-medium tracking-tight">{data.total}</p>
            </div>
            <div className={`card rounded-3xl p-5 ${data.spurious ? "bg-danger text-paper" : ""}`}>
              <p className={`text-sm ${data.spurious ? "text-paper/80" : "text-muted"}`}>Spurious</p>
              <p className="mt-1 text-5xl font-medium tracking-tight">{data.spurious ?? 0}</p>
            </div>
            <div className="card rounded-3xl p-5">
              <p className="text-sm text-muted">By year</p>
              <div className="mt-3 flex h-20 items-end gap-2">
                {data.by_year.map((y) => (
                  <div key={y.year} className="flex flex-1 flex-col items-center gap-1">
                    <span className="text-[10px] text-muted">{y.n}</span>
                    <div className="w-full rounded-t-md bg-brown/80" style={{ height: `${(y.n / maxYear) * 52}px` }} />
                    <span className="text-[10px] text-muted">{y.year}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <details className="card mt-3 rounded-3xl p-5 text-sm">
            <summary className="cursor-pointer font-medium">
              {data.variants.length} spelling{data.variants.length > 1 ? "s" : ""} grouped as this company
            </summary>
            <p className="mt-2 text-xs text-muted">Regulator lists spell company names inconsistently. These were grouped automatically; check them before drawing conclusions.</p>
            <ul className="mt-3 flex flex-wrap gap-2">
              {data.variants.map((v) => <li key={v} className="rounded-full border border-line bg-cream/60 px-3 py-1 text-xs">{v}</li>)}
            </ul>
          </details>

          <div className="card mt-6 rounded-[2rem] p-3 sm:p-4">
            <div className="divide-y divide-line">
              {data.alerts.map((a) => (
                <div key={a.id} className="grid gap-2 px-3 py-4 sm:grid-cols-[1.8fr_0.8fr_1fr_auto] sm:items-center">
                  <div className="min-w-0">
                    <p className="font-medium">{a.product_name}</p>
                    <p className="truncate text-sm text-muted">{a.reason}</p>
                  </div>
                  <p className="font-mono text-sm">{a.batch_no}</p>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${a.category === "spurious" ? "bg-danger/10 text-danger" : "bg-sand text-brown"}`}>{SOURCE_LABEL[a.source]}</span>
                    <span className="text-xs text-muted">{formatMonth(a.alert_month)}</span>
                  </div>
                  <Link href={`/result?${new URLSearchParams({ batch: a.batch_no, brand: a.brand })}`} className="inline-flex w-fit items-center gap-1 rounded-full border border-line px-3 py-1.5 text-xs font-medium transition hover:border-brown hover:text-brown">
                    Check <ArrowUpRight className="size-3.5" />
                  </Link>
                </div>
              ))}
            </div>
          </div>

          <p className="mt-4 flex items-start gap-2 text-xs text-muted">
            <Info className="mt-0.5 size-3.5 shrink-0" />
            A count of published alert rows, not a quality rating. Large manufacturers are sampled more often. A flagged batch does not mean other batches are affected.
          </p>
        </>
      )}
    </main>
  );
}

export default function MakerPage() {
  return (
    <Suspense>
      <MakerView />
    </Suspense>
  );
}
