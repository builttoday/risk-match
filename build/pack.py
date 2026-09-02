# -*- coding: utf-8 -*-
"""
Risk Match -- pack the build output into the two files the app loads.

  funds.json   every fund with its measured statistics, derived house and sector
  series.json  monthly GBP closes per fund, for the growth calculator

WHY MONTHLY IN THE APP: the build keeps weekly closes because covariance work wants the
resolution, but the growth calculator only ever answers "what would £1,000 have become", and
month-ends are enough for that. Monthly keeps the file a few megabytes instead of twenty, which
matters when the whole app is a static page a browser has to download before it can do anything.

Growth figures are computed in the browser from these series, so any number the tool shows can
be traced back to a price history rather than a stored result.
"""
import json, os, time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC_FUNDS = os.path.join(HERE, "funds_v3.json")
SRC_SERIES = os.path.join(HERE, "series_gbp.json")
SRC_FCA = os.path.join(HERE, "fca_cache.json")   # register matches, kept across rebuilds
OUT_FUNDS = os.path.join(ROOT, "funds.json")
OUT_SERIES = os.path.join(ROOT, "series.json")

KEEP = ("symbol", "name", "type", "house", "sector", "currency", "gbpConverted",
        "leveraged", "index", "years", "days", "volDaily", "volWeekly", "maxDD",
        "cagr", "sharpe", "sortino", "worst12m", "r1", "r3", "r5", "last",
        "beta", "corr", "stem", "derived",
        "fcaPrn", "fcaStatus", "fcaName", "fcaUrl", "fcaScore")


def month_key(ts):
    d = datetime.fromtimestamp(ts, tz=timezone.utc)
    return d.year * 12 + d.month


def to_monthly(t, c):
    """Last observation in each calendar month."""
    out_t, out_c, cur = [], [], None
    for ts, px in zip(t, c):
        k = month_key(ts)
        if cur is None or k != cur:
            if cur is not None:
                out_t.append(last_t); out_c.append(round(last_c, 6))
            cur = k
        last_t, last_c = ts, px
    if cur is not None:
        out_t.append(last_t); out_c.append(round(last_c, 6))
    return out_t, out_c


def main():
    fd = json.load(open(SRC_FUNDS, encoding="utf-8"))
    sd = json.load(open(SRC_SERIES, encoding="utf-8"))["series"]
    # The register matches live in their own cache so a rebuild of the universe carries them
    # forward. When they were held only on the fund record, growing the universe from 190 to
    # 982 wiped the whole FCA column without anything failing.
    fca, fca_at = {}, None
    if os.path.exists(SRC_FCA):
        _f = json.load(open(SRC_FCA, encoding="utf-8"))
        fca, fca_at = _f.get("matches", {}), _f.get("checkedAt")

    funds = []
    for f in fd["funds"]:
        rec = {k: f[k] for k in KEEP if k in f}
        rec.update(fca.get(f["symbol"], {}))
        s = sd.get(f["symbol"])
        if s and len(s["c"]) > 12:
            rec["firstDate"] = datetime.fromtimestamp(
                s["t"][0], tz=timezone.utc).strftime("%Y-%m")
            rec["hasSeries"] = True
        else:
            rec["hasSeries"] = False
        funds.append(rec)

    series = {}
    for sym, s in sd.items():
        t, c = to_monthly(s["t"], s["c"])
        if len(c) > 12:
            series[sym] = {"t0": t[0], "t": t, "c": c}

    json.dump({"builtAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "count": len(funds),
               "riskFree": fd.get("riskFree"), "benchmark": fd.get("benchmark"),
               "houses": fd.get("houses"), "sectors": fd.get("sectors"),
               "fcaCheckedAt": fca_at, "fcaMatched": sum(1 for r in funds if r.get("fcaPrn")),
               "funds": funds}, open(OUT_FUNDS, "w"), indent=1)
    json.dump({"builtAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "interval": "monthly", "currency": "GBP", "series": series},
              open(OUT_SERIES, "w"))

    spans = sorted((len(v["c"]) / 12.0) for v in series.values())
    print(f"{len(funds)} funds -> {OUT_FUNDS}  ({os.path.getsize(OUT_FUNDS)/1e6:.1f} MB)")
    print(f"{len(series)} series -> {OUT_SERIES}  ({os.path.getsize(OUT_SERIES)/1e6:.1f} MB)")
    if spans:
        print(f"history: median {spans[len(spans)//2]:.1f}y, "
              f"longest {spans[-1]:.1f}y, "
              f"{sum(1 for x in spans if x >= 10)} funds with 10y+, "
              f"{sum(1 for x in spans if x >= 20)} with 20y+")


if __name__ == "__main__":
    main()
