# -*- coding: utf-8 -*-
"""Repair price series with impossible statistics, and re-measure them.

WHAT WENT WRONG
A handful of instruments carried volatilities of 800%, 7,000%, even 1,958,187% a year. Those
are not risky funds, they are broken price histories, and they were being shown on the page
beside real numbers. Two distinct faults, which need different repairs:

  1. A DENOMINATION FLIP. The source reports a stretch of the history in a different unit --
     the pence trap again, but intermittent. GR8.L fell 99.0% in one month and rose 10,057%
     the next: a divide by 103 followed by a multiply by 101. The tell is that the two breaks
     invert each other, so the segment between them can simply be rescaled.

  2. AN UNREVERSED LEVEL BREAK. The early history belongs to a different instrument, or is
     junk. FRAS.L steps from 0.065 to 2.81 in February 2007 and never comes back;
     DSE.F steps to 63 million. Nothing can be recovered from before the break, so the
     history is truncated to start after it and the fund's stated age drops accordingly.

Only symbols that already look impossible are touched, and any that still look impossible
after repair are dropped rather than published -- a wrong number on a risk tool is worse
than a missing one.
"""
import json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fetch import chart, to_gbp, stats, session, BENCH   # noqa: E402

SRC = os.path.join(HERE, "funds_v2.json")
SER = os.path.join(HERE, "series_gbp.json")

VOL_LIMIT = 100.0      # % a year. Above this for a fund or a listed share is not a market move.
BREAK_UP, BREAK_DN = 4.0, 0.25   # one-day ratios no real instrument produces
FLIP_MAX_DAYS = 500              # how far ahead to look for the inverse of a flip


def find_breaks(c):
    return [(i, c[i] / c[i - 1]) for i in range(1, len(c)) if c[i - 1] > 0
            and (c[i] / c[i - 1] > BREAK_UP or c[i] / c[i - 1] < BREAK_DN)]


def repair(c, t):
    """Returns (closes, times, notes). Rescales inverted pairs, then truncates at whatever
    break is left, keeping the most recent segment."""
    c, t, notes = list(c), list(t), []

    # Pass 1: paired flips. Walk forward so a repair is visible to the next comparison.
    guard = 0
    while guard < 20:
        guard += 1
        brk = find_breaks(c)
        if not brk:
            break
        fixed = False
        for n, (i, k) in enumerate(brk):
            for j, k2 in brk[n + 1:]:
                if j - i > FLIP_MAX_DAYS:
                    break
                if abs(k * k2 - 1.0) < 0.25:
                    for x in range(i, j):
                        c[x] /= k
                    notes.append(f"rescaled {j - i} points by 1/{k:.4g}")
                    fixed = True
                    break
            if fixed:
                break
        if not fixed:
            break

    # Pass 2: whatever is left is a change of instrument, not a change of unit.
    brk = find_breaks(c)
    if brk:
        i = brk[-1][0]
        notes.append(f"truncated {i} points before an unreversed {brk[-1][1]:.4g}x break")
        c, t = c[i:], t[i:]
    return c, t, notes


def main():
    U = json.load(open(SRC, encoding="utf-8"))
    S = json.load(open(SER, encoding="utf-8"))

    suspect = [f for f in U["funds"] if (f.get("volDaily") or 0) > VOL_LIMIT]
    print(f"{len(suspect)} instruments above {VOL_LIMIT:.0f}% volatility")
    if not suspect:
        return

    s = session()
    bpx = chart(s, BENCH)
    bench = None
    if bpx:
        bc, _ = to_gbp(s, bpx)
        if bc:
            bench = {"t": bpx["t"][-len(bc):], "c": bc}

    byname = {f["symbol"]: f for f in U["funds"]}
    repaired, dropped = [], []
    for f in suspect:
        sym = f["symbol"]
        px = chart(s, sym)
        time.sleep(0.35)
        if not px:
            dropped.append((sym, "no price data on refetch"))
            continue
        closes, converted = to_gbp(s, px)
        if not closes:
            dropped.append((sym, "could not convert to GBP"))
            continue
        ts = px["t"][-len(closes):]
        closes, ts, notes = repair(closes, ts)
        if len(closes) < 260:
            dropped.append((sym, f"only {len(closes)} usable points after repair"))
            continue
        st = stats(closes, ts, bench)
        if not st or (st.get("volDaily") or 0) > VOL_LIMIT:
            dropped.append((sym, f"still {st.get('volDaily') if st else '?'}% volatility"))
            continue

        was = f.get("volDaily")
        byname[sym].update(st)
        byname[sym]["repaired"] = notes or ["re-measured"]
        S["series"][sym] = {"t": ts[::5], "c": [round(x, 6) for x in closes[::5]]}
        repaired.append((sym, was, st["volDaily"], st.get("years"), notes))

    keep = {d[0] for d in dropped}
    U["funds"] = [f for f in U["funds"] if f["symbol"] not in keep]
    for sym in keep:
        S["series"].pop(sym, None)

    for path, data in ((SRC, U), (SER, S)):
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=1 if path == SRC else None)
        os.replace(tmp, path)

    print(f"\nrepaired {len(repaired)}:")
    for sym, was, now, yrs, notes in repaired:
        print(f"  {sym:<11} vol {was:>12.1f}% -> {now:>6.1f}%  ({yrs}y)  {'; '.join(notes)}")
    print(f"\ndropped {len(dropped)}:")
    for sym, why in dropped:
        print(f"  {sym:<11} {why}")


if __name__ == "__main__":
    main()
