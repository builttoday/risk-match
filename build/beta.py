"""Recompute beta and correlation against the global GBP equity benchmark.

WHY THIS EXISTS SEPARATELY FROM fetch.py
fetch.py paired a fund with the benchmark by exact timestamp equality. Yahoo stamps an
LSE-listed ETF and an OEIC share class at different times of day, so the intersection was
usually empty and 63% of the universe came back with no beta at all -- silently, because a
missing beta looks the same as a fund that genuinely has too little history.

This recomputes both figures from the packed monthly sterling series, matching on calendar
month rather than on an exact second. Monthly is also the convention: a fund factsheet's
beta is computed from monthly returns, not daily ones, so this is the more comparable
number as well as the one that can actually be produced.

Every fund is measured over the SAME trailing window, so the betas can be read against each
other. A fund with less overlap than the minimum gets no beta rather than one computed over
a window nobody else was measured on.
"""
import json, math, os, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BENCH = "VWRP.L"
WINDOW = 60      # months -- five years, the window most factsheets quote
MIN_MONTHS = 36  # Morningstar's minimum for a published beta


def by_month(s):
    """{(year, month): close}. Later observations in a month win, which is what a
    month-end series wants."""
    out = {}
    for t, c in zip(s["t"], s["c"]):
        if c and c > 0:
            d = datetime.datetime.fromtimestamp(t, datetime.timezone.utc)
            out[(d.year, d.month)] = c
    return out


def main():
    S = json.load(open(os.path.join(ROOT, "series.json"), encoding="utf-8"))["series"]
    U = json.load(open(os.path.join(ROOT, "funds.json"), encoding="utf-8"))

    if BENCH not in S:
        raise SystemExit(f"benchmark {BENCH} has no series; cannot compute beta")
    bm = by_month(S[BENCH])
    keys = sorted(bm)[-WINDOW:]
    print(f"benchmark {BENCH}: {len(keys)} months, {keys[0]} to {keys[-1]}")

    done = skipped = 0
    for f in U["funds"]:
        sym = f["symbol"]
        f["beta"] = f["corr"] = None
        if sym not in S:
            skipped += 1
            continue
        fm = by_month(S[sym])

        # Consecutive months only: a return computed across a gap is not a monthly return.
        fr, br = [], []
        for i in range(1, len(keys)):
            a, b = keys[i - 1], keys[i]
            if a in fm and b in fm and a in bm and b in bm:
                fr.append(fm[b] / fm[a] - 1)
                br.append(bm[b] / bm[a] - 1)
        n = len(fr)
        if n < MIN_MONTHS:
            skipped += 1
            continue

        mf = sum(fr) / n
        mb = sum(br) / n
        cov = sum((fr[i] - mf) * (br[i] - mb) for i in range(n)) / (n - 1)
        vb = sum((x - mb) ** 2 for x in br) / (n - 1)
        vf = sum((x - mf) ** 2 for x in fr) / (n - 1)
        if vb > 0:
            f["beta"] = round(cov / vb, 2)
            if vf > 0:
                f["corr"] = round(cov / math.sqrt(vf * vb), 2)
            done += 1
        else:
            skipped += 1

    U["benchmark"] = BENCH
    U["betaWindowMonths"] = WINDOW
    U["betaFrom"] = f"{keys[0][0]}-{keys[0][1]:02d}"
    U["betaTo"] = f"{keys[-1][0]}-{keys[-1][1]:02d}"

    # Write through a temporary file. Dumping straight over funds.json truncates it before
    # the encoder runs, so one exception mid-serialise destroys the data file.
    dst = os.path.join(ROOT, "funds.json")
    tmp = dst + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(U, fh, indent=1)
    os.replace(tmp, dst)
    tot = len(U["funds"])
    print(f"beta computed for {done}/{tot} ({100*done/tot:.1f}%), {skipped} without enough overlap")


if __name__ == "__main__":
    main()
