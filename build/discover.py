# -*- coding: utf-8 -*-
"""
Risk Match -- expand the fund universe.

The existing funds.json holds 190 sterling share classes. There is no free way to enumerate
the UK fund market (the README already records that the FCA Register API caps at 20 rows with
no working pagination, and its bulk extract is paid). Yahoo's search endpoint does return UK
fund symbols though -- the 0P........L Morningstar-style identifiers -- roughly seven per
query, so a wide sweep of fund-house names and category words builds a much larger universe
from the same public source already in use.

WHY NOT SCRAPE HARGREAVES LANSDOWN: their fund list is rendered client-side, so there is
nothing in the HTML to read, and bulk-harvesting their factsheet data would breach their terms
in a way that matters for a tool advisers may rely on commercially. The manager list below is
simply the set of houses to search for -- public knowledge, not their data.

Output: candidates.json, a deduplicated list of {symbol, name, type} to be priced by fetch.py.
"""
import json, os, time, requests

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "candidates.json")

HOUSES = [
    "abrdn", "Aberdeen", "Aegon", "Allianz", "Artemis", "Ashmore", "AXA", "Baillie Gifford",
    "Barings", "BlackRock", "BNY Mellon", "Brooks Macdonald", "Brown Advisory", "CT",
    "Columbia Threadneedle", "Dimensional", "Evenlode", "Federated Hermes", "Fidelity",
    "First Sentier", "Franklin", "Fundsmith", "GAM", "Goldman Sachs", "Guinness", "Halifax",
    "HSBC", "Impax", "Invesco", "Janus Henderson", "JOHCM", "JPMorgan", "Jupiter",
    "Lazard", "Legal & General", "Lindsell Train", "Liontrust", "M&G", "Man GLG",
    "Marlborough", "Martin Currie", "Mercer", "MFS", "Montanaro", "Morgan Stanley",
    "Ninety One", "Nomura", "Orbis", "Pictet", "PIMCO", "Polar Capital", "Premier Miton",
    "Quilter", "Rathbone", "Robeco", "Royal London", "Ruffer", "Sanlam", "Schroder",
    "Scottish Widows", "Slater", "Stewart Investors", "T. Rowe Price", "TB Amati",
    "Threadneedle", "Troy", "UBS", "Unicorn", "Vanguard", "VT Gravis", "Waverton", "WS",
]

# Global houses. A UK adviser's platform carries far more than UK-domiciled managers, so the
# universe should not stop at British names.
GLOBAL_HOUSES = [
    "iShares", "SPDR", "State Street", "Amundi", "Xtrackers", "DWS", "Capital Group",
    "American Funds", "Wellington", "Nuveen", "Northern Trust", "AllianceBernstein",
    "Dodge & Cox", "Artisan Partners", "Harris Associates", "Oakmark", "Vontobel",
    "Julius Baer", "Lombard Odier", "Candriam", "BNP Paribas", "Natixis", "Carmignac",
    "Comgest", "Flossbach von Storch", "Nordea", "Eurizon", "Mediolanum", "Anima",
    "Azimut", "Santander", "BBVA", "CaixaBank", "Nikko", "Daiwa", "Mitsubishi UFJ",
    "Sumitomo Mitsui", "Manulife", "Sun Life", "RBC Global", "Mackenzie", "Fisher",
    "Neuberger Berman", "Loomis Sayles", "Brandywine", "Western Asset", "Aviva Investors",
    "Legg Mason", "Alliance Bernstein", "Muzinich", "Payden", "Principal", "Invesco Global",
    "First Trust", "VanEck", "WisdomTree", "Global X", "L&G ETF", "HANetf",
]
HOUSES = HOUSES + GLOBAL_HOUSES

CATEGORIES = [
    "UK Equity Income", "UK All Companies", "UK Smaller Companies", "Global Equity",
    "Global Bond", "Corporate Bond", "Strategic Bond", "Gilt", "Index Linked",
    "Multi Asset", "Mixed Investment", "Cautious Managed", "Emerging Markets",
    "Asia Pacific", "Japan", "North America", "European", "Technology", "Healthcare",
    "Infrastructure", "Property", "Absolute Return", "Sustainable", "Index Tracker",
    "Money Market", "High Yield", "Global Smaller Companies", "Balanced Managed",
]

# FTSE 100 constituents, seeded directly -- we already know the tickers, so there is no point
# spending search quota guessing at them. Individual equities are a different animal from funds
# and are tagged as such so the app can keep them separate: a single share's volatility is not
# comparable to a diversified fund's for suitability purposes.
FTSE100 = """AAL ABF ADM AHT ANTO AUTO AV BA BARC BATS BDEV BEZ BKG BME BNZL BP BT-A BTRW
CCH CNA CPG CRDA CTEC DCC DGE DPLM EDV ENT EXPN FCIT FRAS FRES GLEN GSK HIK HLMA HLN HSBA
HSX HWDN IAG ICG IHG III IMB IMI INF ITRK JD KGF LAND LGEN LLOY LMP LSEG MKS MNDI MNG MRO
NG NWG NXT PHNX PRU PSH PSN PSON REL RIO RKT RMV RR RTO SBRY SDR SGE SGRO SHEL SMDS SMIN
SMT SN SPX SSE STAN STJ SVT TSCO TW ULVR UTG UU VOD WEIR WPP WTB""".split()

BENCHMARKS = ["^FTSE", "^FTAS", "^GSPC", "^NDX", "^STOXX50E", "IWDG.L", "VWRP.L", "VUKE.L"]

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def session():
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept": "application/json"})
    try:
        s.get("https://finance.yahoo.com/", timeout=20)   # pick up cookies
    except Exception:
        pass
    return s


def search(s, q):
    try:
        r = s.get("https://query2.finance.yahoo.com/v1/finance/search", timeout=30,
                  params={"q": q, "quotesCount": 50, "newsCount": 0, "listsCount": 0,
                          "enableFuzzyQuery": "false"})
        if r.status_code != 200:
            return [], r.status_code
        return r.json().get("quotes", []), 200
    except Exception:
        return [], -1


def main():
    s = session()
    found, seen = {}, set()
    for t in FTSE100:
        sym = t + ".L"
        seen.add(sym)
        found[sym] = {"symbol": sym, "type": "EQUITY", "name": sym, "exch": "LSE",
                      "index": "FTSE100"}
    for b in BENCHMARKS:
        seen.add(b)
        found[b] = {"symbol": b, "type": "INDEX", "name": b, "exch": "", "index": "BENCHMARK"}
    print(f"seeded {len(found)} (FTSE 100 + benchmarks)", flush=True)
    queries = ([h for h in HOUSES]
               + [f"{h} fund" for h in HOUSES]
               + CATEGORIES
               + [f"{c} fund" for c in CATEGORIES])
    print(f"{len(queries)} queries", flush=True)
    bad = 0
    for i, q in enumerate(queries, 1):
        quotes, code = search(s, q)
        if code != 200:
            bad += 1
            if bad % 10 == 0:
                print(f"  ...{bad} failed queries (last code {code})", flush=True)
        for x in quotes:
            sym = x.get("symbol", "")
            qt = x.get("quoteType", "")
            if not sym or sym in seen:
                continue
            # London first, but global managers list share classes on other venues too.
            # Currency differences are handled later: fetch.py converts every price series to
            # GBP before measuring volatility, because an unhedged USD fund's sterling
            # volatility is what a UK investor actually experiences.
            OK = (".L", ".IL", ".AS", ".DE", ".PA", ".MI", ".SW", ".F", ".VI", ".BR", ".MC")
            if not (sym.endswith(OK) or ("." not in sym and qt in ("MUTUALFUND", "ETF"))):
                continue
            if qt not in ("MUTUALFUND", "ETF", "EQUITY"):
                continue
            seen.add(sym)
            found[sym] = {"symbol": sym, "type": qt,
                          "name": x.get("shortname") or x.get("longname") or sym,
                          "exch": x.get("exchange", "")}
        if i % 25 == 0:
            print(f"  {i}/{len(queries)} queries, {len(found)} candidates", flush=True)
        time.sleep(0.7)
    json.dump({"builtAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "count": len(found), "candidates": sorted(found.values(),
                                                         key=lambda z: z["symbol"])},
              open(OUT, "w"), indent=1)
    kinds = {}
    for v in found.values():
        kinds[v["type"]] = kinds.get(v["type"], 0) + 1
    print(f"\n{len(found)} candidates -> {OUT}")
    print("by type:", kinds)
    print("failed queries:", bad)


if __name__ == "__main__":
    main()
