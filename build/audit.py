# -*- coding: utf-8 -*-
"""
Risk Match -- check the published data against everything it is supposed to be true of.

WHY THIS EXISTS. Three separate faults reached the live site this way: the Match band filter
returned nothing for weeks because a field the front end needed had stopped being produced;
twenty-six funds showed -99% five-year returns because a unit restatement was spliced onto the
old series; and eleven FTSE 100 shares were typed as funds, which took Rolls-Royce out of the
Shares view and put it top of the FUND rankings at +1,186%. None of them failed loudly. Each
one violated something obvious that nothing was checking.

So this checks the obvious things. It reads the published funds.json and series.json only --
no network, no build state -- and prints what does not hold. It exits non-zero if anything in
the ERROR class is found, so it can gate a deploy.

    python build/audit.py

Findings are graded. ERROR is a contradiction: something that cannot be true of correct data.
WARN is a smell: usually explainable, occasionally the first sign of a real fault. NOTE is
context, printed so the numbers are not mistaken for problems.
"""
import json, math, os, sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

errors, warns, notes = [], [], []


def err(cat, msg, rows=()):
    errors.append((cat, msg, list(rows)))


def warn(cat, msg, rows=()):
    warns.append((cat, msg, list(rows)))


def note(msg):
    notes.append(msg)


def name(f):
    return (f.get("name") or f["symbol"])[:44]


def main():
    F = json.load(open(os.path.join(ROOT, "funds.json"), encoding="utf-8"))
    S = json.load(open(os.path.join(ROOT, "series.json"), encoding="utf-8"))["series"]
    funds = F["funds"]
    by = {f["symbol"]: f for f in funds}
    note(f"{len(funds)} funds, {len(S)} price series, built {F.get('builtAt')}")

    # ---- identity -------------------------------------------------------------
    seen = {}
    dupes = []
    for f in funds:
        if f["symbol"] in seen:
            dupes.append(f["symbol"])
        seen[f["symbol"]] = f
    if dupes:
        err("identity", "the same symbol appears twice", dupes)

    # ---- what each row IS ------------------------------------------------------
    # An index tag is only ever put on a constituent share. If one carries any other type,
    # it has been retyped somewhere in the chain -- which is exactly how Rolls-Royce ended
    # up in the fund rankings.
    bad = [f"{f['symbol']} is {f['type']} but tagged {f['index']}"
           for f in funds if f.get("index") in ("FTSE100", "SP500") and f.get("type") != "EQUITY"]
    if bad:
        err("type", "an index constituent is not typed as a share", bad)

    bad = [f"{f['symbol']} {name(f)}" for f in funds
           if f.get("type") == "EQUITY" and f.get("index")
           and f.get("sector") != "UK Equity (single share)"
           and f.get("sector") != "US Equity (single share)"]
    if bad:
        err("type", "a share was given a fund's sector", bad)

    bad = [f"{f['symbol']} is {f['type']}" for f in funds
           if f["symbol"].startswith("0P") and f.get("type") not in (None, "MUTUALFUND")]
    if bad:
        err("type", "a 0P (Morningstar) identifier is not typed as a fund", bad)

    bad = [f"{f['symbol']} {name(f)}" for f in funds
           if f.get("type") == "EQUITY" and not f.get("index")
           and f.get("house") != "— single company share"]
    if bad:
        warn("type", "a listed company with no index tag, filed under a fund manager", bad[:12])

    # ---- the fields the front end needs ---------------------------------------
    need = ("name", "type", "sector", "house", "volDaily", "years")
    for k in need:
        miss = [f["symbol"] for f in funds if f.get(k) in (None, "")]
        if miss:
            err("fields", f"'{k}' is missing, and nothing fails when it is", miss[:12])
    miss = [f["symbol"] for f in funds if f.get("volWeekly") is None]
    if miss:
        warn("fields", "no weekly volatility, so the SRRI comparison is blank", miss[:12])

    # ---- statistics that cannot be what they say -------------------------------
    def bad_range(k, lo, hi, cat="numbers", msg=None, fund_only=True):
        rows = []
        for f in funds:
            if fund_only and (f.get("type") == "EQUITY" or f.get("leveraged")):
                continue
            v = f.get(k)
            if v is not None and not (lo <= v <= hi):
                rows.append(f"{f['symbol']} {k}={v}  {name(f)}")
        if rows:
            err(cat, msg or f"'{k}' outside {lo} to {hi}", rows[:12])

    bad_range("volDaily", 0.0, 100.0, msg="a volatility no fund produces")
    bad_range("r5", -90.0, 2000.0, msg="a five-year return no fund produces")
    bad_range("r3", -90.0, 2000.0, msg="a three-year return no fund produces")
    bad_range("r1", -90.0, 500.0, msg="a one-year return no fund produces")
    bad_range("cagr", -40.0, 200.0, msg="a growth rate no fund sustains")
    bad_range("maxDD", -100.0, 0.0, msg="a drawdown that is not a fall")
    bad_range("beta", -3.0, 4.0, msg="a beta outside anything a fund shows")
    bad_range("corr", -1.0, 1.0, fund_only=False, msg="a correlation outside -1 to 1")

    # Weekly and daily volatility measure the same thing at two sampling rates. They differ,
    # but not by multiples: a big divergence means one of the two series is wrong.
    rows = [f"{f['symbol']} daily={f['volDaily']} weekly={f['volWeekly']}  {name(f)}"
            for f in funds
            if f.get("volDaily") and f.get("volWeekly")
            and not (0.4 <= f["volWeekly"] / f["volDaily"] <= 2.5)]
    if rows:
        warn("numbers", "weekly and daily volatility disagree by more than a factor", rows[:12])

    # Sharpe is (growth - 4%) / volatility. If the sign disagrees with that, it was computed
    # from something other than the numbers now stored beside it.
    rows = []
    for f in funds:
        c, v, sh = f.get("cagr"), f.get("volDaily"), f.get("sharpe")
        if None in (c, v, sh) or not v:
            continue
        want = (c - F.get("riskFree", 4.0)) / v
        # Sharpe is computed from unrounded inputs and then all three are stored to 2dp, so
        # the check has to allow for BOTH roundings: 0.005 on the numerator, and 0.005 on a
        # volatility that may itself be 0.16. On a very calm fund that is a fifth of a point
        # of Sharpe -- arithmetic, not a fault. Anything wider than that is worth seeing.
        tol = max(0.05, (0.005 + abs(sh) * 0.005) / v)
        if abs(want - sh) > tol:
            rows.append(f"{f['symbol']} sharpe={sh} but (cagr {c} - rf)/vol {v} = {want:.2f}")
    if rows:
        err("numbers", "Sharpe does not follow from the figures shown beside it", rows[:12])

    # ---- the series behind the figures ----------------------------------------
    now = datetime.now(timezone.utc)
    stale, gaps, breaks, mismatch, share_breaks = [], [], [], [], []
    for f in funds:
        s = S.get(f["symbol"])
        if not s:
            if f.get("hasSeries"):
                mismatch.append(f"{f['symbol']} claims a series but none was published")
            continue
        t, c = s["t"], s["c"]
        end = datetime.fromtimestamp(t[-1], tz=timezone.utc)
        if (now - end).days > 45:
            stale.append(f"{f['symbol']} last priced {end.date()}  {name(f)}")
        for i in range(1, len(t)):
            if (t[i] - t[i - 1]) / 86400.0 > 200:
                gaps.append(f"{f['symbol']} {(t[i]-t[i-1])/86400:.0f}-day hole at "
                            f"{datetime.fromtimestamp(t[i], tz=timezone.utc).date()}")
                break
        for i in range(1, len(c)):
            if c[i - 1] > 0 and (c[i] / c[i - 1] > 4 or c[i] / c[i - 1] < 0.25):
                # Taylor Wimpey fell 79% in a month in 2008 and rose 151% two months later.
                # That is a housebuilder meeting the financial crisis, not a broken file --
                # so for a single company this is worth seeing, not worth failing on.
                row = f"{f['symbol']} {c[i]/c[i-1]:.4g}x step  {name(f)}"
                (share_breaks if f.get("type") == "EQUITY" else breaks).append(row)
                break
        # The stated age has to match the series it was measured from.
        span = (t[-1] - t[0]) / (365.25 * 86400)
        if f.get("years") and abs(span - f["years"]) > 1.2:
            mismatch.append(f"{f['symbol']} says {f['years']}y, series spans {span:.1f}y")
    if breaks:
        err("series", "a price step no fund makes", breaks[:12])
    if share_breaks:
        warn("series", "a single company moving further than any fund could", share_breaks[:12])
    if gaps:
        err("series", "a hole in the history, measured straight across", gaps[:12])
    if mismatch:
        err("series", "the stated history does not match the series", mismatch[:12])
    if stale:
        warn("series", "not priced recently -- closed, merged or delisted?", stale[:12])

    # ---- the benchmark checks itself ------------------------------------------
    b = by.get(F.get("benchmark") or "")
    if b:
        if b.get("beta") is not None and abs(b["beta"] - 1.0) > 0.02:
            err("benchmark", f"the benchmark's own beta is {b['beta']}, not 1.00")
        else:
            note(f"benchmark {b['symbol']} beta {b.get('beta')}, correlation {b.get('corr')}"
                 " -- the arithmetic is wired up correctly")

    # ---- things that are fine but worth seeing --------------------------------
    note(f"{sum(1 for f in funds if f.get('type') == 'EQUITY' and f.get('index'))} index "
         f"constituents, {sum(1 for f in funds if f.get('type') == 'ETF')} ETFs, "
         f"{sum(1 for f in funds if f.get('type') == 'MUTUALFUND')} funds")
    unc = sum(1 for f in funds if f.get("sector") == "Unclassified")
    note(f"{unc} funds the name-based sector rules could not place "
         f"({unc * 100.0 / len(funds):.0f}%) -- shown as Unclassified, not guessed")
    lev = sum(1 for f in funds if f.get("leveraged"))
    note(f"{lev} leveraged or inverse products, hidden by default")

    # ---- report ---------------------------------------------------------------
    for label, items in (("ERROR", errors), ("WARN", warns)):
        for cat, msg, rows in items:
            print(f"\n{label}  [{cat}]  {msg}")
            for r in rows:
                print(f"    {r}")
    print("\nNOTES")
    for n in notes:
        print(f"    {n}")
    print(f"\n{len(errors)} error(s), {len(warns)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
