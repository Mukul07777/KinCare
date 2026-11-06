"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowUpRight, ChevronLeft, ChevronRight, ExternalLink, Search } from "lucide-react";
import { Eyebrow, Heading } from "@/components/Heading";
import { formatMonth, getAlerts, getStats, SOURCE_LABEL, type Alert, type Stats } from "@/lib/api";

const FILTERS = [
  { id: "", label: "All" },
  { id: "spurious", label: "Spurious" },
  { id: "nsq", label: "Not of standard quality" },
];
const PAGE = 25;

export default function AlertsPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [data, setData] = useState<{ total: number; items: Alert[] } | null>(null);
  const [error, setError] = useState(false);
  const [q, setQ] = useState("");
  const [cat, setCat] = useState("");
  const [page, setPage] = useState(0);

  useEffect(() => {
    getStats().then(setStats).catch(() => setError(true));
  }, []);

  useEffect(() => {
    const t = setTimeout(() => {
      getAlerts({ q, category: cat, limit: PAGE, offset: page * PAGE }).then(setData).catch(() => setError(true));
    }, 250);
    return () => clearTimeout(t);
  }, [q, cat, page]);

  const maxMonth = Math.max(1, ...(stats?.by_month.map((m) => m.n) ?? [1]));
  const pages = data ? Math.ceil(data.total / PAGE) : 0;

  return (
    <main className="blush mx-auto max-w-6xl px-4 pt-12 sm:px-6 sm:pt-16">
      <div className="grid items-end gap-6 md:grid-cols-2">
        <div>
          <Eyebrow>Alert explorer</Eyebrow>
          <Heading as="h1" lead="Every regulator alert," tail="searchable." className="mt-4 text-4xl sm:text-6xl" />
        </div>
        <p className="max-w-sm text-muted md:ml-auto">
          {stats
            ? `${stats.documents} CDSCO and state alert PDFs, ${formatMonth(stats.coverage.start)} to ${formatMonth(stats.coverage.end)}, parsed into one list.`
            : "Monthly CDSCO and state alert PDFs, parsed into one clean list."}
        </p>
      </div>

      <div className="mt-10 grid gap-3 lg:grid-cols-[1fr_1fr_1fr_1.6fr]">
        {[
          ["Alerts indexed", stats?.total],
          ["Spurious", stats?.spurious],
          ["Manufacturers", stats?.manufacturers],
        ].map(([label, v], i) => (
          <div key={label as string} className={`card rounded-3xl p-5 ${i === 1 ? "bg-brown text-paper" : ""}`}>
            <p className={`text-sm ${i === 1 ? "text-paper/70" : "text-muted"}`}>{label}</p>
            <p className="mt-2 text-4xl font-medium tracking-tight sm:text-5xl">{v?.toLocaleString("en-IN") ?? "…"}</p>
          </div>
        ))}
        <div className="card rounded-3xl p-5">
          <p className="text-sm text-muted">Flagged per month</p>
          <div className="mt-3 flex h-20 items-end gap-1.5">
            {stats?.by_month.map((m) => (
              <div key={m.month} className="group relative flex-1">
                <div className="w-full rounded-t-md bg-clay transition group-hover:bg-brown" style={{ height: `${(m.n / maxMonth) * 72}px` }} />
                <span className="pointer-events-none absolute -top-6 left-1/2 hidden -translate-x-1/2 whitespace-nowrap rounded bg-espresso px-1.5 py-0.5 text-[10px] text-paper group-hover:block">
                  {m.month}: {m.n}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="card mt-6 rounded-[2rem] p-3 sm:p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <label className="relative flex-1">
            <Search className="absolute left-4 top-1/2 size-4 -translate-y-1/2 text-muted" />
            <input
              value={q}
              onChange={(e) => { setQ(e.target.value); setPage(0); }}
              placeholder="Search medicine, batch or manufacturer"
              className="w-full rounded-full border border-line bg-cream/60 py-3 pl-11 pr-4 text-sm outline-none transition focus:border-brown/40 focus:bg-paper"
            />
          </label>
          <div className="flex gap-1 overflow-x-auto rounded-full border border-line bg-cream/60 p-1">
            {FILTERS.map((f) => (
              <button
                key={f.id}
                onClick={() => { setCat(f.id); setPage(0); }}
                className={`whitespace-nowrap rounded-full px-4 py-2 text-xs font-medium transition ${cat === f.id ? "bg-brown text-paper" : "text-muted hover:text-espresso"}`}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-3 divide-y divide-line">
          {error && <p className="p-6 text-center text-danger">Couldn’t load alerts right now. Check your connection and refresh.</p>}
          {!data && !error && <p className="p-6 text-center text-muted">Loading alerts…</p>}
          {data && data.items.length === 0 && <p className="p-6 text-center text-muted">No alerts match your search.</p>}
          {data?.items.map((a) => (
            <div key={a.id} className="grid gap-3 px-3 py-4 sm:grid-cols-[1.7fr_0.8fr_1.1fr_auto] sm:items-center">
              <div className="min-w-0">
                <p className="font-medium">{a.product_name}</p>
                <p className="truncate text-sm text-muted">
                  {a.manufacturer && !/investigation/i.test(a.manufacturer) ? (
                    <Link href={`/maker?name=${encodeURIComponent(a.manufacturer)}`} className="hover:text-brown hover:underline">{a.manufacturer}</Link>
                  ) : (a.manufacturer || "Maker not named")}{" "}
                  · {a.reason}
                </p>
              </div>
              <p className="font-mono text-sm">{a.batch_no}</p>
              <div className="flex flex-wrap items-center gap-2">
                <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${a.category === "spurious" ? "bg-danger/10 text-danger" : "bg-sand text-brown"}`}>
                  {SOURCE_LABEL[a.source]}
                </span>
                <span className="text-xs text-muted">{formatMonth(a.alert_month)}</span>
              </div>
              <div className="flex gap-2">
                <Link
                  href={`/result?${new URLSearchParams({ batch: a.batch_no, brand: a.brand })}`}
                  className="inline-flex items-center gap-1 rounded-full border border-line px-3 py-1.5 text-xs font-medium transition hover:border-brown hover:text-brown"
                >
                  Check <ArrowUpRight className="size-3.5" />
                </Link>
                <a
                  href={a.alert_url + (a.pdf_page ? `#page=${a.pdf_page}` : "")}
                  target="_blank"
                  rel="noreferrer"
                  className="grid size-8 place-items-center rounded-full border border-line transition hover:border-brown hover:text-brown"
                  aria-label="Open regulator PDF"
                >
                  <ExternalLink className="size-3.5" />
                </a>
              </div>
            </div>
          ))}
        </div>

        {pages > 1 && (
          <div className="mt-2 flex items-center justify-between border-t border-line px-3 pt-3 text-sm text-muted">
            <span>{data!.total.toLocaleString("en-IN")} results</span>
            <div className="flex items-center gap-2">
              <button disabled={page === 0} onClick={() => setPage(page - 1)} className="grid size-8 place-items-center rounded-full border border-line disabled:opacity-30" aria-label="Previous">
                <ChevronLeft className="size-4" />
              </button>
              <span>{page + 1} / {pages}</span>
              <button disabled={page + 1 >= pages} onClick={() => setPage(page + 1)} className="grid size-8 place-items-center rounded-full border border-line disabled:opacity-30" aria-label="Next">
                <ChevronRight className="size-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {stats && stats.top_manufacturers.length > 0 && (
        <div className="card mt-6 rounded-3xl p-6">
          <p className="font-medium">Most-flagged manufacturers in this period</p>
          <p className="text-xs text-muted">Count of alert rows naming the maker. Many makers appear once; a count is not a quality rating.</p>
          <div className="mt-4 grid gap-x-8 gap-y-2 sm:grid-cols-2">
            {stats.top_manufacturers.map((m) => (
              <Link key={m.manufacturer} href={`/maker?name=${encodeURIComponent(m.manufacturer)}`} className="flex items-center gap-3 text-left text-sm">
                <span className="flex-1 truncate hover:text-brown">{m.manufacturer}</span>
                <span className="h-1.5 rounded-full bg-brown" style={{ width: `${(m.n / stats.top_manufacturers[0].n) * 80}px` }} />
                <span className="w-8 text-right font-mono text-muted">{m.n}</span>
              </Link>
            ))}
          </div>
        </div>
      )}
    </main>
  );
}
