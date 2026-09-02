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

  2. A REDENOMINATION. The unit price is restated -- pence to pounds, or a unit split -- and
     the source splices the old scale onto the new without adjusting. The break factor is
     almost exactly 1/100 (0.0097x, 0.0099x, 0.0103x: the restatement plus that day's real
     move) and it never comes back. Nothing about the investment changed, so the early
     segment is rescaled by the break factor and the whole history is kept.

  3. AN UNREVERSED LEVEL BREAK THAT IS NOT A UNIT CHANGE. The early history belongs to a
     different instrument, or is junk. FRAS.L steps from 0.065 to 2.81 in February 2007 and
     never comes back; DSE.F steps to 63 million. Nothing can be recovered from before it,
     so the history is truncated and the fund's stated age drops accordingly.

WHAT TRIGGERS A REPAIR, AND WHY IT IS NOT JUST VOLATILITY
This pass used to look only at funds above 100% volatility. That misses the whole of case 2:
one ÷100 step in 1,935 daily observations lifts annualised volatility to about 39%, which
looks like an adventurous fund rather than a broken file, while the five-year return reads
-99%. WS Lindsell Train UK Equity was on the live site at -99.08% over five years for exactly
this reason. So the trigger is now the FAULT, not its effect: any single-step break in the
price series, or any stored figure no fund produces -- a 1/3/5-year return at or below -90%,
a CAGR at or below -40% a year, a worst-twelve-months or drawdown at or below -90%.

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

# A break within this tolerance of a round unit change is a redenomination, not a change of
# instrument. The tolerance has to be wide enough to swallow the real market move on the same
# day -- the observed factors run 0.0097 to 0.0103 -- and narrow enough not to claim a genuine
# collapse. NWG.L's 0.211x in January 2009 is a bank losing two-thirds of its value in a day;
# it matches nothing here and is left alone rather than rescaled into a comfortable fiction.
REDENOM_FACTORS = (0.001, 0.01, 100.0, 1000.0)
REDENOM_TOL = 0.10               # +/- 10% of the round factor


def redenomination(k):
    """The round unit factor this break is, or None if it is not one."""
    for f in REDENOM_FACTORS:
        if abs(k / f - 1.0) <= REDENOM_TOL:
            return f
    return None


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

    # Pass 2: a redenomination. The investment did not change, only the unit it is quoted
    # in, so rescale everything before the break rather than throwing that history away.
    guard = 0
    while guard < 10:
        guard += 1
        brk = [b for b in find_breaks(c) if redenomination(b[1])]
        if not brk:
            break
        i, k = brk[0]
        for x in range(0, i):
            c[x] *= k
        notes.append(f"rescaled {i} points before a {k:.4g}x redenomination")

    # Pass 3: whatever is left is a change of instrument, not a change of unit.
    brk = find_breaks(c)
    if brk:
        i = brk[-1][0]
        notes.append(f"truncated {i} points before an unreversed {brk[-1][1]:.4g}x break")
        c, t = c[i:], t[i:]
    return c, t, notes


def main():
    U = json.load(open(SRC, encoding="utf-8"))
    S = json.load(open(SER, encoding="utf-8"))

    # The stored series is sampled every fifth day, which is plenty to see a x100 step.
    def has_break(sym):
        ser = S["series"].get(sym)
        if not ser:
            return False
        c = ser["c"]
        return any(c[i - 1] > 0 and (c[i] / c[i - 1] > BREAK_UP or c[i] / c[i - 1] < BREAK_DN)
                   for i in range(1, len(c)))

    # A -95% drawdown is impossible for a diversified fund and ORDINARY for a single company
    # over a long history: Lloyds and NatWest really did fall that far through 2008-09, and a
    # leveraged ETP really can lose 99%. An earlier version of this guard dropped twenty real
    # shares as "impossible". So the return and break tests apply to FUNDS only; the
    # catastrophic-volatility net still covers everything.
    def is_fund(f):
        return f.get("type") != "EQUITY" and not f.get("leveraged")

    def impossible(f):
        if not is_fund(f):
            return False
        for k in ("r1", "r3", "r5", "worst12m", "maxDD"):
            if f.get(k) is not None and f[k] <= -90:
                return True
        return f.get("cagr") is not None and f["cagr"] <= -40

    suspect = [f for f in U["funds"]
               if (f.get("volDaily") or 0) > VOL_LIMIT
               or (is_fund(f) and (impossible(f) or has_break(f["symbol"])))]
    print(f"{len(suspect)} instruments look broken "
          f"(a price-series break, or a figure no fund produces)")
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
        if not st:
            dropped.append((sym, "could not be measured after repair"))
            continue
        if (st.get("volDaily") or 0) > VOL_LIMIT:
            dropped.append((sym, f"still {st['volDaily']:.0f}% volatility"))
            continue
        # WHAT COUNTS AS STILL BROKEN, AFTER a repair, IS MECHANICAL -- a remaining break, or
        # a volatility no market produces. It is deliberately NOT "a figure that looks too
        # bad": Liontrust Russia's -91.7% drawdown is a real fund meeting a real 2022, and an
        # earlier version of this guard threw it away for being implausible. Judging
        # plausibility is how a tool starts deciding which history it likes.
        if find_breaks(closes):
            dropped.append((sym, "a break survives the repair; the series is still spliced"))
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
