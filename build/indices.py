# -*- coding: utf-8 -*-
"""Add index constituents -- the S&P 500 and the FTSE 100 -- as individual companies.

WHY A SEPARATE STEP. discover.py finds funds by searching for fund-house names. Index
constituents are a known list, not something to search for, and they need an industry
against each name that no amount of name-parsing will produce: "Diageo plc" does not say
Consumer Staples anywhere in it. So the list and the industry come from outside.

The S&P 500 list carries its own GICS sector. The FTSE 100 does not have an equivalent free
machine-readable list, so its industries are written out below by hand and dated -- an index
changes a few times a year, and a hand-written map that does not say when it was written is
a trap for whoever reads it next.

Every price is fetched and converted to sterling by the same code as everything else, so a
US share is measured after the dollar move, which is the return a UK investor actually got.
"""
import csv, io, json, os, sys, time
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fetch import chart, to_gbp, stats, session, BENCH   # noqa: E402

SP500_CSV = ("https://raw.githubusercontent.com/datasets/s-and-p-500-companies/"
             "main/data/constituents.csv")
OUT = os.path.join(HERE, "funds_v2.json")
SER = os.path.join(HERE, "series_gbp.json")

# FTSE 100 industries, written out 2026-09-02 against the constituents the tool holds.
# ICB industry level, which is the level someone browsing actually wants.
FTSE_INDUSTRY = {
    "AAL.L": "Basic Materials", "ABF.L": "Consumer Staples", "ADM.L": "Financials",
    "ANTO.L": "Basic Materials", "AUTO.L": "Technology", "AV.L": "Financials",
    "BA.L": "Industrials", "BARC.L": "Financials", "BATS.L": "Consumer Staples",
    "BEZ.L": "Financials", "BKG.L": "Consumer Discretionary", "BME.L": "Consumer Discretionary",
    "BNZL.L": "Industrials", "BP.L": "Energy", "BT-A.L": "Telecommunications",
    "BTRW.L": "Consumer Discretionary", "CCH.L": "Consumer Staples", "CNA.L": "Utilities",
    "CPG.L": "Consumer Discretionary", "CRDA.L": "Basic Materials", "CTEC.L": "Health Care",
    "DCC.L": "Energy", "DGE.L": "Consumer Staples", "DPLM.L": "Industrials",
    "EDV.L": "Basic Materials", "ENT.L": "Consumer Discretionary", "EXPN.L": "Industrials",
    "FCIT.L": "Financials", "FRAS.L": "Consumer Discretionary", "FRES.L": "Basic Materials",
    "GLEN.L": "Basic Materials", "GSK.L": "Health Care", "HIK.L": "Health Care",
    "HLMA.L": "Technology", "HLN.L": "Consumer Staples", "HSBA.L": "Financials",
    "HSX.L": "Financials", "HWDN.L": "Consumer Discretionary", "IAG.L": "Consumer Discretionary",
    "ICG.L": "Financials", "IHG.L": "Consumer Discretionary", "III.L": "Financials",
    "IMB.L": "Consumer Staples", "IMI.L": "Industrials", "INF.L": "Consumer Discretionary",
    "ITRK.L": "Industrials", "JD.L": "Consumer Discretionary", "KGF.L": "Consumer Discretionary",
    "LAND.L": "Real Estate", "LGEN.L": "Financials", "LLOY.L": "Financials",
    "LMP.L": "Real Estate", "LSEG.L": "Financials", "MKS.L": "Consumer Staples",
    "MNDI.L": "Basic Materials", "MNG.L": "Financials", "MRO.L": "Industrials",
    "NG.L": "Utilities", "NWG.L": "Financials", "NXT.L": "Consumer Discretionary",
    "PRU.L": "Financials", "PSH.L": "Financials", "PSN.L": "Consumer Discretionary",
    "PSON.L": "Consumer Discretionary", "REL.L": "Industrials", "RIO.L": "Basic Materials",
    "RKT.L": "Consumer Staples", "RMV.L": "Technology", "RR.L": "Industrials",
    "RTO.L": "Industrials", "SBRY.L": "Consumer Staples", "SDR.L": "Financials",
    "SGE.L": "Technology", "SGRO.L": "Real Estate", "SHEL.L": "Energy",
    "SMIN.L": "Industrials", "SMT.L": "Financials", "SN.L": "Health Care",
    "SPX.L": "Industrials", "SSE.L": "Utilities", "STAN.L": "Financials",
    "STJ.L": "Financials", "SVT.L": "Utilities", "TSCO.L": "Consumer Staples",
    "TW.L": "Consumer Discretionary", "ULVR.L": "Consumer Staples", "UTG.L": "Real Estate",
    "UU.L": "Utilities", "VOD.L": "Telecommunications", "WEIR.L": "Industrials",
    "WPP.L": "Consumer Discretionary", "WTB.L": "Consumer Discretionary",
}
FTSE_INDUSTRY_AS_AT = "2026-09-02"

WANT_SP500_CONSTITUENTS = False

# GICS names are close enough to ICB to sit in one column, but not identical. Mapped so a
# sector breakdown across both indices counts like with like rather than showing
# "Information Technology" and "Technology" as two different things.
GICS_TO_ICB = {
    "Information Technology": "Technology",
    "Communication Services": "Telecommunications",
    "Consumer Discretionary": "Consumer Discretionary",
    "Consumer Staples": "Consumer Staples",
    "Health Care": "Health Care",
    "Financials": "Financials",
    "Industrials": "Industrials",
    "Energy": "Energy",
    "Utilities": "Utilities",
    "Real Estate": "Real Estate",
    "Materials": "Basic Materials",
}


def sp500():
    r = requests.get(SP500_CSV, timeout=30)
    r.raise_for_status()
    out = []
    for row in csv.DictReader(io.StringIO(r.text)):
        sym = (row["Symbol"] or "").strip()
        if not sym:
            continue
        # Yahoo writes class shares with a hyphen where the index uses a full stop.
        out.append({
            "symbol": sym.replace(".", "-"),
            "name": (row["Security"] or "").strip(),
            "index": "SP500",
            "industry": GICS_TO_ICB.get((row["GICS Sector"] or "").strip(),
                                        (row["GICS Sector"] or "").strip() or None),
            "subIndustry": (row["GICS Sub-Industry"] or "").strip() or None,
        })
    return out


def main():
    U = json.load(open(OUT, encoding="utf-8"))
    S = json.load(open(SER, encoding="utf-8"))
    have = {f["symbol"]: f for f in U["funds"]}

    # Backfill the industry onto the FTSE 100 shares already held.
    tagged = 0
    for sym, ind in FTSE_INDUSTRY.items():
        if sym in have:
            have[sym]["industry"] = ind
            have[sym]["industryAsAt"] = FTSE_INDUSTRY_AS_AT
            tagged += 1
    print("FTSE 100: industry set on %d of %d listed" % (tagged, len(FTSE_INDUSTRY)))

    # THE S&P 500 CONSTITUENTS WERE REMOVED DELIBERATELY. They were fetched once and taken
    # back out: individual US shares belong in the Filing Diff tool, and what this tool needs
    # is the index as something you can buy -- the tracker share classes, which the fund
    # universe already holds and which classify.py files under an "S&P 500" sector. Set
    # WANT_SP500_CONSTITUENTS to re-enable, but ask first whether 500 single companies help
    # anyone choosing a fund.
    if not WANT_SP500_CONSTITUENTS:
        print("S&P 500 constituents: skipped by design (see the note in this file)")
        cands, todo = [], []
    else:
        cands = sp500()
        print("S&P 500 list: %d constituents" % len(cands))
        todo = [c for c in cands if c["symbol"] not in have]
        print("%d already held, fetching %d" % (len(cands) - len(todo), len(todo)))

    s = session()
    bpx = chart(s, BENCH)
    bench = None
    if bpx:
        bc, _ = to_gbp(s, bpx)
        if bc:
            bench = {"t": bpx["t"][-len(bc):], "c": bc}

    added = failed = 0
    for i, c in enumerate(todo, 1):
        px = chart(s, c["symbol"])
        time.sleep(0.3)
        if not px or len(px["c"]) < 260:
            failed += 1
            continue
        closes, converted = to_gbp(s, px)
        if not closes:
            failed += 1
            continue
        st = stats(closes, px["t"][-len(closes):], bench)
        if not st:
            failed += 1
            continue
        rec = dict(c)
        rec.update(st)
        rec["type"] = "EQUITY"
        rec["currency"] = px["cur"]
        rec["gbpConverted"] = converted
        if px.get("longName"):
            rec["name"] = px["longName"]
        U["funds"].append(rec)
        tt = px["t"][-len(closes):]
        S["series"][c["symbol"]] = {"t": tt[::5], "c": [round(x, 6) for x in closes[::5]]}
        added += 1
        if i % 50 == 0:
            print("  %d/%d  added %d  failed %d" % (i, len(todo), added, failed), flush=True)

    for path, data in ((OUT, U), (SER, S)):
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=1 if path == OUT else None)
        os.replace(tmp, path)

    print("\nadded %d S&P 500 shares, %d failed; universe now %d"
          % (added, failed, len(U["funds"])))


if __name__ == "__main__":
    main()
