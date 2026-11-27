#!/usr/bin/env python3
"""Extract the price-history chart series that PriceCharting embeds in item
pages and write one tidy CSV covering several card versions.

    pip install requests
    python scrape_chart.py --dump     # print series keys per card, for debugging
    python scrape_chart.py            # -> src/data/prices.csv
"""
import argparse
import csv
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

import requests

CARDS = {
    "Japanese Charizard": "https://www.pricecharting.com/game/pokemon-japanese-expansion-pack/charizard-6",
    "English Charizard Unlimited": "https://www.pricecharting.com/game/pokemon-base-set/charizard-4",
    "English Charizard 1st Edition": "https://www.pricecharting.com/game/pokemon-base-set/charizard-1st-edition-4",
    "English Charizard Shadowless": "https://www.pricecharting.com/game/pokemon-base-set/charizard-shadowless-4",
    "Japanese Blastoise": "https://www.pricecharting.com/game/pokemon-japanese-expansion-pack/blastoise-9",
    "English Blastoise 1st Edition": "https://www.pricecharting.com/game/pokemon-base-set/blastoise-1st-edition-2",
    "English Blastoise Shadowless": "https://www.pricecharting.com/game/pokemon-base-set/blastoise-shadowless-2",
    "English Blastoise Unlimited": "https://www.pricecharting.com/game/pokemon-base-set/blastoise-2",
    "Japanese Venusaur": "https://www.pricecharting.com/game/pokemon-japanese-expansion-pack/venusaur-3",
    "English Venusaur 1st Edition": "https://www.pricecharting.com/game/pokemon-base-set/venusaur-1st-edition-15",
    "English Venusaur Shadowless": "https://www.pricecharting.com/game/pokemon-base-set/venusaur-shadowless-15",
    "English Venusaur Unlimited": "https://www.pricecharting.com/game/pokemon-base-set/venusaur-15"
}

# Chart series key -> grade label.
SERIES = {
    "used": "Ungraded",
    "cib": "Grade 7",
    "new": "Grade 8",
    "graded": "Grade 9",
    "manualonly": "PSA 10",
}

FIELDS = ["date", "version", "series", "grade", "price"]


def extract_chart_data(html):
    m = re.search(r"chart_data\s*=\s*", html)
    if not m:
        raise ValueError("chart_data not found in page source")
    start = html.index("{", m.end())
    obj, _ = json.JSONDecoder().raw_decode(html[start:])
    return obj


def fetch_chart(url):
    resp = requests.get(url, timeout=30, headers={
        "User-Agent": "Mozilla/5.0 (personal price-history project)"})
    resp.raise_for_status()
    return extract_chart_data(resp.text)


def to_rows(version, data, divisor):
    rows = []
    for key, label in SERIES.items():
        for ts, value in data.get(key, []):
            if not value:  # 0 / null = no sales that month
                continue
            day = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).date().isoformat()
            rows.append({"date": day, "version": version, "series": key,
                         "grade": label, "price": round(value / divisor, 2)})
    return rows


def load_existing(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if "version" in r]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="src/data/prices.csv")
    ap.add_argument("--divisor", type=float, default=100.0,
                    help="values are assumed to be cents; use 1 if dollars")
    ap.add_argument("--dump", action="store_true")
    args = ap.parse_args()

    existing = load_existing(args.out)
    fresh, failed = [], []

    for i, (version, url) in enumerate(CARDS.items()):
        if i:
            time.sleep(2)  # be polite between requests
        try:
            data = fetch_chart(url)
        except (requests.RequestException, ValueError, json.JSONDecodeError) as e:
            print(f"warning: {version}: {e}", file=sys.stderr)
            failed.append(version)
            continue
        if args.dump:
            print(f"== {version}")
            for k, v in data.items():
                print(" ", k, len(v), v[:2])
            continue
        rows = to_rows(version, data, args.divisor)
        if not rows:
            print(f"warning: {version}: no data points parsed", file=sys.stderr)
            failed.append(version)
            continue
        fresh += rows
        print(f"{version}: {len(rows)} points")

    if args.dump:
        return

    # A failed card keeps its previously saved rows instead of vanishing.
    kept = [r for r in existing if r["version"] in failed]
    rows = fresh + kept
    if not fresh:
        sys.exit("error: nothing scraped from any card")

    rows.sort(key=lambda r: (r["version"], r["grade"], r["date"]))
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} rows -> {args.out}")


if __name__ == "__main__":
    main()
