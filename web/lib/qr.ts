// Reads what's printed in a medicine pack's QR / Data Matrix code.
// India's Schedule H2 (Aug 2023) makes the top 300 brands carry one with product, batch, mfg and expiry.
// Three shapes seen in the wild:
// - GS1 element strings: (01) GTIN, (10) batch, (17) expiry YYMMDD, (11) mfg, (21) serial; raw or with brackets
// - a maker's verification URL with the batch in its query string
// - plain "Batch No: ... Exp: ..." text

export type PackCode = {
  format: "gs1" | "url" | "text";
  batch: string | null;
  expiry: string | null; // YYYY-MM
  mfg: string | null; // YYYY-MM
  gtin: string | null;
  serial: string | null;
  brand: string | null;
  maker: string | null;
  url: string | null;
  raw: string;
};

const GS = "\u001d";
// Fixed-length GS1 application identifiers (data length); everything else ends at GS or the next bracket.
const FIXED: Record<string, number> = { "01": 14, "02": 14, "11": 6, "13": 6, "15": 6, "17": 6, "20": 2 };

function gs1Date(v: string | undefined): string | null {
  if (!v || !/^\d{6}$/.test(v)) return null;
  const yy = Number(v.slice(0, 2));
  const mm = v.slice(2, 4);
  if (Number(mm) < 1 || Number(mm) > 12) return null;
  return `${yy >= 70 ? 1900 + yy : 2000 + yy}-${mm}`;
}

function parseGs1(s: string): Record<string, string> | null {
  const out: Record<string, string> = {};
  const t = s.replace(/^\]([CdQe])\d/, "").trim(); // symbology prefix some scanners add
  if (t.includes("(")) {
    for (const m of t.matchAll(/\((\d{2,4})\)([^(]*)/g)) out[m[1]] = m[2].replace(GS, "").trim();
    return Object.keys(out).length ? out : null;
  }
  if (!/^(01|02|10|11|17|21)\d/.test(t)) return null;
  let i = 0;
  while (i < t.length) {
    const ai = t.slice(i, i + 2);
    if (!/^\d{2}$/.test(ai)) break;
    i += 2;
    if (FIXED[ai]) {
      out[ai] = t.slice(i, i + FIXED[ai]);
      i += FIXED[ai];
    } else {
      const end = t.indexOf(GS, i);
      out[ai] = t.slice(i, end === -1 ? undefined : end);
      i = end === -1 ? t.length : end + 1;
    }
    if (t[i] === GS) i++;
  }
  return out["10"] || out["01"] ? out : null;
}

const MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"];

/** "06/2026", "JUN 2026", "06-26", "2026-06" -> "2026-06". */
export function textDate(v: string | undefined): string | null {
  if (!v) return null;
  const s = v.trim().toLowerCase();
  let m = s.match(/^(\d{4})[-/.](\d{1,2})/);
  if (m) return `${m[1]}-${m[2].padStart(2, "0")}`;
  m = s.match(/^(\d{1,2})[-/.](\d{2,4})/);
  if (m && Number(m[1]) >= 1 && Number(m[1]) <= 12) return `${m[2].length === 2 ? "20" + m[2] : m[2]}-${m[1].padStart(2, "0")}`;
  m = s.match(/^([a-z]{3})[a-z]*[\s.\-/]*(\d{2,4})/);
  if (m && MONTHS.includes(m[1])) return `${m[2].length === 2 ? "20" + m[2] : m[2]}-${String(MONTHS.indexOf(m[1]) + 1).padStart(2, "0")}`;
  return null;
}

const KEYS = {
  batch: /^(batch|batch\s*no|b\.?\s*no|lot|lot\s*no|bn|batchno|batch_no|batchnumber)$/i,
  expiry: /^(exp|expiry|exp\.?\s*date|expiry\s*date|expdate|exp_date|use\s*before)$/i,
  mfg: /^(mfg|mfd|mfg\.?\s*date|manufacturing\s*date|mfgdate|mfg_date)$/i,
  brand: /^(brand|product|product\s*name|name|brand\s*name)$/i,
  maker: /^(mfr|manufacturer|mfd\.?\s*by|mfg\.?\s*by|manufactured\s*by|marketed\s*by|company)$/i,
  gtin: /^(gtin|upc|ean|product\s*code|unique\s*product\s*identification\s*code|upic)$/i,
};
type Key = keyof typeof KEYS;
const keyOf = (k: string) => (Object.keys(KEYS) as Key[]).find((x) => KEYS[x].test(k.trim().replace(/[.:]+$/, ""))) ?? null;

export function parsePackCode(raw: string): PackCode {
  const base: PackCode = { format: "text", batch: null, expiry: null, mfg: null, gtin: null, serial: null, brand: null, maker: null, url: null, raw };
  const s = raw.trim();

  const g = parseGs1(s);
  if (g) {
    return { ...base, format: "gs1", batch: g["10"] || null, expiry: gs1Date(g["17"]), mfg: gs1Date(g["11"]), gtin: g["01"] || null, serial: g["21"] || null };
  }

  if (/^https?:\/\//i.test(s)) {
    const out: PackCode = { ...base, format: "url", url: s };
    try {
      const u = new URL(s);
      for (const [k, v] of u.searchParams) {
        const key = keyOf(k);
        if (!key || !v) continue;
        if (key === "expiry" || key === "mfg") out[key] = textDate(v) ?? gs1Date(v);
        else out[key] = v.trim();
      }
      // Some codes carry a GS1 string inside the link (GS1 Digital Link: /01/<gtin>/10/<batch>).
      const dl = u.pathname.match(/\/01\/(\d{14})(?:\/10\/([^/?]+))?/);
      if (dl) { out.gtin ??= dl[1]; out.batch ??= dl[2] ? decodeURIComponent(dl[2]) : null; }
      const exp = u.searchParams.get("17");
      if (exp) out.expiry ??= gs1Date(exp);
    } catch { /* not a valid URL after all */ }
    return out;
  }

  // "Key: value" pairs on lines, or separated by | ; ,
  const out: PackCode = { ...base };
  for (const part of s.split(/\r?\n|\||;|,(?=\s*[A-Za-z .]+\s*[:=])/)) {
    const m = part.match(/^\s*([A-Za-z][A-Za-z .]*?)\s*[:=#-]\s*(.+)$/);
    if (!m) continue;
    const key = keyOf(m[1]);
    if (!key || out[key]) continue;
    out[key] = key === "expiry" || key === "mfg" ? textDate(m[2]) : m[2].trim();
  }
  return out;
}
