"""Seed simulated symptom reports so Early Signal can be demoed without real patients.

Every row is stored with origin='simulated' and the UI labels it. Remove them with --clear.

    python -m simulate --batch KT24117 --brand "Paracip 500" --city Delhi --reports 7 --symptom no_effect
    python -m simulate --clear
"""
import argparse
import random
import string

from checkin import SYMPTOMS
from db import connect
from matcher import normalise_batch

CITIES = ["Delhi", "Noida", "Gurugram", "Ghaziabad", "Faridabad", "Jaipur", "Lucknow", "Chandigarh"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch")
    ap.add_argument("--brand")
    ap.add_argument("--maker")
    ap.add_argument("--city", default="Delhi")
    ap.add_argument("--reports", type=int, default=7)
    ap.add_argument("--symptom", default="no_effect", choices=list(SYMPTOMS))
    ap.add_argument("--background", type=int, default=40, help="scattered reports across other batches, the baseline PRR compares against")
    ap.add_argument("--clear", action="store_true")
    a = ap.parse_args()
    conn = connect()
    if a.clear:
        n = conn.execute("DELETE FROM reports WHERE origin = 'simulated'").rowcount
        conn.commit()
        print(f"removed {n} simulated reports")
        return
    if not a.batch:
        ap.error("--batch is required")

    rnd = random.Random(7)
    keys = list(SYMPTOMS)
    rows = []
    for i in range(a.background):  # common, mild complaints spread thinly over many batches
        b = "".join(rnd.choices(string.ascii_uppercase, k=2)) + str(rnd.randint(1000, 99999))
        rows.append((f"sim-bg-{i}", b, None, rnd.choice(CITIES), rnd.sample(keys[:5], rnd.randint(1, 2))))
    near = [c for c in CITIES if c != a.city]
    for i in range(a.reports):  # the cluster: one symptom on one batch, mostly one area
        extra = rnd.sample([k for k in keys[:5] if k != a.symptom], rnd.randint(0, 1))
        rows.append((f"sim-{a.batch}-{i}", a.batch, a.brand, a.city if i % 3 else rnd.choice(near), [a.symptom, *extra]))

    for dev, batch, brand, city, sym in rows:
        conn.execute(
            """INSERT OR REPLACE INTO reports (device, batch, batch_norm, brand, maker, city, symptoms, origin)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'simulated')""",
            (dev, batch, normalise_batch(batch), brand if batch == a.batch else None, a.maker if batch == a.batch else None, city, ",".join(sorted(sym))),
        )
    conn.commit()
    print(f"seeded {a.reports} reports on {a.batch} and {a.background} background reports (all marked simulated)")


if __name__ == "__main__":
    main()
