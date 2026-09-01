# -*- coding: utf-8 -*-
"""
Risk Match -- derive fund manager and sector for every fund, and normalise names for matching.

THESE FIELDS ARE DERIVED FROM THE FUND NAME, NOT LOOKED UP. There is no free feed of UK fund
sector classifications, so a fund called "Royal London Sustainable Leaders C Acc" is assigned
house "Royal London" and sector "Global Equity" by reading the name. That is good enough to
browse and filter by, and it is wrong often enough that it must never be presented as the IA
sector or the manager of record. Every derived value is flagged `derived: true` so the UI can
say so.

Name normalisation exists for a different reason: FCA matching. Share-class noise is why 93 of
190 funds failed to match the register -- "Royal London GMAP Adventurous R GBP Acc" will never
equal "Royal London GMAP Adventurous Fund". Stripping the class letters, currency and
accumulation/income markers leaves a stem that matches far more often.
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
IN = os.path.join(HERE, "funds_v2.json")
OUT = os.path.join(HERE, "funds_v3.json")

HOUSES = [
    "Baillie Gifford", "Columbia Threadneedle", "Legal & General", "Janus Henderson",
    "First Sentier", "Stewart Investors", "Franklin Templeton", "BNY Mellon", "Royal London",
    "Scottish Widows", "Brooks Macdonald", "Brown Advisory", "Federated Hermes",
    "Polar Capital", "Premier Miton", "Lindsell Train", "Martin Currie", "Ninety One",
    "T. Rowe Price", "Morgan Stanley", "Goldman Sachs", "Neuberger Berman", "Loomis Sayles",
    "Flossbach von Storch", "Dodge & Cox", "Artisan Partners", "Aviva Investors",
    "Capital Group", "American Funds", "Northern Trust", "AllianceBernstein", "Western Asset",
    "Mitsubishi UFJ", "Sumitomo Mitsui", "Julius Baer", "Lombard Odier", "BNP Paribas",
    "State Street", "Man GLG", "TB Amati", "VT Gravis", "Alliance Bernstein", "WisdomTree",
    "First Trust", "Global X", "Fundsmith", "Threadneedle", "Marlborough", "Montanaro",
    "Rathbone", "Liontrust", "Schroder", "Invesco", "Fidelity", "Jupiter", "Artemis",
    "Vanguard", "iShares", "Amundi", "Xtrackers", "BlackRock", "JPMorgan", "Barings",
    "Allianz", "Ashmore", "abrdn", "Aberdeen", "Aegon", "Dimensional", "Evenlode",
    "Guinness", "Impax", "JOHCM", "Lazard", "Mercer", "Nomura", "Orbis", "Pictet", "PIMCO",
    "Quilter", "Robeco", "Ruffer", "Sanlam", "Slater", "Unicorn", "Waverton", "Vontobel",
    "Candriam", "Natixis", "Carmignac", "Comgest", "Nordea", "Eurizon", "Mediolanum",
    "Azimut", "Santander", "Nikko", "Daiwa", "Manulife", "Mackenzie", "Muzinich", "VanEck",
    "HSBC", "AXA", "GAM", "M&G", "MFS", "UBS", "DWS", "SPDR", "Anima", "L&G", "CT", "WS",
]

SECTORS = [
    ("Money Market",          ("money market", "liquidity", "cash fund", "treasury reserve")),
    ("Index-Linked Gilts",    ("index linked", "index-linked", "inflation link")),
    ("Gilts",                 ("gilt", "government bond", "treasury bond")),
    ("High Yield Bond",       ("high yield", "high income bond")),
    ("Corporate Bond",        ("corporate bond", "investment grade", "credit fund", " credit ")),
    ("Strategic / Global Bond", ("bond", "fixed income", "fixed interest", "aggregate")),
    ("UK Equity Income",      ("uk equity income", "uk income")),
    ("UK Smaller Companies",  ("uk smaller", "uk micro")),
    ("UK Equity",             ("uk equity", "uk all companies", "uk growth", "ftse 100",
                               "ftse all", "uk index", "uk select", "british")),
    ("Global Smaller Companies", ("global smaller", "world smaller")),
    ("Emerging Markets",      ("emerging", "frontier", "china", "india", "brazil", "latin")),
    ("Asia Pacific",          ("asia", "pacific", "asean", "korea", "singapore")),
    ("Japan",                 ("japan", "nippon")),
    ("North America",         ("north america", "us equity", "usa", "s&p 500", "american",
                               "nasdaq")),
    ("Europe",                ("europe", "euro stoxx", "eurozone", "german", "french")),
    ("Technology",            ("technolog", "digital", "software", "semiconductor", "ai ")),
    ("Healthcare",            ("health", "biotech", "pharma", "medical")),
    ("Energy & Resources",    ("energy", "natural resources", "mining", "gold", "commodit",
                               "oil", "silver", "platinum", "palladium", "metals",
                               "precious")),
    ("Infrastructure",        ("infrastructure", "renewable")),
    ("Property",              ("property", "real estate", "reit")),
    ("Absolute Return",       ("absolute return", "targeted return", "market neutral",
                               "long/short")),
    ("Multi-Asset",          ("multi asset", "multi-asset", "mixed investment", "managed",
                              "balanced", "cautious", "adventurous", "moderate", "defensive",
                              "portfolio fund", "lifestrategy", "gmap", "allocation")),
    ("Global Equity",        ("global", "world", "international", "equity", "growth", "income")),
]

CLASS_NOISE = re.compile(
    r"\b("
    r"acc(umulation)?|inc(ome)?|dist(ribution)?|hedged|unhedged|gbp|usd|eur|chf|jpy|"
    r"class\s*[a-z0-9]{1,3}|"
    r"[a-z]\s?\d{0,2}\s?(acc|inc)|"
    r"institutional|retail|clean|net|gross|shares?|units?|share\s*class|"
    r"ltd|plc|fund|oeic|sicav|icvc|ucits|etf"
    r")\b", re.I)


# NAMES ARE USED VERBATIM. An earlier version expanded abbreviations ("Acc" ->
# "Accumulation") to read like a platform's house style. That was wrong: the requirement is
# accuracy to the fund factsheet, and rewriting a share-class name makes it LESS accurate, not
# more. Yahoo's longName is Morningstar-sourced and is the closest free match to the official
# share-class name, so it is passed through untouched.
#
# If names must be guaranteed to match the factsheet exactly -- for a client file or a
# suitability report -- that needs a licensed feed (FE fundinfo, Morningstar Direct). No free
# source can promise it, and this one does not.
def display_name(name):
    return name


def house_of(name):
    low = name.lower()
    for h in sorted(HOUSES, key=len, reverse=True):
        if low.startswith(h.lower()) or f" {h.lower()} " in f" {low} ":
            return h
    return name.split()[0] if name.split() else "Unknown"


# Short keywords must match whole words. Plain substring matching put "abrdn Physical
# PLATINUM Shares ETF" into Emerging Markets, because "platinum" contains "latin".
_SECT_RE = None


def _sector_patterns():
    global _SECT_RE
    if _SECT_RE is None:
        _SECT_RE = []
        for sec, keys in SECTORS:
            pats = []
            for k in keys:
                k = k.strip()
                pats.append(re.compile("\\b" + re.escape(k) + "\\b", re.I))
            _SECT_RE.append((sec, pats))
    return _SECT_RE


def sector_of(name):
    for sec, pats in _sector_patterns():
        if any(p.search(name) for p in pats):
            return sec
    return "Unclassified"


def stem(name):
    s = CLASS_NOISE.sub(" ", name)
    s = re.sub(r"[^A-Za-z0-9& ]+", " ", s)
    s = re.sub(r"\b[A-Z]\b", " ", s)          # stray single-letter class markers
    return re.sub(r"\s+", " ", s).strip()


def main():
    d = json.load(open(IN, encoding="utf-8"))
    funds = d["funds"]
    houses, sectors = {}, {}
    for f in funds:
        nm = f.get("name") or f["symbol"]
        if f.get("type") == "EQUITY":
            f["house"] = "— single company share"
            f["sector"] = "UK Equity (single share)" if f.get("index") == "FTSE100" else "Single share"
        elif f.get("type") == "INDEX":
            f["house"] = "— index"
            f["sector"] = "Benchmark index"
        else:
            f["house"] = house_of(nm)
            f["sector"] = sector_of(nm)
        f["displayName"] = display_name(nm)
        f["stem"] = stem(nm)
        f["derived"] = True
        houses[f["house"]] = houses.get(f["house"], 0) + 1
        sectors[f["sector"]] = sectors.get(f["sector"], 0) + 1

    d["funds"] = funds
    d["houses"] = sorted(houses.items(), key=lambda x: (-x[1], x[0]))
    d["sectors"] = sorted(sectors.items(), key=lambda x: (-x[1], x[0]))
    json.dump(d, open(OUT, "w"), indent=1)

    print(f"{len(funds)} funds classified -> {OUT}\n")
    print(f"{len(houses)} managers. Top 15:")
    for h, c in d["houses"][:15]:
        print(f"   {c:>4}  {h}")
    print(f"\n{len(sectors)} sectors:")
    for s, c in d["sectors"]:
        print(f"   {c:>4}  {s}")


if __name__ == "__main__":
    main()
