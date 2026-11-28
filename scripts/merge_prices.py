#!/usr/bin/env python3
"""Merge the per-set CSVs into one file for the notebook.

    python merge_prices.py            # src/data/*_prices.csv -> src/data/all_prices.csv
"""
import csv
import glob
import os
import sys

FIELDS = ["date", "version", "grade", "set", "card", "edition", "price"]
OUT = "src/data/all_prices.csv"

paths = [p for p in sorted(glob.glob("src/data/*_prices.csv")) if os.path.basename(p) != os.path.basename(OUT)]
if not paths:
    sys.exit("error: no src/data/*_prices.csv files found")

rows = []
for p in paths:
    with open(p, newline="", encoding="utf-8") as f:
        part = list(csv.DictReader(f))
    print(f"{p}: {len(part)} rows")
    rows += part

# Same card, edition and month should appear once, even if a card is listed in two files.
seen, merged = set(), []
for r in rows:
    key = (r["set"], r["version"], r["grade"], r["date"])
    if key not in seen:
        seen.add(key)
        merged.append(r)

merged.sort(key=lambda r: (r["set"], r["card"], r["edition"], r["grade"], r["date"]))
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
    w.writeheader()
    w.writerows(merged)
print(f"{len(merged)} rows -> {OUT}")
