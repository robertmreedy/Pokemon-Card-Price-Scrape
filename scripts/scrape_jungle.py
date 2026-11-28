#!/usr/bin/env python3
"""Extract the price-history chart series that PriceCharting embeds in item
pages and write one tidy CSV covering several card versions.

    pip install requests
    python scrape_chart.py --dump     # print series keys per card, for debugging
    python scrape_chart.py            # -> src/data/jungle_prices.csv
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
    "Japanese Snorlax": "https://www.pricecharting.com/game/pokemon-japanese-jungle/snorlax-143",
    "English Snorlax 1st Edition": "https://www.pricecharting.com/game/pokemon-jungle/snorlax-1st-edition-11",
    "English Snorlax No Symbol": "https://www.pricecharting.com/game/pokemon-jungle/snorlax-no-symbol-11",
    "English Snorlax Unlimited": "https://www.pricecharting.com/game/pokemon-jungle/snorlax-11",
    "Japanese Jolteon": "https://www.pricecharting.com/game/pokemon-japanese-jungle/jolteon-135",
    "English Jolteon 1st Edition": "https://www.pricecharting.com/game/pokemon-jungle/jolteon-1st-edition-4",
    "English Jolteon No Symbol": "https://www.pricecharting.com/game/pokemon-jungle/jolteon-no-symbol-4",
    "English Jolteon Unlimited": "https://www.pricecharting.com/game/pokemon-jungle/jolteon-4",
    "Japanese Flareon": "https://www.pricecharting.com/game/pokemon-japanese-jungle/flareon-136",
    "English Flareon 1st Edition": "https://www.pricecharting.com/game/pokemon-jungle/flareon-1st-edition-3",
    "English Flareon No Symbol": "https://www.pricecharting.com/game/pokemon-jungle/flareon-no-symbol-3",
    "English Flareon Unlimited": "https://www.pricecharting.com/game/pokemon-jungle/flareon-3",
    "Japanese Vaporeon": "https://www.pricecharting.com/game/pokemon-japanese-jungle/vaporeon-134",
    "English Vaporeon 1st Edition": "https://www.pricecharting.com/game/pokemon-jungle/vaporeon-1st-edition-12",
    "English Vaporeon No Symbol": "https://www.pricecharting.com/game/pokemon-jungle/vaporeon-no-symbol-12",
    "English Vaporeon Unlimited": "https://www.pricecharting.com/game/pokemon-jungle/vaporeon-12",
    "Japanese Clefable": "https://www.pricecharting.com/game/pokemon-japanese-jungle/clefable-36",
    "English Clefable 1st Edition": "https://www.pricecharting.com/game/pokemon-jungle/clefable-1st-edition-1",
    "English Clefable Unlimited": "https://www.pricecharting.com/game/pokemon-jungle/clefable-1",
    "Japanese Electrode": "https://www.pricecharting.com/game/pokemon-japanese-jungle/electrode-101",
    "English Electrode 1st Edition": "https://www.pricecharting.com/game/pokemon-jungle/electrode-1st-edition-2",
    "English Electrode Unlimited": "https://www.pricecharting.com/game/pokemon-jungle/electrode-2",
    "Japanese Kangaskhan": "https://www.pricecharting.com/game/pokemon-japanese-jungle/kangaskhan-115",
    "English Kangaskhan 1st Edition": "https://www.pricecharting.com/game/pokemon-jungle/kangaskhan-1st-edition-5",
    "English Kangaskhan Unlimited": "https://www.pricecharting.com/game/pokemon-jungle/kangaskhan-5",
    "Japanese Mr Mime": "https://www.pricecharting.com/game/pokemon-japanese-jungle/mr-mime-122",
    "English Mr Mime 1st Edition": "https://www.pricecharting.com/game/pokemon-jungle/mr-mime-1st-edition-6",
    "English Mr Mime Unlimited": "https://www.pricecharting.com/game/pokemon-jungle/mr-mime-6",
    "Japanese Nidoqueen": "https://www.pricecharting.com/game/pokemon-japanese-jungle/nidoqueen-31",
    "English Nidoqueen 1st Edition": "https://www.pricecharting.com/game/pokemon-jungle/nidoqueen-1st-edition-7",
    "English Nidoqueen Unlimited": "https://www.pricecharting.com/game/pokemon-jungle/nidoqueen-7",
    "Japanese Pidgeot": "https://www.pricecharting.com/game/pokemon-japanese-jungle/pidgeot-18",
    "English Pidgeot 1st Edition": "https://www.pricecharting.com/game/pokemon-jungle/pidgeot-1st-edition-8",
    "English Pidgeot Unlimited": "https://www.pricecharting.com/game/pokemon-jungle/pidgeot-8",
    "Japanese Pinsir": "https://www.pricecharting.com/game/pokemon-japanese-jungle/pinsir-127",
    "English Pinsir 1st Edition": "https://www.pricecharting.com/game/pokemon-jungle/pinsir-1st-edition-9",
    "English Pinsir Unlimited": "https://www.pricecharting.com/game/pokemon-jungle/pinsir-9",
    "Japanese Scyther": "https://www.pricecharting.com/game/pokemon-japanese-jungle/scyther-123",
    "English Scyther 1st Edition": "https://www.pricecharting.com/game/pokemon-jungle/scyther-1st-edition-10",
    "English Scyther Unlimited": "https://www.pricecharting.com/game/pokemon-jungle/scyther-10",
    "Japanese Venomoth": "https://www.pricecharting.com/game/pokemon-japanese-jungle/venomoth-49",
    "English Venomoth 1st Edition": "https://www.pricecharting.com/game/pokemon-jungle/venomoth-1st-edition-13",
    "English Venomoth Unlimited": "https://www.pricecharting.com/game/pokemon-jungle/venomoth-13",
    "Japanese Victreebel": "https://www.pricecharting.com/game/pokemon-japanese-jungle/victreebel-71",
    "English Victreebel 1st Edition": "https://www.pricecharting.com/game/pokemon-jungle/victreebel-1st-edition-14",
    "English Victreebel Unlimited": "https://www.pricecharting.com/game/pokemon-jungle/victreebel-14",
    "Japanese Vileplume": "https://www.pricecharting.com/game/pokemon-japanese-jungle/vileplume-45",
    "English Vileplume 1st Edition": "https://www.pricecharting.com/game/pokemon-jungle/vileplume-1st-edition-15",
    "English Vileplume Unlimited": "https://www.pricecharting.com/game/pokemon-jungle/vileplume-15",
    "Japanese Wigglytuff": "https://www.pricecharting.com/game/pokemon-japanese-jungle/wigglytuff-40",
    "English Wigglytuff 1st Edition": "https://www.pricecharting.com/game/pokemon-jungle/wigglytuff-1st-edition-16",
    "English Wigglytuff Unlimited": "https://www.pricecharting.com/game/pokemon-jungle/wigglytuff-16"
}

# Chart series key -> grade label.
SERIES = {
    "used": "Ungraded",
    "cib": "Grade 7",
    "new": "Grade 8",
    "graded": "Grade 9",
    "manualonly": "PSA 10",
}

# The original columns keep their positions; the new ones are appended at the end,
# so notebooks that read columns by name (version, grade, date, price) are unaffected.
FIELDS = ["date", "version", "series", "grade", "price", "set", "card", "edition"]

SET_BY_SLUG = {
    "pokemon-base-set": "Base",
    "pokemon-japanese-expansion-pack": "Base",
    "pokemon-jungle": "Jungle",
    "pokemon-japanese-jungle": "Jungle",
}
EDITIONS = ("1st Edition", "Unlimited", "No Symbol", "Shadowless")


def parse_label(label):
    """'English Snorlax 1st Edition' -> ('Snorlax', '1st Edition'); 'Japanese Snorlax' -> ('Snorlax', 'Japanese')."""
    if label.startswith("Japanese "):
        return label[len("Japanese "):], "Japanese"
    name = label[len("English "):] if label.startswith("English ") else label
    for e in EDITIONS:
        if name.endswith(" " + e):
            return name[: -len(e) - 1], e
    print(f"warning: can't parse edition from label: {label}", file=sys.stderr)
    return name, ""


def set_of(url):
    slug = url.split("/game/")[1].split("/")[0]
    # Unknown slugs fall back to a readable name, e.g. pokemon-fossil -> "Fossil".
    return SET_BY_SLUG.get(slug, slug.replace("pokemon-", "").replace("japanese-", "").replace("-", " ").title())


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


def to_rows(version, url, data, divisor):
    card, edition = parse_label(version)
    set_name = set_of(url)
    rows = []
    for key, label in SERIES.items():
        for ts, value in data.get(key, []):
            if not value:  # 0 / null = no sales that month
                continue
            day = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).date().isoformat()
            rows.append({"date": day, "version": version, "series": key,
                         "grade": label, "price": round(value / divisor, 2),
                         "set": set_name, "card": card, "edition": edition})
    return rows


def load_existing(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if "version" in r]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="src/data/jungle_prices.csv")
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
        rows = to_rows(version, url, data, args.divisor)
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
    for r in kept:  # rows saved before the set/card/edition columns existed
        if not r.get("set") and r["version"] in CARDS:
            r["card"], r["edition"] = parse_label(r["version"])
            r["set"] = set_of(CARDS[r["version"]])
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
