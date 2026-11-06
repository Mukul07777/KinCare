"use client";

import { useState } from "react";
import { ExternalLink, Loader2, MapPin, Navigation, Store as StoreIcon } from "lucide-react";
import { getJanAushadhi, type Store } from "@/lib/api";

/** Nearest Jan Aushadhi Kendras (government generic-medicine stores). Ask there by salt name, not brand. */
export function JanAushadhi({ salt }: { salt?: string }) {
  const [stores, setStores] = useState<Store[] | null>(null);
  const [maps, setMaps] = useState("https://www.google.com/maps/search/Jan+Aushadhi+Kendra+near+me");
  const [note, setNote] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const find = () => {
    if (!navigator.geolocation) return setNote("This browser can't share location. Use the maps search below.");
    setBusy(true);
    setNote(null);
    navigator.geolocation.getCurrentPosition(
      async (p) => {
        try {
          const r = await getJanAushadhi(p.coords.latitude, p.coords.longitude);
          setStores(r.stores);
          setMaps(r.maps_search);
          if (r.error) setNote("The open store map is busy right now. The maps search below still works.");
          else if (!r.stores.length) setNote("No Kendra is mapped near you on OpenStreetMap yet. Try the maps search.");
        } catch (e) {
          setNote((e as Error).message);
        } finally {
          setBusy(false);
        }
      },
      () => { setBusy(false); setNote("Location is off. Use the maps search below."); },
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 600000 },
    );
  };

  return (
    <div className="card rounded-3xl p-5 text-sm">
      <p className="flex items-center gap-2 font-medium"><StoreIcon className="size-4 text-teal" /> Jan Aushadhi Kendra near you</p>
      <p className="mt-1 text-muted">
        Government stores selling generic medicines, often far below brand prices.
        {salt && <> Ask for the salt: <b className="text-espresso">{salt}</b>.</>}
      </p>
      {!stores && (
        <button onClick={find} disabled={busy} className="mt-3 inline-flex items-center gap-2 rounded-full bg-teal px-4 py-2 font-medium text-paper hover:bg-teal-2">
          {busy ? <Loader2 className="size-4 animate-spin" /> : <MapPin className="size-4" />} Find near me
        </button>
      )}
      {stores && stores.length > 0 && (
        <div className="mt-3 divide-y divide-line">
          {stores.slice(0, 5).map((s) => (
            <div key={`${s.lat},${s.lon}`} className="flex items-start justify-between gap-3 py-2.5">
              <div className="min-w-0">
                <p className="font-medium">{s.name}</p>
                <p className="text-xs text-muted">{[s.address, s.hours].filter(Boolean).join(" · ") || "Address not on the map"}</p>
              </div>
              <a href={s.directions} target="_blank" rel="noreferrer" className="inline-flex shrink-0 items-center gap-1 rounded-full bg-sand px-3 py-1 text-xs font-medium text-brown">
                <Navigation className="size-3" /> {s.km < 1 ? `${Math.round(s.km * 1000)} m` : `${s.km.toFixed(1)} km`}
              </a>
            </div>
          ))}
        </div>
      )}
      {note && <p className="mt-2 text-xs text-warn">{note}</p>}
      <a href={maps} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-teal hover:underline">
        Search Jan Aushadhi Kendra on maps <ExternalLink className="size-3" />
      </a>
      {stores && stores.length > 0 && <p className="mt-1 text-[11px] text-muted">Store locations: OpenStreetMap contributors. Call ahead; stock varies.</p>}
    </div>
  );
}
