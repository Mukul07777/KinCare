# Real strip photos for the OCR benchmark

Put phone photos of the **back of real medicine strips** here (jpg or png), then add one line per photo to
`../labels.csv`, typed by a person from what is printed on the strip (never copied from KinCare's output):

```
real/IMG_0412.jpg,real,Dolo 650,DOBS3975,08/2027,
```

`flagged` is optional: `yes` if the batch is on a CDSCO / state alert list, `no` if not, empty to skip that check.

Aim for variety: 20+ strips, different brands, foil glare, curved strips, low light, embossed (not printed) batch numbers.
Then run `python bench_strips.py` from `api/`. Results go to `data/strip_bench.json` and show on the /status page.
