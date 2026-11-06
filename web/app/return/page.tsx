"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Printer } from "lucide-react";
import { checkBatch, formatIST, formatMonth, type CheckResult } from "@/lib/api";

function ReturnNote() {
  const p = useSearchParams();
  const batch = p.get("batch") ?? "";
  const brand = p.get("brand") ?? undefined;
  const maker = p.get("maker") ?? undefined;
  const [r, setR] = useState<CheckResult | null>(null);
  const [name, setName] = useState("");

  useEffect(() => {
    if (batch) checkBatch({ batch, brand, maker }).then(setR).catch(() => setR(null));
  }, [batch, brand, maker]);

  const a = r?.matches[0]?.alert;
  if (!batch) return <p className="py-24 text-center text-muted">No batch given.</p>;
  if (r && !a) return <p className="py-24 text-center text-muted">No published alert names this batch, so there is no return note to generate.</p>;

  return (
    <main className="mx-auto max-w-3xl px-4 pt-10 sm:px-6">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3 print:hidden">
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name (optional)" className="rounded-full border border-line bg-paper px-4 py-2.5 text-sm outline-none focus:border-brown/40" />
        <button onClick={() => window.print()} className="inline-flex items-center gap-2 rounded-full bg-brown px-5 py-2.5 text-sm font-medium text-paper transition hover:bg-brown-2">
          <Printer className="size-4" /> Print or save as PDF
        </button>
      </div>

      <article className="card rounded-3xl p-8 sm:p-12 print:rounded-none print:border-0 print:shadow-none">
        <div className="flex items-start justify-between border-b border-line pb-6">
          <div>
            <p className="text-xl font-semibold tracking-tight">kincare.</p>
            <p className="text-xs text-muted">Medicine batch alert: return request</p>
          </div>
          <p className="text-right text-xs text-muted">Generated {r ? formatIST(r.checked_at) : "…"}</p>
        </div>

        {!a ? (
          <p className="py-10 text-center text-muted">Looking up the alert…</p>
        ) : (
          <>
            <p className="mt-8 leading-relaxed">To the pharmacist,</p>
            <p className="mt-4 leading-relaxed">
              I purchased the medicine below from your store. The batch number on my pack appears in an official regulator alert, which lists it as{" "}
              <b>{a.category === "spurious" ? "spurious" : "not of standard quality"}</b>. I request that you verify this against the notice and advise on a return or replacement.
            </p>

            <table className="mt-8 w-full text-sm">
              <tbody className="divide-y divide-line">
                {[
                  ["Medicine on my pack", brand ?? a.product_name],
                  ["Batch number", batch],
                  ["Manufacturer on label", maker ?? "—"],
                  ["Alert listing", a.product_name],
                  ["Alert category", a.category === "spurious" ? "Spurious" : "Not of standard quality (NSQ)"],
                  ["Alert month", formatMonth(a.alert_month)],
                  ["Reason given", a.reason],
                ].map(([k, v]) => (
                  <tr key={k}>
                    <td className="w-48 py-2.5 pr-4 text-muted">{k}</td>
                    <td className="py-2.5 font-medium">{v}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <p className="mt-6 break-all text-sm">
              Regulator notice: <a href={a.alert_url} className="text-brown underline">{a.alert_url}</a>
            </p>

            <div className="mt-12 grid grid-cols-2 gap-8 text-sm">
              <div>
                <div className="h-10 border-b border-espresso/30">{name}</div>
                <p className="mt-1 text-muted">Customer</p>
              </div>
              <div>
                <div className="h-10 border-b border-espresso/30" />
                <p className="mt-1 text-muted">Pharmacist (signature and stamp)</p>
              </div>
            </div>

            <p className="mt-10 border-t border-line pt-4 text-[11px] leading-relaxed text-muted">
              KinCare matches batch numbers against published regulator alerts and links the source. It does not test medicines or certify authenticity. Please verify with the official notice and follow your recall procedure.
            </p>
          </>
        )}
      </article>
    </main>
  );
}

export default function ReturnPage() {
  return (
    <Suspense>
      <ReturnNote />
    </Suspense>
  );
}
