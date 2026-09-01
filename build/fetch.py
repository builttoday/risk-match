# -*- coding: utf-8 -*-
"""
Risk Match -- price every candidate, convert to GBP, and measure it.

EVERYTHING IS REPORTED IN STERLING. A global manager's share class may be priced in USD, EUR
or CHF, and for a UK investor the volatility that matters is the volatility *after* the
currency moves, not the local-currency figure on the factsheet. So each price series is
converted to GBP with a matching daily FX series before any statistic is computed. Funds that
had to be converted are flagged, because their sterling volatility includes currency risk that
a GBP-hedged share class would not carry.

THE PENCE TRAP: the London Stock Exchange quotes most things in GBp (pence), and Yahoo reports
that as the currency. A series in pence divided by nothing is a hundred times too large. It
does not change volatility -- that is scale-invariant -- but it wrecks any level comparison, so
it is normalised here.

TWO VOLATILITY NUMBERS, deliberately:
  volDaily  = stdev(daily returns) x sqrt(252)   -- what the tool has always shown
  volWeekly = stdev(weekly returns) x sqrt(52)   -- the SRRI convention used on every UCITS
              KIID, and therefore the number a firm's risk bands were probably calibrated
              against. Showing both stops a fund looking like a band 5 here and a band 4 on
              its own factsheet with no explanation.

Nothing here rates, ranks or recommends anything. It measures.
"""
import json, math, os, time
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
CAND = os.path.join(HERE, "candidates.json")
OUT = os.path.join(HERE, "funds_v2.json")
SERIES = os.path.join(HERE, "series_gbp.json")   # weekly GBP closes for growth + portfolios

RISK_FREE = 4.0          # % a year. Stated, not hidden -- Sharpe is meaningless without it.
BENCH = "VWRP.L"         # global equity, GBP: the correlation/beta reference
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

_fx_cache = {}


def session():
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept": "application/json"})
    try:
        s.get("https://finance.yahoo.com/", timeout=20)
    except Exception:
        pass
    return s


YEARS_BACK = 25

def chart(s, sym, rng=None, interval="1d"):
    """Yahoo's range=max is broken for daily data -- it returned 152 points for a fund that
    range=5y gave 1262 for. Explicit period1/period2 timestamps are the only reliable way to
    ask for long history, and they returned 6347 daily points (~25 years) on the same test."""
    try:
        now = int(time.time())
        r = s.get(f"https://query2.finance.yahoo.com/v8/finance/chart/{sym}",
                  timeout=30, params={"period1": now - YEARS_BACK * 365 * 86400,
                                      "period2": now, "interval": interval})
        if r.status_code != 200:
            return None
        res = (r.json().get("chart") or {}).get("result") or []
        if not res:
            return None
        d = res[0]
        ts = d.get("timestamp") or []
        q = ((d.get("indicators") or {}).get("quote") or [{}])[0]
        adj = ((d.get("indicators") or {}).get("adjclose") or [{}])
        closes = (adj[0].get("adjclose") if adj and adj[0].get("adjclose") else q.get("close")) or []
        meta = d.get("meta") or {}
        cur = meta.get("currency") or ""
        # Non-positive closes appear in long histories (bad ticks, delisted stubs). They make
        # a price ratio negative, and a negative number raised to 1/years is COMPLEX in
        # Python -- which crashed the run rather than producing a wrong number, fortunately.
        pairs = [(t, c) for t, c in zip(ts, closes) if c is not None and c > 0]
        # longName is the ONLY place Yahoo gives the untruncated fund name -- search's
        # shortname is cut at 30 characters, which removes exactly the descriptive tail the
        # sector classifier needs ("T. Rowe Price Funds SICAV - Asi...").
        return {"cur": cur, "longName": meta.get("longName") or meta.get("shortName") or "",
                "t": [p[0] for p in pairs], "c": [float(p[1]) for p in pairs]}
    except Exception:
        return None


def fx_to_gbp(s, cur):
    """Daily series of GBP per unit of `cur`, keyed by timestamp."""
    cur = cur.upper()
    if cur in ("GBP", "GBX", "GBP="):
        return {}
    if cur in _fx_cache:
        return _fx_cache[cur]
    series = None
    d = chart(s, f"{cur}GBP=X")
    if d and len(d["c"]) > 100:
        series = {t: c for t, c in zip(d["t"], d["c"])}
    else:
        d = chart(s, f"GBP{cur}=X")
        if d and len(d["c"]) > 100:
            series = {t: (1.0 / c) for t, c in zip(d["t"], d["c"]) if c}
    _fx_cache[cur] = series or {}
    time.sleep(0.4)
    return _fx_cache[cur]


def to_gbp(s, px):
    """Return (closes_in_gbp, converted_flag). Handles pence and foreign currency."""
    cur = (px["cur"] or "").upper()
    c = px["c"]
    if cur in ("GBP", ""):
        return c, False
    if cur == "GBX" or px["cur"] == "GBp":
        return [x / 100.0 for x in c], False        # pence -> pounds, not a conversion
    fx = fx_to_gbp(s, cur)
    if not fx:
        return None, False
    out, keys = [], sorted(fx)
    j = 0
    for t, v in zip(px["t"], c):
        # nearest FX observation at or before this price date
        while j + 1 < len(keys) and keys[j + 1] <= t:
            j += 1
        rate = fx.get(t) or fx.get(keys[j])
        if rate:
            out.append(v * rate)
    return (out if len(out) > 100 else None), True


def stats(closes, ts, bench=None):
    n = len(closes)
    if n < 200:
        return None
    rets = [(closes[i] / closes[i - 1]) - 1.0 for i in range(1, n) if closes[i - 1]]
    if len(rets) < 200:
        return None

    def sd(xs):
        m = sum(xs) / len(xs)
        return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) if len(xs) > 1 else 0.0

    vol_d = sd(rets) * math.sqrt(252) * 100
    weekly = [closes[i] for i in range(0, n, 5)]
    wrets = [(weekly[i] / weekly[i - 1]) - 1.0 for i in range(1, len(weekly)) if weekly[i - 1]]
    vol_w = sd(wrets) * math.sqrt(52) * 100 if len(wrets) > 40 else None

    peak, mdd = closes[0], 0.0
    for x in closes:
        peak = max(peak, x)
        mdd = min(mdd, x / peak - 1.0)

    years = (ts[-1] - ts[0]) / (365.25 * 24 * 3600)
    cagr = None
    if years > 0.5 and closes[0] > 0 and closes[-1] > 0:
        cagr = ((closes[-1] / closes[0]) ** (1 / years) - 1) * 100

    down = [r for r in rets if r < 0]
    dsd = sd(down) * math.sqrt(252) * 100 if len(down) > 20 else None
    sharpe = round((cagr - RISK_FREE) / vol_d, 2) if (cagr is not None and vol_d) else None
    sortino = round((cagr - RISK_FREE) / dsd, 2) if (cagr is not None and dsd) else None

    # worst rolling 12 months -- the number clients actually feel
    worst12 = None
    if n > 260:
        w = [(closes[i] / closes[i - 252] - 1) * 100 for i in range(252, n) if closes[i - 252]]
        worst12 = round(min(w), 1) if w else None

    def ret_over(days):
        if n > days and closes[-1 - days]:
            return round((closes[-1] / closes[-1 - days] - 1) * 100, 2)
        return None

    out = {"years": round(years, 1), "days": n,
           "volDaily": round(vol_d, 2), "volWeekly": round(vol_w, 2) if vol_w else None,
           "maxDD": round(mdd * 100, 1), "cagr": round(cagr, 2) if cagr else None,
           "sharpe": sharpe, "sortino": sortino, "worst12m": worst12,
           "r1": ret_over(252), "r3": ret_over(756), "r5": ret_over(1260),
           "last": round(closes[-1], 4)}

    if bench:
        bmap = dict(zip(bench["t"], bench["c"]))
        pairs = [(closes[i], bmap[ts[i]]) for i in range(n) if ts[i] in bmap]
        if len(pairs) > 200:
            fr = [(pairs[i][0] / pairs[i - 1][0]) - 1 for i in range(1, len(pairs)) if pairs[i - 1][0]]
            br = [(pairs[i][1] / pairs[i - 1][1]) - 1 for i in range(1, len(pairs)) if pairs[i - 1][1]]
            m = min(len(fr), len(br))
            fr, br = fr[:m], br[:m]
            mf, mb = sum(fr) / m, sum(br) / m
            cov = sum((fr[i] - mf) * (br[i] - mb) for i in range(m)) / (m - 1)
            vb = sum((b - mb) ** 2 for b in br) / (m - 1)
            sf = sd(fr)
            sb = math.sqrt(vb)
            out["beta"] = round(cov / vb, 2) if vb else None
            out["corr"] = round(cov / (sf * sb), 2) if sf and sb else None
    return out


def main():
    s = session()
    cands = json.load(open(CAND, encoding="utf-8"))["candidates"]
    print(f"{len(cands)} candidates", flush=True)

    bpx = chart(s, BENCH)
    bench_gbp = None
    if bpx:
        bc, _ = to_gbp(s, bpx)
        if bc:
            bench_gbp = {"t": bpx["t"][-len(bc):], "c": bc}
    print(f"benchmark {BENCH}: {'ok' if bench_gbp else 'UNAVAILABLE'}", flush=True)

    out, fails, series = [], 0, {}
    for i, c in enumerate(cands, 1):
        px = chart(s, c["symbol"])
        if not px or len(px["c"]) < 260:
            fails += 1
        else:
            closes, converted = to_gbp(s, px)
            if closes:
                st = stats(closes, px["t"][-len(closes):], bench_gbp)
                if st:
                    rec = dict(c)
                    rec.update(st)
                    rec["currency"] = px["cur"]
                    if px.get("longName"):
                        rec["name"] = px["longName"]
                    rec["gbpConverted"] = converted
                    out.append(rec)
                    tt = px["t"][-len(closes):]
                    series[c["symbol"]] = {"t": tt[::5],
                                           "c": [round(x, 6) for x in closes[::5]]}
                else:
                    fails += 1
            else:
                fails += 1
        if i % 50 == 0:
            print(f"  {i}/{len(cands)}  kept {len(out)}  failed {fails}", flush=True)
        time.sleep(0.35)

    json.dump({"builtAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "riskFree": RISK_FREE, "benchmark": BENCH,
               "count": len(out), "funds": out}, open(OUT, "w"), indent=1)
    json.dump({"builtAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "interval": "weekly", "currency": "GBP", "series": series},
              open(SERIES, "w"))
    print(f"\n{len(out)} priced -> {OUT}   ({fails} failed)")
    print(str(len(series)) + " weekly GBP series -> " + SERIES)


if __name__ == "__main__":
    main()
