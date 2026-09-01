# -*- coding: utf-8 -*-
"""
Risk Match -- funds-of-funds construction, built on the measured metrics and validated
properly.

NOT ADVICE. No rating, no ranking for suitability, no recommendation. This is a backtest of
mechanical rules over public sterling price history.

WHAT MAKES THIS MORE THAN A CURVE FIT
-------------------------------------
1. WALK-FORWARD, NOT ONE SPLIT. A single build/test split can be luck. The history is cut into
   several consecutive folds; every portfolio is rebuilt using only data before each fold and
   scored on the fold itself. What gets reported is the mean AND the spread across folds,
   because a rule that wins on average but loses in a third of periods is not a good rule.
2. SHRINKAGE, NOT RAW COVARIANCE. Minimum-variance optimisation on a sample covariance matrix
   is error-maximising: it loads onto whichever fund's correlation was underestimated by noise.
   The covariance is shrunk toward a constant-correlation target, and the shrinkage strength is
   chosen by cross-validation INSIDE the build window -- never using test data.
3. SELECTION FROM MEASURED METRICS. Funds are chosen by the statistics fetch.py computed --
   Sharpe, Sortino, beta, worst 12 months, correlation -- rather than by name or past return
   alone. "Best past return" is kept deliberately as a control: it is what most people actually
   do, and the out-of-sample column shows what it is worth.
4. A BOOTSTRAP, NOT A POINT ESTIMATE. Beating a benchmark by 0.4% a year means nothing without
   knowing the noise. Fold returns are resampled to give a rough confidence interval on the
   difference.

TWO BIASES THAT FLATTER EVERY NUMBER HERE
  SURVIVORSHIP -- the universe is funds alive today with five years of history; the ones that
  closed after doing badly are missing. This alone can add a point a year to a fund backtest.
  COSTS -- fund NAVs are net of the fund's own charges, but PLATFORM_FEE is applied on top for
  the platform. Transaction costs of rebalancing are NOT modelled.
"""
import json, math, os, random
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SERIES = os.path.join(HERE, "series_gbp.json")
FUNDS = os.path.join(HERE, "funds_v2.json")
OUT = os.path.join(HERE, "portfolios.json")

PLATFORM_FEE = 0.35
RISK_FREE = 4.0
BENCHMARKS = ["VWRP.L", "VUKE.L", "IWDG.L", "^FTSE"]
N_HOLD = 10
FOLDS = 4
WPY = 52.0
random.seed(7)
np.random.seed(7)


# --------------------------------------------------------------------------- data
def load():
    s = json.load(open(SERIES, encoding="utf-8"))["series"]
    f = {x["symbol"]: x for x in json.load(open(FUNDS, encoding="utf-8"))["funds"]}
    return s, f


def align(series, syms, years=6.5, min_cover=0.45):
    """Weekly return matrix on a COMMON DATE AXIS.

    min_cover is deliberately loose. Each series was sampled every fifth trading day FROM ITS
    OWN START, so two funds with different inception dates sit on different day-of-week grids
    and rarely share exact timestamps. Demanding 98% exact matches silently excluded every
    benchmark. Gaps are forward-filled, which for weekly data is a fair approximation.

    The window is 6.5 years, not longer, because the global GBP benchmark (VWRP.L) only
    launched in 2019 -- an 8-year axis silently excluded every benchmark, leaving the test
    with nothing to beat. Better a slightly shorter window than a comparison against nothing.

    The first version intersected every symbol's timestamps, which returns almost nothing once
    759 funds with different inception dates and holiday calendars are involved -- one fund
    missing one week drops that week for everyone. Instead: build the axis from the dates that
    appear most often across the universe over the chosen window, keep funds that cover at
    least `min_cover` of it, and forward-fill the odd missing week.
    """
    import collections
    now = max(max(v["t"]) for v in series.values() if v["t"])
    start = now - years * 365.25 * 86400
    freq = collections.Counter()
    for sym in syms:
        v = series.get(sym)
        if not v:
            continue
        for t in v["t"]:
            if t >= start:
                freq[t] += 1
    if not freq:
        return [], {}
    # a date is on the axis if a decent share of funds priced that week
    peak = max(freq.values())
    axis = sorted(t for t, n in freq.items() if n >= peak * 0.60)
    if len(axis) < 60:
        return [], {}

    out = {}
    for sym in syms:
        v = series.get(sym)
        if not v:
            continue
        # Walk the fund's own timestamps with a pointer and take the latest observation at
        # or before each axis date. The previous version only filled on an exact timestamp
        # match, so a series on a different weekday grid never initialised at all -- which is
        # why every benchmark silently vanished despite having full coverage.
        ts, cs = v["t"], v["c"]
        j, last, px = 0, None, []
        for t in axis:
            while j < len(ts) and ts[j] <= t:
                last = cs[j]; j += 1
            if last is None:
                px = []
                break
            px.append(last)
        own = sum(1 for t in ts if t >= axis[0])
        if not px or own < len(axis) * min_cover:
            continue
        out[sym] = np.array([px[i] / px[i - 1] - 1.0 for i in range(1, len(px))])
    return axis[1:], out


# --------------------------------------------------------------------------- stats
def perf(r, fee=PLATFORM_FEE):
    r = np.asarray(r, dtype=float)
    if r.size < 8:
        return None
    wk = (fee / 100.0) / WPY
    growth = np.cumprod(1 + r - wk)
    peak = np.maximum.accumulate(growth)
    mdd = float((growth / peak - 1).min()) * 100
    yrs = r.size / WPY
    cagr = (float(growth[-1]) ** (1 / yrs) - 1) * 100 if yrs > 0.2 else None
    vol = float(r.std(ddof=1)) * math.sqrt(WPY) * 100
    dn = r[r < 0]
    dsd = float(dn.std(ddof=1)) * math.sqrt(WPY) * 100 if dn.size > 5 else None
    return {"cagr": round(cagr, 2) if cagr is not None else None,
            "vol": round(vol, 2), "maxDD": round(mdd, 1),
            "sharpe": round((cagr - RISK_FREE) / vol, 2) if cagr is not None and vol else None,
            "sortino": round((cagr - RISK_FREE) / dsd, 2) if cagr is not None and dsd else None,
            "weeks": int(r.size)}


def shrunk_cov(X):
    """Sample covariance shrunk toward a constant-correlation target. The shrinkage weight is
    picked by 5-fold CV inside the supplied window, minimising realised portfolio variance --
    so no test data is touched."""
    n, p = X.shape
    S = np.cov(X, rowvar=False)
    sd = np.sqrt(np.diag(S))
    sd[sd == 0] = 1e-12
    R = S / np.outer(sd, sd)
    rbar = (R.sum() - p) / (p * (p - 1)) if p > 1 else 0.0
    F = rbar * np.outer(sd, sd)
    np.fill_diagonal(F, np.diag(S))

    best, best_d = None, 0.5
    idx = np.arange(n)
    np.random.shuffle(idx)
    folds = np.array_split(idx, 5)
    for d in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0):
        v = []
        for k in range(5):
            te = folds[k]
            tr = np.concatenate([folds[j] for j in range(5) if j != k])
            if tr.size < p + 5 or te.size < 3:
                continue
            Str = np.cov(X[tr], rowvar=False)
            sdt = np.sqrt(np.diag(Str)); sdt[sdt == 0] = 1e-12
            Rt = Str / np.outer(sdt, sdt)
            rb = (Rt.sum() - p) / (p * (p - 1)) if p > 1 else 0.0
            Ft = rb * np.outer(sdt, sdt); np.fill_diagonal(Ft, np.diag(Str))
            C = (1 - d) * Str + d * Ft
            w = min_var_weights(C)
            v.append(float(np.var(X[te] @ w, ddof=1)))
        if v:
            m = float(np.mean(v))
            if best is None or m < best:
                best, best_d = m, d
    return (1 - best_d) * S + best_d * F, best_d


def min_var_weights(C):
    """Long-only minimum variance by projected gradient. No inversion, so a near-singular
    covariance cannot produce absurd leverage."""
    p = C.shape[0]
    w = np.ones(p) / p
    step = 1.0 / (np.trace(C) / p * p * 4 + 1e-12)
    for _ in range(3000):
        g = 2 * C @ w
        w = w - step * (g - g.mean())
        w = np.maximum(w, 0)
        t = w.sum()
        w = w / t if t > 0 else np.ones(p) / p
    return w


# --------------------------------------------------------------- selection (uses metrics)
def sel_metric(cands, R, meta, k, key, reverse=True, guard=True):
    """Rank on a measured metric, but computed on the BUILD window only, not the stored
    lifetime figure -- otherwise future information leaks in through the metric."""
    scored = []
    for s in cands:
        st = perf(R[s], fee=0.0)
        if not st or st["cagr"] is None:
            continue
        if guard and st["maxDD"] < -60:
            continue
        v = st.get(key)
        if v is None:
            continue
        scored.append((v, s))
    scored.sort(reverse=reverse)
    return [s for _, s in scored[:k]]


def sel_decorrelated(cands, R, meta, k):
    """Greedy diversification: start from the lowest-volatility fund, then add whichever has
    the lowest mean correlation to what is already held."""
    M = {s: R[s] for s in cands}
    sd = {s: float(v.std(ddof=1)) or 1e-12 for s, v in M.items()}
    chosen = [min(cands, key=lambda s: sd[s])]
    A = np.vstack([M[s] for s in cands])
    idx = {s: i for i, s in enumerate(cands)}
    C = np.corrcoef(A)
    while len(chosen) < k:
        best, bv = None, 9e9
        ci = [idx[c] for c in chosen]
        for s in cands:
            if s in chosen:
                continue
            v = float(np.mean(C[idx[s], ci]))
            if v < bv:
                best, bv = s, v
        if best is None:
            break
        chosen.append(best)
    return chosen


SELECTORS = {
    "highest Sharpe":        lambda c, R, m, k: sel_metric(c, R, m, k, "sharpe"),
    "highest Sortino":       lambda c, R, m, k: sel_metric(c, R, m, k, "sortino"),
    "shallowest drawdown":   lambda c, R, m, k: sel_metric(c, R, m, k, "maxDD"),
    "least correlated":      sel_decorrelated,
    "best past return":      lambda c, R, m, k: sel_metric(c, R, m, k, "cagr"),
}

WEIGHTS = {
    "equal": lambda X: np.ones(X.shape[1]) / X.shape[1],
    "inverse vol": lambda X: (lambda v: v / v.sum())(1.0 / (X.std(axis=0, ddof=1) + 1e-12)),
    "min variance (shrunk)": lambda X: min_var_weights(shrunk_cov(X)[0]),
}


def main():
    series, funds = load()
    universe = [s for s, f in funds.items()
                if f.get("type") in ("MUTUALFUND", "ETF")
                and (f.get("years") or 0) >= 4.5 and s in series]
    print(f"universe: {len(universe)} funds")
    dates, R = align(series, universe + BENCHMARKS)
    if not dates:
        print("no common timeline"); return
    usable = [s for s in universe if s in R and R[s].size > 200]
    n = len(dates)
    print(f"{len(usable)} usable funds on {n} weekly points ({n/WPY:.1f}y)\n")

    bounds = [int(n * (i + 1) / (FOLDS + 1)) for i in range(FOLDS + 1)]
    results = {}
    for sname, sel in SELECTORS.items():
        for wname, wf in WEIGHTS.items():
            per_fold, holds = [], None
            for k in range(FOLDS):
                a, b = bounds[k], bounds[k + 1]
                build = {s: R[s][:a] for s in usable}
                chosen = sel(usable, build, funds, N_HOLD)
                if len(chosen) < 3:
                    continue
                X = np.column_stack([build[s] for s in chosen])
                w = wf(X)
                test = np.column_stack([R[s][a:b] for s in chosen])
                p = perf(test @ w)
                if p:
                    per_fold.append(p)
                    holds = chosen
            if per_fold:
                cag = [f["cagr"] for f in per_fold if f["cagr"] is not None]
                results[(sname, wname)] = {
                    "selection": sname, "weighting": wname, "folds": per_fold,
                    "meanCagr": round(float(np.mean(cag)), 2),
                    "worstFold": round(float(np.min(cag)), 2),
                    "spread": round(float(np.std(cag)), 2),
                    "meanVol": round(float(np.mean([f["vol"] for f in per_fold])), 2),
                    "meanSharpe": round(float(np.mean([f["sharpe"] for f in per_fold
                                                       if f["sharpe"] is not None])), 2),
                    "lastHoldings": holds}

    bench = {}
    for bsym in BENCHMARKS:
        if bsym not in R:
            continue
        fol = []
        for k in range(FOLDS):
            p = perf(R[bsym][bounds[k]:bounds[k + 1]])
            if p:
                fol.append(p)
        if fol:
            cag = [f["cagr"] for f in fol if f["cagr"] is not None]
            bench[bsym] = {"meanCagr": round(float(np.mean(cag)), 2),
                           "worstFold": round(float(np.min(cag)), 2),
                           "meanVol": round(float(np.mean([f["vol"] for f in fol])), 2),
                           "folds": fol}

    print(f"{'selection':<24}{'weighting':<24}{'mean':>8}{'worst':>8}{'spread':>8}{'vol':>7}{'sharpe':>8}")
    print("-" * 87)
    for r in sorted(results.values(), key=lambda z: -z["meanCagr"]):
        print(f"{r['selection']:<24}{r['weighting']:<24}{r['meanCagr']:>8.2f}"
              f"{r['worstFold']:>8.2f}{r['spread']:>8.2f}{r['meanVol']:>7.2f}{r['meanSharpe']:>8.2f}")
    print()
    for b, v in sorted(bench.items(), key=lambda z: -z[1]["meanCagr"]):
        print(f"BENCHMARK {b:<14}{'':<20}{v['meanCagr']:>8.2f}{v['worstFold']:>8.2f}"
              f"{'':>8}{v['meanVol']:>7.2f}")

    if bench:
        bb = max(bench.items(), key=lambda z: z[1]["meanCagr"])
        bcag = [f["cagr"] for f in bb[1]["folds"] if f["cagr"] is not None]
        print(f"\nbest benchmark out of sample: {bb[0]} at {bb[1]['meanCagr']}% a year\n")
        for r in sorted(results.values(), key=lambda z: -z["meanCagr"])[:5]:
            d = [c - b for c, b in zip([f["cagr"] for f in r["folds"]], bcag)]
            if len(d) >= 3:
                boot = [float(np.mean(np.random.choice(d, len(d), replace=True)))
                        for _ in range(4000)]
                lo, hi = np.percentile(boot, [5, 95])
                wins = sum(1 for x in d if x > 0)
                print(f"  {r['selection']:<22}{r['weighting']:<22} "
                      f"excess {np.mean(d):+.2f}%  90% CI [{lo:+.2f}, {hi:+.2f}]  "
                      f"beat benchmark in {wins}/{len(d)} folds")

    json.dump({"platformFee": PLATFORM_FEE, "riskFree": RISK_FREE, "hold": N_HOLD,
               "folds": FOLDS,
               "portfolios": [v for v in results.values()], "benchmarks": bench,
               "caveats": ["survivorship bias: universe is funds alive today",
                           "walk-forward: each fold built only on prior data",
                           "backtest only -- not advice, not a recommendation",
                           "platform fee applied; rebalancing costs not modelled"]},
              open(OUT, "w"), indent=1)
    print(f"\n-> {OUT}")


if __name__ == "__main__":
    main()
