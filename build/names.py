# -*- coding: utf-8 -*-
"""Backfill full fund names from Yahoo chart meta `longName`.

Search's `shortname` is truncated at 30 characters and is missing entirely for many symbols,
which left 413 of 964 funds named only by their ticker and 505 unclassifiable. A one-month
chart request is enough to read the metadata, so this repairs the names without re-pricing
five years of history for every fund.
"""
import json, os, time, requests

HERE = os.path.dirname(os.path.abspath(__file__))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
s = requests.Session(); s.headers.update({"User-Agent": UA})
try: s.get("https://finance.yahoo.com/", timeout=20)
except Exception: pass

d = json.load(open(os.path.join(HERE, "funds_v2.json"), encoding="utf-8"))
funds = d["funds"]
fixed = miss = 0
for i, f in enumerate(funds, 1):
    try:
        r = s.get(f"https://query2.finance.yahoo.com/v8/finance/chart/{f['symbol']}",
                  timeout=25, params={"range": "1mo", "interval": "1d"})
        if r.status_code == 200:
            m = (r.json()["chart"]["result"][0].get("meta") or {})
            ln = m.get("longName") or ""
            if ln and len(ln) > len(f.get("name", "")):
                f["name"] = ln; fixed += 1
            else:
                miss += 1
        else:
            miss += 1
    except Exception:
        miss += 1
    if i % 100 == 0:
        print(f"  {i}/{len(funds)}  fixed {fixed}  unchanged {miss}", flush=True)
    time.sleep(0.3)
json.dump(d, open(os.path.join(HERE, "funds_v2.json"), "w"), indent=1)
print(f"\n{fixed} names repaired, {miss} unchanged")
