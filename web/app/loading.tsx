// Shown instantly while any page's server data loads, so a click never feels dead.
export default function Loading() {
  return (
    <main className="mx-auto max-w-6xl px-4 pt-14 sm:px-6 sm:pt-16" aria-busy="true" aria-live="polite">
      <span className="sr-only">Loading…</span>
      <div className="animate-pulse">
        <div className="h-3 w-28 rounded-full bg-sand" />
        <div className="mt-5 h-12 w-3/4 max-w-xl rounded-2xl bg-sand" />
        <div className="mt-4 h-4 w-1/2 max-w-md rounded-full bg-sand/70" />
        <div className="mt-10 grid gap-4 md:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="card h-44 rounded-3xl p-6">
              <div className="size-12 rounded-2xl bg-sand" />
              <div className="mt-8 h-4 w-2/3 rounded-full bg-sand" />
              <div className="mt-3 h-3 w-full rounded-full bg-sand/70" />
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
