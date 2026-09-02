# -*- coding: utf-8 -*-
"""Match funds to the FCA Financial Services Register, and cache what was matched.

WHY A CACHE FILE RATHER THAN A FIELD ON THE FUND
The register lookup needs credentials and is slow, and the fund universe gets rebuilt far
more often than the register changes. Keeping the matches in build/fca_cache.json keyed by
symbol means a rebuild carries the existing matches forward instead of silently dropping
them -- which is exactly what happened when the universe went from 190 funds to 982: the
whole FCA column disappeared and the match view lost a column of evidence without anything
failing loudly.

RUNNING THE LOOKUP needs a register API key (they are free):
    https://register.fca.org.uk/Developer/s/  ->  set FCA_EMAIL and FCA_KEY
Without them this script still runs; it just reports what the cache already holds and
matches nothing new. The front end shows a dash for an unmatched fund, and a dash means
"no confident name match was found", not "not authorised".

ON SCORING. A match is scored on normalised-name similarity and anything below 0.75 is
shown with a "?" rather than dressed up as confirmed. Presenting a 0.6 match with the same
confidence as a 1.0 one is how a wrong PRN ends up in a client's suitability file.
"""
import json, os, re, sys, time, difflib

HERE = os.path.dirname(os.path.abspath(__file__))
FUNDS = os.path.join(HERE, "funds_v3.json")
CACHE = os.path.join(HERE, "fca_cache.json")
API = "https://register.fca.org.uk/services/V0.1/CommonSearch"

# Share-class and wrapper noise: none of it appears in the register's fund name, and leaving
# it in drags every similarity score down.
NOISE = re.compile(
    r"\b(acc|inc|accumulation|income|dist|distributing|hedged|unhedged|gbp|usd|eur|chf|jpy|"
    r"class|cls|shares?|units?|ucits|etf|oeic|icvc|sicav|plc|ltd|limited|fund|funds|"
    r"[a-z]?\d*(acc|inc)|[a-z]\b)\b", re.I)


def norm(name):
    s = re.sub(r"[^a-z0-9 ]+", " ", (name or "").lower())
    s = NOISE.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def score(a, b):
    return round(difflib.SequenceMatcher(None, norm(a), norm(b)).ratio(), 2)


def lookup(sess, name):
    r = sess.get(API, params={"q": name, "type": "firm"}, timeout=25)
    if r.status_code != 200:
        return None
    for row in (r.json().get("Data") or [])[:20]:
        got = row.get("Name") or ""
        sc = score(name, got)
        if sc >= 0.55:
            prn = str(row.get("Reference Number") or "")
            if prn:
                return {"fcaPrn": prn, "fcaName": got, "fcaScore": sc,
                        "fcaStatus": row.get("Status") or "listed",
                        "fcaUrl": f"https://register.fca.org.uk/s/search?q={prn}&type=Companies"}
    return None


def main():
    funds = json.load(open(FUNDS, encoding="utf-8"))["funds"]
    cache = {}
    if os.path.exists(CACHE):
        cache = json.load(open(CACHE, encoding="utf-8")).get("matches", {})

    hit = sum(1 for f in funds if f["symbol"] in cache)
    print(f"{len(funds)} funds, {len(cache)} cached matches, {hit} of them still in the universe")

    email, key = os.environ.get("FCA_EMAIL"), os.environ.get("FCA_KEY")
    if not (email and key):
        print("FCA_EMAIL / FCA_KEY not set -- carrying the cache forward, matching nothing new.")
        print("Get a free key at https://register.fca.org.uk/Developer/s/ to fill the rest.")
        return

    import requests
    sess = requests.Session()
    sess.headers.update({"X-Auth-Email": email, "X-Auth-Key": key, "Accept": "application/json"})

    todo = [f for f in funds if f["symbol"] not in cache and f.get("type") != "EQUITY"]
    print(f"looking up {len(todo)}")
    found = 0
    for i, f in enumerate(todo, 1):
        try:
            m = lookup(sess, f.get("name") or f["symbol"])
        except Exception as e:
            print(f"  {f['symbol']}: {e}")
            m = None
        if m:
            cache[f["symbol"]] = m
            found += 1
        if i % 50 == 0:
            print(f"  {i}/{len(todo)}  matched {found}", flush=True)
        time.sleep(0.25)

    tmp = CACHE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump({"checkedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "matches": cache}, fh, indent=1)
    os.replace(tmp, CACHE)
    print(f"matched {found} new; cache now holds {len(cache)}")


if __name__ == "__main__":
    main()
