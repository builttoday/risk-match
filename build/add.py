# -*- coding: utf-8 -*-
"""
Risk Match -- add named share classes to the universe without rebuilding it.

WHY THIS EXISTS. discover.py sweeps fund-house names through Yahoo's search endpoint, which
finds a lot but never everything: a small manager whose name is not in the HOUSES list simply
does not appear. When a specific fund is asked for by name or ISIN, refetching all ~1,000
candidates to pick up one of them costs twenty minutes and rewrites every measurement in the
file for no reason. This prices only what is named and merges it in.

MEASURED THE SAME WAY OR IT IS NOT COMPARABLE. Every statistic here comes from fetch.py's own
chart/to_gbp/stats functions, imported rather than reimplemented, so an added fund's
volatility is the same calculation as the rest of the universe -- including the GBP
conversion and the pence handling. A second implementation that drifted by a rounding rule
would put a fund in the wrong volatility band, which is the one thing this tool must not do.

ISINs ARE THE RELIABLE LOOKUP. Yahoo's search matches an ISIN exactly and matches fund names
badly (nine name variations returning nothing, the ISIN resolving first time). Pass either.

USAGE
    python add.py GB00BNM3D752 GB00BNM3D646        # by ISIN
    python add.py 0P0001NIW1.L                     # by Yahoo symbol

Then re-run the rest of the chain, which is cheap and offline apart from the register lookup:
    python classify.py && python fca.py && python pack.py && python beta.py
"""
import json, os, sys, time

import fetch          # session/chart/to_gbp/stats, so the maths is shared, not copied

HERE = os.path.dirname(os.path.abspath(__file__))
CAND = os.path.join(HERE, "candidates.json")
FUNDS = os.path.join(HERE, "funds_v2.json")
SERIES = os.path.join(HERE, "series_gbp.json")


def resolve(s, q):
    """ISIN or name -> (symbol, quoteType, exchange). A Yahoo symbol is returned unchanged."""
    if q.endswith(".L") or q.startswith("0P") or ("." in q and len(q) < 12):
        return q, "MUTUALFUND", ""
    r = s.get("https://query2.finance.yahoo.com/v1/finance/search", timeout=30,
              params={"q": q, "quotesCount": 10, "newsCount": 0, "listsCount": 0,
                      "enableFuzzyQuery": "false"})
    if r.status_code != 200:
        return None, None, None
    for x in r.json().get("quotes", []):
        if x.get("quoteType") in ("MUTUALFUND", "ETF", "EQUITY"):
            return x.get("symbol"), x.get("quoteType"), x.get("exchange") or ""
    return None, None, None


def main(args):
    if not args:
        print(__doc__)
        return 1

    s = fetch.session()

    # Beta and correlation are only computed when the benchmark series is present, and a fund
    # added without them would show blanks in a column every other fund fills. beta.py would
    # fill them later anyway; doing it here keeps funds_v2.json internally consistent.
    bpx = fetch.chart(s, fetch.BENCH)
    bench_gbp = None
    if bpx:
        bc, _ = fetch.to_gbp(s, bpx)
        if bc:
            bench_gbp = {"t": bpx["t"][-len(bc):], "c": bc}
    print("benchmark %s: %s" % (fetch.BENCH, "ok" if bench_gbp else "UNAVAILABLE"))

    U = json.load(open(FUNDS, encoding="utf-8"))
    S = json.load(open(SERIES, encoding="utf-8"))
    C = json.load(open(CAND, encoding="utf-8"))
    have = {f["symbol"] for f in U["funds"]}
    cand_have = {c["symbol"] for c in C["candidates"]}

    added = []
    for q in args:
        sym, qt, exch = resolve(s, q)
        if not sym:
            print("  %-16s no Yahoo match -- skipped" % q)
            continue
        if sym in have:
            print("  %-16s %s already in the universe -- skipped" % (q, sym))
            continue

        px = fetch.chart(s, sym)
        if not px or len(px["c"]) < 260:
            print("  %-16s %s only %d daily points -- needs about a year, skipped"
                  % (q, sym, len(px["c"]) if px else 0))
            continue
        closes, converted = fetch.to_gbp(s, px)
        if not closes:
            print("  %-16s %s no GBP series -- skipped" % (q, sym))
            continue
        ts = px["t"][-len(closes):]
        st = fetch.stats(closes, ts, bench_gbp)
        if not st:
            print("  %-16s %s too short to measure -- skipped" % (q, sym))
            continue

        rec = {"symbol": sym, "type": qt, "name": px.get("longName") or sym,
               "exch": exch}
        rec.update(st)
        rec["currency"] = px["cur"]
        rec["gbpConverted"] = converted
        U["funds"].append(rec)
        have.add(sym)
        S["series"][sym] = {"t": ts[::5], "c": [round(x, 6) for x in closes[::5]]}
        if sym not in cand_have:
            C["candidates"].append({"symbol": sym, "type": qt, "name": rec["name"],
                                    "exch": exch})
            cand_have.add(sym)
        added.append(rec)
        print("  %-16s %-14s %s" % (q, sym, rec["name"]))
        print("  %-16s %-14s vol %.2f%%  maxDD %.1f%%  %.1f years"
              % ("", "", rec["volDaily"], rec["maxDD"], rec["years"]))
        time.sleep(0.35)

    if not added:
        print("nothing added -- files untouched")
        return 0

    U["count"] = len(U["funds"])
    C["count"] = len(C["candidates"])
    U["builtAt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    for path, data in ((FUNDS, U), (SERIES, S), (CAND, C)):
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=1 if path != SERIES else None)
        os.replace(tmp, path)

    print("\nadded %d; funds_v2.json now holds %d" % (len(added), len(U["funds"])))
    print("now run: python classify.py && python fca.py && python pack.py && python beta.py")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
