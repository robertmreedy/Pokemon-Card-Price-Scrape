#!/usr/bin/env python3
"""Extract the price-history chart series that PriceCharting embeds in item
pages (Base Set holos: Japanese, 1st Edition, Unlimited) and write one tidy CSV.

    pip install requests
    python scrape_base.py --dump     # print series keys per card, for debugging
    python scrape_base.py            # -> src/data/base_prices.csv
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
    "Japanese Alakazam": "https://www.pricecharting.com/game/pokemon-japanese-expansion-pack/alakazam-65",
    "English Alakazam 1st Edition": "https://www.pricecharting.com/game/pokemon-base-set/alakazam-1st-edition-1",
    "English Alakazam Unlimited": "https://www.pricecharting.com/game/pokemon-base-set/alakazam-1",
    "English Alakazam Shadowless": "https://www.pricecharting.com/game/pokemon-base-set/alakazam-shadowless-1",
    "Japanese Blastoise": "https://www.pricecharting.com/game/pokemon-japanese-expansion-pack/blastoise-9",
    "English Blastoise 1st Edition": "https://www.pricecharting.com/game/pokemon-base-set/blastoise-1st-edition-2",
    "English Blastoise Unlimited": "https://www.pricecharting.com/game/pokemon-base-set/blastoise-2",
    "English Blastoise Shadowless": "https://www.pricecharting.com/game/pokemon-base-set/blastoise-shadowless-2",
    "Japanese Chansey": "https://www.pricecharting.com/game/pokemon-japanese-expansion-pack/chansey-113",
    "English Chansey 1st Edition": "https://www.pricecharting.com/game/pokemon-base-set/chansey-1st-edition-3",
    "English Chansey Unlimited": "https://www.pricecharting.com/game/pokemon-base-set/chansey-3",
    "English Chansey Shadowless": "https://www.pricecharting.com/game/pokemon-base-set/chansey-shadowless-3",
    "Japanese Charizard": "https://www.pricecharting.com/game/pokemon-japanese-expansion-pack/charizard-6",
    "English Charizard 1st Edition": "https://www.pricecharting.com/game/pokemon-base-set/charizard-1st-edition-4",
    "English Charizard Unlimited": "https://www.pricecharting.com/game/pokemon-base-set/charizard-4",
    "English Charizard Shadowless": "https://www.pricecharting.com/game/pokemon-base-set/charizard-shadowless-4",
    "Japanese Clefairy": "https://www.pricecharting.com/game/pokemon-japanese-expansion-pack/clefairy-35",
    "English Clefairy 1st Edition": "https://www.pricecharting.com/game/pokemon-base-set/clefairy-1st-edition-5",
    "English Clefairy Unlimited": "https://www.pricecharting.com/game/pokemon-base-set/clefairy-5",
    "English Clefairy Shadowless": "https://www.pricecharting.com/game/pokemon-base-set/clefairy-shadowless-5",
    "Japanese Gyarados": "https://www.pricecharting.com/game/pokemon-japanese-expansion-pack/gyarados-130",
    "English Gyarados 1st Edition": "https://www.pricecharting.com/game/pokemon-base-set/gyarados-1st-edition-6",
    "English Gyarados Unlimited": "https://www.pricecharting.com/game/pokemon-base-set/gyarados-6",
    "English Gyarados Shadowless": "https://www.pricecharting.com/game/pokemon-base-set/gyarados-shadowless-6",
    "Japanese Hitmonchan": "https://www.pricecharting.com/game/pokemon-japanese-expansion-pack/hitmonchan-107",
    "English Hitmonchan 1st Edition": "https://www.pricecharting.com/game/pokemon-base-set/hitmonchan-1st-edition-7",
    "English Hitmonchan Unlimited": "https://www.pricecharting.com/game/pokemon-base-set/hitmonchan-7",
    "English Hitmonchan Shadowless": "https://www.pricecharting.com/game/pokemon-base-set/hitmonchan-shadowless-7",
    "Japanese Machamp": "https://www.pricecharting.com/game/pokemon-japanese-expansion-pack/machamp-68",
    "English Machamp 1st Edition": "https://www.pricecharting.com/game/pokemon-base-set/machamp-1st-edition-8",
    "English Machamp Unlimited": "https://www.pricecharting.com/game/pokemon-base-set/machamp-8",
    "English Machamp Shadowless": "https://www.pricecharting.com/game/pokemon-base-set/machamp-shadowless-8",
    "Japanese Magneton": "https://www.pricecharting.com/game/pokemon-japanese-expansion-pack/magneton-82",
    "English Magneton 1st Edition": "https://www.pricecharting.com/game/pokemon-base-set/magneton-1st-edition-9",
    "English Magneton Unlimited": "https://www.pricecharting.com/game/pokemon-base-set/magneton-9",
    "English Magneton Shadowless": "https://www.pricecharting.com/game/pokemon-base-set/magneton-shadowless-9",
    "Japanese Mewtwo": "https://www.pricecharting.com/game/pokemon-japanese-expansion-pack/mewtwo-150",
    "English Mewtwo 1st Edition": "https://www.pricecharting.com/game/pokemon-base-set/mewtwo-1st-edition-10",
    "English Mewtwo Unlimited": "https://www.pricecharting.com/game/pokemon-base-set/mewtwo-10",
    "English Mewtwo Shadowless": "https://www.pricecharting.com/game/pokemon-base-set/mewtwo-shadowless-10",
    "Japanese Nidoking": "https://www.pricecharting.com/game/pokemon-japanese-expansion-pack/nidoking-34",
    "English Nidoking 1st Edition": "https://www.pricecharting.com/game/pokemon-base-set/nidoking-1st-edition-11",
    "English Nidoking Unlimited": "https://www.pricecharting.com/game/pokemon-base-set/nidoking-11",
    "English Nidoking Shadowless": "https://www.pricecharting.com/game/pokemon-base-set/nidoking-shadowless-11",
    "Japanese Ninetales": "https://www.pricecharting.com/game/pokemon-japanese-expansion-pack/ninetales-38",
    "English Ninetales 1st Edition": "https://www.pricecharting.com/game/pokemon-base-set/ninetales-1st-edition-12",
    "English Ninetales Unlimited": "https://www.pricecharting.com/game/pokemon-base-set/ninetales-12",
    "English Ninetales Shadowless": "https://www.pricecharting.com/game/pokemon-base-set/ninetales-shadowless-12",
    "Japanese Poliwrath": "https://www.pricecharting.com/game/pokemon-japanese-expansion-pack/poliwrath-62",
    "English Poliwrath 1st Edition": "https://www.pricecharting.com/game/pokemon-base-set/poliwrath-1st-edition-13",
    "English Poliwrath Unlimited": "https://www.pricecharting.com/game/pokemon-base-set/poliwrath-13",
    "English Poliwrath Shadowless": "https://www.pricecharting.com/game/pokemon-base-set/poliwrath-shadowless-13",
    "Japanese Raichu": "https://www.pricecharting.com/game/pokemon-japanese-expansion-pack/raichu-26",
    "English Raichu 1st Edition": "https://www.pricecharting.com/game/pokemon-base-set/raichu-1st-edition-14",
    "English Raichu Unlimited": "https://www.pricecharting.com/game/pokemon-base-set/raichu-14",
    "English Raichu Shadowless": "https://www.pricecharting.com/game/pokemon-base-set/raichu-shadowless-14",
    "Japanese Venusaur": "https://www.pricecharting.com/game/pokemon-japanese-expansion-pack/venusaur-3",
    "English Venusaur 1st Edition": "https://www.pricecharting.com/game/pokemon-base-set/venusaur-1st-edition-15",
    "English Venusaur Unlimited": "https://www.pricecharting.com/game/pokemon-base-set/venusaur-15",
    "English Venusaur Shadowless": "https://www.pricecharting.com/game/pokemon-base-set/venusaur-shadowless-15",
    "Japanese Zapdos": "https://www.pricecharting.com/game/pokemon-japanese-expansion-pack/zapdos-145",
    "English Zapdos 1st Edition": "https://www.pricecharting.com/game/pokemon-base-set/zapdos-1st-edition-16",
    "English Zapdos Unlimited": "https://www.pricecharting.com/game/pokemon-base-set/zapdos-16",
    "English Zapdos Shadowless": "https://www.pricecharting.com/game/pokemon-base-set/zapdos-shadowless-16"
}

# Chart series key -> grade label.
SERIES = {
    "used": "Ungraded",
    "cib": "Grade 7",
    "new": "Grade 8",
    "graded": "Grade 9",
    "manualonly": "PSA 10",
}

# Same columns as the Jungle file, so the two CSVs can be merged directly.
FIELDS = ["date", "version", "grade", "set", "card", "edition", "price"]

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
            rows.append({"date": day, "version": version, "grade": label,
                         "set": set_name, "card": card, "edition": edition,
                         "price": round(value / divisor, 2)})
    return rows


def load_existing(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if "version" in r]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="src/data/base_prices.csv")
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
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} rows -> {args.out}")


if __name__ == "__main__":
    main()
