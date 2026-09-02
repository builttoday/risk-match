# -*- coding: utf-8 -*-
"""Does anything measurable predict a fund's growth?

THE TRAP THIS AVOIDS. Correlating the stored `cagr` against the stored statistics looks like
the obvious study and is worthless, for two reasons:

  1. CIRCULARITY. sharpe = (cagr - 4) / volDaily and sortino = (cagr - 4) / downside deviation.
     Correlating growth with either is correlating growth with itself; you get a large r and
     it means nothing.
  2. DIFFERENT WINDOWS. Each fund's cagr is measured over its own history -- 1.1 to 25.1
     years. A fund that compounded through 2009-2019 is not being compared with one that
     lived only through 2022-2026. The differences between periods swamp those between funds.

So everything here is recomputed from the monthly sterling series over ONE window common to
every fund, and the circular measures are rebuilt from that window rather than reused.

Reported: Pearson (linear), Spearman (monotonic, robust to the outliers a fund universe is
full of), a permutation test that assumes nothing about the distributions, partial
correlation controlling for volatility, and a multiple regression to see what survives when
the predictors compete. Bootstrap intervals on the headline figures.
"""
import json, math, os, datetime
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WINDOW = 60           # months, matching the beta window
MIN_MONTHS = 54       # a fund must cover almost all of it
RF = 4.0              # % a year, the stated risk-free rate
rng = np.random.default_rng(7)


def by_month(s):
    out = {}
    for t, c in zip(s["t"], s["c"]):
        if c and c > 0:
            d = datetime.datetime.fromtimestamp(t, datetime.timezone.utc)
            out[(d.year, d.month)] = c
    return out


def pearson(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    xm, ym = x - x.mean(), y - y.mean()
    d = math.sqrt(float((xm ** 2).sum()) * float((ym ** 2).sum()))
    return float((xm * ym).sum() / d) if d else float("nan")


def rank(a):
    """Average ranks, so ties do not distort Spearman."""
    a = np.asarray(a, float)
    order = a.argsort()
    r = np.empty(len(a), float)
    r[order] = np.arange(len(a), dtype=float)
    s = a[order]
    i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and s[j + 1] == s[i]:
            j += 1
        if j > i:
            r[order[i:j + 1]] = (i + j) / 2.0
        i = j + 1
    return r


def spearman(x, y):
    return pearson(rank(x), rank(y))


def perm_p(x, y, n=10000):
    """How often does a reshuffle beat the observed association? No distributional
    assumption, which matters because none of these variables is normal."""
    obs = abs(pearson(x, y))
    y = np.asarray(y, float)
    hits = 0
    for _ in range(n):
        if abs(pearson(x, rng.permutation(y))) >= obs:
            hits += 1
    return (hits + 1) / (n + 1)


def boot_ci(x, y, n=3000):
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = len(x)
    out = []
    for _ in range(n):
        i = rng.integers(0, m, m)
        out.append(pearson(x[i], y[i]))
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def partial(x, y, z):
    """Correlation of x and y with the linear effect of z removed from both."""
    rxy, rxz, ryz = pearson(x, y), pearson(x, z), pearson(y, z)
    d = math.sqrt((1 - rxz ** 2) * (1 - ryz ** 2))
    return (rxy - rxz * ryz) / d if d else float("nan")


def ols(X, y):
    """Least squares on standardised inputs, so coefficients compare directly."""
    X = np.asarray(X, float)
    y = np.asarray(y, float)
    Xs = (X - X.mean(0)) / X.std(0)
    ys = (y - y.mean()) / y.std()
    A = np.column_stack([np.ones(len(ys)), Xs])
    beta, *_ = np.linalg.lstsq(A, ys, rcond=None)
    resid = ys - A @ beta
    n, k = A.shape
    dof = n - k
    s2 = float((resid ** 2).sum()) / dof
    cov = s2 * np.linalg.pinv(A.T @ A)
    se = np.sqrt(np.diag(cov))
    t = beta / se
    r2 = 1 - float((resid ** 2).sum()) / float(((ys - ys.mean()) ** 2).sum())
    return beta, t, r2, dof


def betainc(a, b, x):
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(math.log(x) * a + math.log(1 - x) * b - lbeta) / a
    f, c, d = 1.0, 1.0, 0.0
    for i in range(300):
        m = i // 2
        if i == 0:
            num = 1.0
        elif i % 2 == 0:
            num = (m * (b - m) * x) / ((a + 2 * m - 1) * (a + 2 * m))
        else:
            num = -((a + m) * (a + b + m) * x) / ((a + 2 * m) * (a + 2 * m + 1))
        d = 1.0 + num * d
        if abs(d) < 1e-30:
            d = 1e-30
        d = 1.0 / d
        c = 1.0 + num / c
        if abs(c) < 1e-30:
            c = 1e-30
        f *= c * d
        if abs(1.0 - c * d) < 1e-10:
            break
    return front * (f - 1.0)


def t_to_p(t, dof):
    """Two-sided p from a t statistic, via the incomplete beta -- scipy is not installed."""
    return betainc(dof / 2.0, 0.5, dof / (dof + t * t))


def main():
    S = json.load(open(os.path.join(ROOT, "series.json"), encoding="utf-8"))["series"]
    U = json.load(open(os.path.join(ROOT, "funds.json"), encoding="utf-8"))
    F = {f["symbol"]: f for f in U["funds"]}
    BENCH = U.get("benchmark", "VWRP.L")

    bm = by_month(S[BENCH])
    keys = sorted(bm)[-WINDOW:]
    print("Common window: %d-%02d to %d-%02d (%d months), benchmark %s\n"
          % (keys[0][0], keys[0][1], keys[-1][0], keys[-1][1], len(keys), BENCH))

    rows = []
    for sym, f in F.items():
        if sym not in S:
            continue
        fm = by_month(S[sym])
        r, br = [], []
        for i in range(1, len(keys)):
            a, b = keys[i - 1], keys[i]
            if a in fm and b in fm:
                r.append(fm[b] / fm[a] - 1)
                br.append(bm[b] / bm[a] - 1)
        if len(r) < MIN_MONTHS:
            continue
        r = np.array(r)
        n = len(r)
        growth = float(np.prod(1 + r))
        if growth <= 0:
            continue
        yrs = n / 12.0
        cagr = (growth ** (1 / yrs) - 1) * 100
        vol = float(r.std(ddof=1)) * math.sqrt(12) * 100
        down = r[r < 0]
        dvol = float(down.std(ddof=1)) * math.sqrt(12) * 100 if len(down) > 6 else None

        eq = np.cumprod(1 + r)
        peak = np.maximum.accumulate(eq)
        mdd = float((eq / peak - 1).min()) * 100

        br = np.array(br)
        vb = float(br.var(ddof=1))
        beta = float(np.cov(r, br, ddof=1)[0, 1] / vb) if vb else None
        corr = pearson(r, br)

        w12 = None
        if n >= 12:
            w12 = min(float(np.prod(1 + r[i:i + 12]) - 1) * 100 for i in range(n - 11))

        rows.append({
            "sym": sym, "name": f.get("name") or sym, "sector": f.get("sector"),
            "cagr": cagr, "vol": vol, "dvol": dvol, "maxDD": mdd, "beta": beta,
            "corr": corr, "worst12m": w12,
            "sharpe": (cagr - RF) / vol if vol else None,
            "sortino": (cagr - RF) / dvol if dvol else None,
            "years": f.get("years"), "leveraged": bool(f.get("leveraged")),
            "isShare": f.get("type") == "EQUITY" and bool(f.get("index")),
        })

    rows = [r for r in rows if not r["leveraged"]]
    print("%d instruments over the identical window "
          "(leveraged and inverse products excluded)" % len(rows))

    # THE POOL CHANGES THE ANSWER, so all three are reported rather than one of them.
    # Adding 500 individual US shares to a universe of funds turned the volatility/growth
    # relationship from a hill -- rising, then collapsing in the most volatile tenth -- into
    # a plateau, because the most volatile tenth stopped being niche funds and became large
    # American companies. Neither reading is wrong; they answer different questions, and
    # quoting either alone as "the" result would be the misleading thing to do.
    for title, sub in [("FUNDS AND TRUSTS ONLY", [r for r in rows if not r["isShare"]]),
                       ("INDIVIDUAL SHARES ONLY", [r for r in rows if r["isShare"]]),
                       ("EVERYTHING TOGETHER", rows)]:
        if len(sub) < 60:
            continue
        print()
        print("#" * 78)
        print("## %s  (n = %d)" % (title, len(sub)))
        print("#" * 78)
        report(sub)


def report(rows):
    y = np.array([r["cagr"] for r in rows], float)
    preds = ["vol", "maxDD", "beta", "corr", "worst12m", "dvol", "years"]

    print("=" * 78)
    print("GROWTH (annualised, same window for every fund) vs each measure")
    print("=" * 78)
    print("%-11s%5s%9s%20s%10s%10s" % ("measure", "n", "Pearson", "95% CI", "Spearman", "perm p"))
    for k in preds:
        idx = [i for i, r in enumerate(rows) if r[k] is not None]
        if len(idx) < 40:
            continue
        xs = np.array([rows[i][k] for i in idx], float)
        ys = y[idx]
        rp, rs = pearson(xs, ys), spearman(xs, ys)
        lo, hi = boot_ci(xs, ys)
        p = perm_p(xs, ys)
        print("%-11s%5d%9.3f     [%6.3f,%6.3f]%10.3f%10.4f"
              % (k, len(idx), rp, lo, hi, rs, p))

    print("\nCIRCULAR BY CONSTRUCTION -- reported only to show why they are excluded:")
    for k in ("sharpe", "sortino"):
        idx = [i for i, r in enumerate(rows) if r[k] is not None]
        xs = np.array([rows[i][k] for i in idx], float)
        print("  %-9s Pearson %+.3f  (it is (growth - %.0f) over a risk measure, "
              "so this is growth against itself)" % (k, pearson(xs, y[idx]), RF))

    print("\n" + "=" * 78)
    print("PARTIAL CORRELATION with growth, controlling for volatility")
    print("=" * 78)
    base = [i for i, r in enumerate(rows) if r["vol"] is not None]
    for k in ("maxDD", "beta", "corr", "worst12m"):
        idx = [i for i in base if rows[i][k] is not None]
        if len(idx) < 40:
            continue
        xs = np.array([rows[i][k] for i in idx], float)
        zs = np.array([rows[i]["vol"] for i in idx], float)
        print("  %-10s raw %+.3f   controlling for vol %+.3f"
              % (k, pearson(xs, y[idx]), partial(xs, y[idx], zs)))

    print("\n" + "=" * 78)
    print("MULTIPLE REGRESSION -- standardised, so coefficients compare directly")
    print("=" * 78)
    use = ["vol", "maxDD", "beta", "corr", "worst12m"]
    idx = [i for i, r in enumerate(rows) if all(r[k] is not None for k in use)]
    X = np.array([[rows[i][k] for k in use] for i in idx], float)
    beta, t, r2, dof = ols(X, y[idx])
    print("  n = %d,  R2 = %.3f" % (len(idx), r2))
    print("  %-11s%9s%9s%10s" % ("predictor", "beta", "t", "p"))
    for j, k in enumerate(use):
        p = t_to_p(t[j + 1], dof)
        star = "  <-- significant" if p < 0.05 else ""
        print("  %-11s%9.3f%9.2f%10.4f%s" % (k, beta[j + 1], t[j + 1], p, star))

    print("\n" + "=" * 78)
    print("DID TAKING MORE RISK PAY? funds sorted into volatility deciles")
    print("=" * 78)
    srt = sorted([r for r in rows if r["vol"] is not None], key=lambda r: r["vol"])
    step = max(1, len(srt) // 10)
    print("  %-8s%5s%9s%18s%9s" % ("decile", "n", "vol %", "growth % a year", "median"))
    for d in range(10):
        chunk = srt[d * step: (d + 1) * step if d < 9 else len(srt)]
        if not chunk:
            continue
        print("  %-8d%5d%9.1f%18.1f%9.1f"
              % (d + 1, len(chunk),
                 float(np.mean([c["vol"] for c in chunk])),
                 float(np.mean([c["cagr"] for c in chunk])),
                 float(np.median([c["cagr"] for c in chunk]))))

    out = os.path.join(HERE, "correlations.json")
    json.dump({"window": ["%d-%02d" % (keys[0][0], keys[0][1]),
                          "%d-%02d" % (keys[-1][0], keys[-1][1])],
               "n": len(rows), "rows": rows},
              open(out, "w"), indent=1, default=str)
    print("\nper-fund window figures -> %s" % out)


if __name__ == "__main__":
    main()
