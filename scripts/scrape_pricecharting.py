#!/usr/bin/env python3
"""Extract the price-history chart series that PriceCharting embeds in an item
page (the data behind the "Show Historic Prices" chart) and write a tidy CSV.

    pip install requests
    python scrape_chart.py                  # -> chart.csv
    python scrape_chart.py --dump           # print the series keys found, for debugging
"""
import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone

import requests

URL = "https://www.pricecharting.com/game/pokemon-japanese-expansion-pack/charizard-6"

# Chart series key -> grade label (same order as the price table on the page).
SERIES = {
    "used": "Ungraded",
    "cib": "Grade 7",
    "new": "Grade 8",
    "graded": "Grade 9",
    "boxonly": "Grade 9.5",
    "manualonly": "PSA 10",
}


def extract_chart_data(html):
    """Find `chart_data = {...}` in the page's inline JS and parse the object."""
    m = re.search(r"chart_data\s*=\s*", html)
    if not m:
        raise ValueError("chart_data not found in page source")
    start = html.index("{", m.end())
    obj, _ = json.JSONDecoder().raw_decode(html[start:])
    return obj


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=URL)
    ap.add_argument("--out", default="chart.csv")
    ap.add_argument("--divisor", type=float, default=100.0,
                    help="values are assumed to be cents; use 1 if they are dollars")
    ap.add_argument("--dump", action="store_true")
    args = ap.parse_args()

    resp = requests.get(args.url, timeout=30, headers={
        "User-Agent": "Mozilla/5.0 (personal price-history project)"})
    resp.raise_for_status()

    try:
        data = extract_chart_data(resp.text)
    except (ValueError, json.JSONDecodeError) as e:
        sys.exit(f"error: {e}")

    if args.dump:
        for k, v in data.items():
            print(k, len(v), v[:2])
        return

    rows = []
    for key, label in SERIES.items():
        for ts, value in data.get(key, []):
            if not value:  # 0 / null = no sales that month
                continue
            day = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).date().isoformat()
            rows.append({"date": day, "series": key, "grade": label,
                         "price": round(value / args.divisor, 2)})

    if not rows:
        sys.exit("error: no data points parsed (series keys changed? try --dump)")

    rows.sort(key=lambda r: (r["grade"], r["date"]))
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["date", "series", "grade", "price"])
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} points -> {args.out}")


if __name__ == "__main__":
    main()
