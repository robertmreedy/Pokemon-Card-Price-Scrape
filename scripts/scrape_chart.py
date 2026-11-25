"""Scrape PriceCharting item pages: the embedded price-history chart and the
population report. One request per page feeds both outputs.

    pip install requests beautifulsoup4
    python scrape_chart.py                  # -> src/data/prices.csv + src/data/pop.csv
    python scrape_chart.py --dump           # chart series keys per card
    python scrape_chart.py --dump-pop       # what the pop parser found per card
    python scrape_chart.py --save-html dbg  # save each page's raw HTML to ./dbg
"""
import argparse
import csv
import json
import os
import re
import sys
import time
from datetime import date, datetime, timezone

import requests
from bs4 import BeautifulSoup

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
    "boxonly": "Grade 9.5",
    "manualonly": "PSA 10",
}

FIELDS = ["date", "version", "series", "grade", "price"]
POP_FIELDS = ["version", "grader", "grade", "pop", "scraped_on"]

GRADERS = {"psa", "bgs", "cgc", "sgc", "tag", "ace", "total"}
COUNT_WORDS = {"pop", "population", "count"}
GRADE_RE = re.compile(
    r"^(?:grade\s*)?(?:(psa|bgs|cgc|sgc|tag|ace)\s*)?(\d{1,2}(?:\.\d)?)"
    r"(?:\s*(?:pristine|prist\.?|black))?$", re.I)


# ---------- fetching ----------

def fetch_html(url):
    resp = requests.get(url, timeout=30, headers={
        "User-Agent": "Mozilla/5.0 (personal price-history project)"})
    resp.raise_for_status()
    return resp.text


# ---------- price chart ----------

def extract_chart_data(html):
    m = re.search(r"chart_data\s*=\s*", html)
    if not m:
        raise ValueError("chart_data not found in page source")
    start = html.index("{", m.end())
    obj, _ = json.JSONDecoder().raw_decode(html[start:])
    return obj


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


# ---------- population report ----------

def _text(el):
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True))


def _num(s):
    m = re.search(r"\d[\d,]*", s)
    return int(m.group().replace(",", "")) if m else None


def _is_grader(h):
    h = h.lower().strip()
    return h in GRADERS or h in COUNT_WORDS


def parse_pop_table(table):
    """Return [(grader, grade, pop)] if this looks like a population table, else [].
    Handles graders-as-columns and graders-as-rows."""
    rows = [[_text(c) for c in tr.find_all(["th", "td"])] for tr in table.find_all("tr")]
    rows = [r for r in rows if r]
    if len(rows) < 2:
        return []
    header, body = rows[0], rows[1:]
    if any("sale date" in h.lower() for h in header):
        return []

    out = []
    row_labels = [r[0] for r in body]
    head = header[1:]

    if (sum(bool(GRADE_RE.match(x)) for x in row_labels) >= 0.6 * len(row_labels)
            and head and all(_is_grader(h) for h in head)):
        # rows = grades, columns = graders
        for r in body:
            m = GRADE_RE.match(r[0])
            if not m:
                continue
            for j, grader in enumerate(head):
                n = _num(r[j + 1]) if j + 1 < len(r) else None
                if n is not None:
                    out.append(((m.group(1) or grader).upper(), m.group(2), n))
    elif (sum(bool(GRADE_RE.match(h)) for h in head) >= 0.6 * max(len(head), 1)
            and all(_is_grader(x) for x in row_labels)):
        # rows = graders, columns = grades
        for r in body:
            for j, h in enumerate(head):
                m = GRADE_RE.match(h)
                n = _num(r[j + 1]) if j + 1 < len(r) else None
                if m and n is not None:
                    out.append((r[0].upper(), m.group(2), n))

    return out if len(out) >= 3 else []


def extract_pop(html):
    soup = BeautifulSoup(html, "html.parser")
    seen, rows = set(), []
    for table in soup.find_all("table"):
        for grader, grade, n in parse_pop_table(table):
            if (grader, grade) not in seen:
                seen.add((grader, grade))
                rows.append((grader, grade, n))
    headers = [[_text(c) for c in t.find("tr").find_all(["th", "td"])][:8]
               for t in soup.find_all("table") if t.find("tr")]
    return rows, headers


# ---------- io ----------

def load_existing(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if "version" in r]


def write_csv(path, fields, rows):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="src/data/prices.csv")
    ap.add_argument("--pop-out", default="src/data/pop.csv")
    ap.add_argument("--divisor", type=float, default=100.0,
                    help="chart values are assumed to be cents; use 1 if dollars")
    ap.add_argument("--dump", action="store_true")
    ap.add_argument("--dump-pop", action="store_true")
    ap.add_argument("--save-html", metavar="DIR")
    args = ap.parse_args()

    existing = load_existing(args.out)
    existing_pop = load_existing(args.pop_out)
    fresh, failed = [], []
    fresh_pop, failed_pop = [], []
    today = date.today().isoformat()

    for i, (version, url) in enumerate(CARDS.items()):
        if i:
            time.sleep(2)  # be polite between requests
        try:
            html = fetch_html(url)
        except requests.RequestException as e:
            print(f"warning: {version}: {e}", file=sys.stderr)
            failed.append(version)
            failed_pop.append(version)
            continue

        if args.save_html:
            os.makedirs(args.save_html, exist_ok=True)
            slug = re.sub(r"\W+", "-", version.lower()).strip("-")
            with open(os.path.join(args.save_html, slug + ".html"), "w", encoding="utf-8") as f:
                f.write(html)

        # --- chart ---
        try:
            data = extract_chart_data(html)
        except (ValueError, json.JSONDecodeError) as e:
            print(f"warning: {version}: {e}", file=sys.stderr)
            data = None
        if args.dump and data is not None:
            print(f"== {version}")
            for k, v in data.items():
                print(" ", k, len(v), v[:2])
        if not args.dump and not args.dump_pop:
            rows = to_rows(version, data, args.divisor) if data else []
            if rows:
                fresh += rows
                print(f"{version}: {len(rows)} price points")
            else:
                print(f"warning: {version}: no price points parsed", file=sys.stderr)
                failed.append(version)

        # --- population ---
        pop, headers = extract_pop(html)
        if args.dump_pop:
            print(f"== {version}: {len(pop)} pop rows")
            for p in pop[:6]:
                print("  ", p)
            if not pop:
                print("   tables seen (header cells):")
                for h in headers[:8]:
                    print("    ", h)
        elif pop:
            fresh_pop += [{"version": version, "grader": g, "grade": gr,
                           "pop": n, "scraped_on": today} for g, gr, n in pop]
            print(f"{version}: {len(pop)} pop rows")
        else:
            print(f"warning: {version}: no population table found", file=sys.stderr)
            failed_pop.append(version)

    if args.dump or args.dump_pop:
        return

    # A failed page keeps its previously saved rows instead of vanishing.
    if not fresh:
        sys.exit("error: nothing scraped from any card")
    rows = fresh + [r for r in existing if r["version"] in failed]
    rows.sort(key=lambda r: (r["version"], r["grade"], r["date"]))
    write_csv(args.out, FIELDS, rows)
    print(f"{len(rows)} rows -> {args.out}")

    # Population is best-effort: it never fails the run.
    if fresh_pop:
        kept = [r for r in existing_pop if r["version"] in failed_pop]
        pop_rows = fresh_pop + kept
        pop_rows.sort(key=lambda r: (r["version"], r["grader"], r["grade"]))
        write_csv(args.pop_out, POP_FIELDS, pop_rows)
        print(f"{len(pop_rows)} rows -> {args.pop_out}")
    else:
        print("note: no population data found on any page; pop file not written "
              "(run --dump-pop / --save-html to investigate)", file=sys.stderr)


if __name__ == "__main__":
    main()
EOF
pip install beautifulsoup4 -q 2>&1 | tail -1; python3 -m py_compile scrape_chart.py && python3 - <<'EOF'
import importlib.util
s=importlib.util.spec_from_file_location("m","scrape_chart.py");m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
cols = """<table><tr><th>Grade</th><th>PSA</th><th>CGC</th></tr>
<tr><td>10</td><td>1,234</td><td>56</td></tr><tr><td>9.5</td><td>–</td><td>12</td></tr><tr><td>9</td><td>2,000</td><td>30</td></tr></table>"""
rows_t = """<table><tr><th></th><th>10</th><th>9</th><th>8</th></tr>
<tr><td>PSA</td><td>1,234</td><td>2,000</td><td>900</td></tr><tr><td>BGS</td><td>5</td><td>7</td><td>9</td></tr></table>"""
price = """<table><tr><th>Ungraded</th><th>Grade 7</th><th>Grade 8</th><th>Grade 9</th></tr><tr><td>$57.80 -$1.92</td><td>$172</td><td>$271</td><td>$458</td></tr></table>"""
sales = """<table><tr><th>Sale Date</th><th>Title</th><th>Price</th></tr><tr><td>2026-11-23</td><td>x PSA 9</td><td>$435.00</td></tr></table>"""
for name, html in [("cols",cols),("rows",rows_t),("price",price),("sales",sales),("all",cols+price+sales)]:
    r,_ = m.extract_pop(html); print(name, r)
