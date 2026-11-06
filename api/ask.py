"""'Ask the regulator': plain-language questions over the alert store.

Deterministic parsing, no LLM: every answer is a database query, and every
row it relies on is returned as a citation.
"""
import re

from rapidfuzz import fuzz

from matcher import normalise_batch, normalise_maker

MONTHS = "january february march april may june july august september october november december".split()
STOP = set("""a an the is are was were has have had did do does any of in for on to from by with and or me show list tell
which what how many much all this that these those there their its it be been batch batches medicine medicines drug drugs
alert alerts flagged failed fail found listed nsq spurious fake substandard quality standard not year month company maker
manufacturer made sample samples tablet tablets ip mg last recent latest please failure failures failing issue issues
problem problems recall recalls recalled list about give find get check checked""".split())
GENERIC = re.compile(r"\b(pharma\w*|labs?|laborator\w*|healthcare|life\s?sciences?|remedies|formulations?|drugs?|biotech\w*|industries)\b")


def _core(s: str) -> str:
    return " ".join(GENERIC.sub(" ", normalise_maker(s)).split())


def answer(conn, question: str) -> dict:
    q = question.strip()
    ql = q.lower()
    where, args, said = [], [], []

    # Batch number: a token with both letters/digits, or a long digit run.
    for tok in re.findall(r"[A-Za-z0-9][A-Za-z0-9\-/]{3,}", q):
        if re.search(r"\d", tok) and not re.fullmatch(r"(19|20)\d\d", tok) and (re.search(r"[A-Za-z]", tok) or len(tok) >= 5):
            hits = conn.execute("SELECT COUNT(*) FROM alerts WHERE batch_norm = ?", (normalise_batch(tok),)).fetchone()[0]
            if hits:
                where.append("batch_norm = ?")
                args.append(normalise_batch(tok))
                said.append(f"batch {tok.upper()}")
                break

    if "spurious" in ql or "fake" in ql or "nakli" in ql:
        where.append("category = 'spurious'")
        said.append("spurious")
    elif re.search(r"\bnsq\b|substandard|standard quality", ql):
        where.append("category = 'nsq'")
        said.append("not of standard quality")

    year = re.search(r"\b(20[12]\d)\b", ql)
    month = next((i for i, m in enumerate(MONTHS) if re.search(rf"\b{m[:3]}\w*\b", ql)), None)
    if year and month is not None:
        where.append("alert_month = ?")
        args.append(f"{year.group(1)}-{month + 1:02d}")
        said.append(f"{MONTHS[month].title()} {year.group(1)}")
    elif year:
        where.append("alert_month LIKE ?")
        args.append(f"{year.group(1)}-%")
        said.append(year.group(1))
    elif re.search(r"\b(this|last|latest|recent)\s+month\b", ql):
        where.append("alert_month = (SELECT MAX(alert_month) FROM alerts)")
        said.append("the latest month")

    if m := re.search(r"\b(state|cdsco)\b", ql):
        where.append("source = ?" if m.group(1) == "state" else "source IN ('cdsco_nsq','cdsco_spurious')")
        if m.group(1) == "state":
            args.append("state_nsq")
        said.append("state labs" if m.group(1) == "state" else "CDSCO labs")

    # Remaining words: a manufacturer or a medicine name.
    words = [w for w in re.findall(r"[a-z][a-z\-]{2,}", ql) if w not in STOP and w not in MONTHS and not any(w.startswith(m[:3]) and len(w) <= 4 for m in MONTHS)]
    if words and not any("batch_norm" in w for w in where):
        phrase = " ".join(words)
        makers = [r[0] for r in conn.execute("SELECT DISTINCT manufacturer FROM alerts WHERE manufacturer != ''")]
        scored = sorted(((fuzz.ratio(_core(m), _core(phrase)), m) for m in makers if _core(m)), reverse=True)
        maker_hits = [m for s, m in scored if s >= 88]
        if maker_hits:
            where.append(f"manufacturer IN ({','.join('?' * len(maker_hits))})")
            args += maker_hits
            said.append(f"made by {maker_hits[0].rstrip('.')}")
        else:
            for w in words:
                where.append("(LOWER(product_name) LIKE ? OR LOWER(brand) LIKE ?)")
                args += [f"%{w}%", f"%{w}%"]
            said.append(f"matching “{phrase}”")

    if not where:
        return {"answer": "Ask about a medicine, a manufacturer, a batch number, a month or a year. For example: “spurious drugs in 2026” or “paracetamol failures in 2025”.",
                "total": 0, "citations": [], "understood": []}

    clause = " AND ".join(where)
    total = conn.execute(f"SELECT COUNT(*) FROM alerts WHERE {clause}", args).fetchone()[0]
    rows = [dict(r) for r in conn.execute(f"SELECT * FROM alerts WHERE {clause} ORDER BY alert_month DESC LIMIT 10", args)]
    about = ", ".join(said)
    if total == 0:
        text = f"No published alert found for {about}. That means no regulator list names it, not that it was tested and passed."
    else:
        spur =sum(1 for r in rows if r["category"] == "spurious")
        text = (f"{total} alert row{'s' if total != 1 else ''} found for {about}."
                f" Most recent: {rows[0]['product_name']} (batch {rows[0]['batch_no']}), {rows[0]['alert_month']}."
                + (f" {spur} of the {len(rows)} shown are spurious." if spur else "")
                + (f" Showing the latest {len(rows)}." if total > len(rows) else ""))
    return {"answer": text, "total": total, "citations": rows, "understood": said}
