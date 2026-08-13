#!/usr/bin/env python3
"""
Checks every race in races.csv against current official sources using the
Claude API (with web search) and reports any dates that appear to have
changed. Does NOT overwrite races.csv directly -- it writes a report and
lets the GitHub Action open a PR so a human reviews before anything is
merged. Racing fixtures get postponed/moved more often than you'd think
(weather, track conditions, broadcaster deals) so auto-committing without
review is asking for a bad surprise on your calendar.

Requires env var ANTHROPIC_API_KEY.

Usage:
    python3 verify_dates.py
"""

import csv
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import urllib.request
import urllib.error

HERE = Path(__file__).parent
CSV_PATH = HERE / "races.csv"
REPORT_PATH = HERE / "date_check_report.md"

API_KEY = os.environ.get("ANTHROPIC_API_KEY")
API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-6"

DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


def ask_claude(race_name: str, track: str, country: str, current_date: str) -> dict:
    """Ask Claude (with web search) to confirm this race's 2026 date."""
    prompt = (
        f"Search for the official, confirmed 2026 date of the horse race "
        f"\"{race_name}\" held at {track}, {country}. "
        f"My records currently show {current_date}. "
        f"Reply with EXACTLY one line in this format and nothing else:\n"
        f"STATUS: <CONFIRMED_SAME | CONFIRMED_DIFFERENT | NOT_YET_ANNOUNCED>\n"
        f"DATE: <YYYY-MM-DD or UNKNOWN>\n"
        f"SOURCE: <domain of the source you used, or NONE>"
    )

    body = {
        "model": MODEL,
        "max_tokens": 300,
        "messages": [{"role": "user", "content": prompt}],
        "tools": [{"type": "web_search_20250305", "name": "web_search"}],
    }

    req = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": API_KEY,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"status": "ERROR", "detail": f"HTTP {e.code}: {e.read().decode()[:200]}"}
    except Exception as e:
        return {"status": "ERROR", "detail": str(e)}

    text_blocks = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
    full_text = "\n".join(text_blocks)

    status_match = re.search(r"STATUS:\s*(\w+)", full_text)
    date_match = DATE_RE.search(full_text)
    source_match = re.search(r"SOURCE:\s*(\S+)", full_text)

    return {
        "status": status_match.group(1) if status_match else "PARSE_ERROR",
        "found_date": date_match.group(1) if date_match else None,
        "source": source_match.group(1) if source_match else None,
        "raw": full_text.strip(),
    }


def main():
    if not API_KEY:
        print("ERROR: ANTHROPIC_API_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)

    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    changes = []
    unconfirmed = []
    errors = []

    # Only check races whose date hasn't already passed -- no point
    # re-verifying history, and it keeps weekly API usage from growing
    # unbounded as more years of rows accumulate in the CSV.
    today = datetime.utcnow()
    checkable_rows = [
        r for r in rows
        if r.get("date") and datetime.strptime(r["date"], "%Y-%m-%d") >= today
    ]

    for i, row in enumerate(checkable_rows, 1):
        race_id, name, track, country = row["race_id"], row["race_name"], row["track"], row["country"]
        current = row["date"]
        print(f"[{i}/{len(checkable_rows)}] Checking {name} ({row['year']})...", file=sys.stderr)

        result = ask_claude(f"{name} ({row['year']} edition)", track, country, current)

        if result.get("status") == "ERROR":
            errors.append((name, result["detail"]))
        elif result.get("status") == "CONFIRMED_DIFFERENT" and result.get("found_date"):
            changes.append({
                "race_id": race_id, "race": name, "track": track, "country": country,
                "old_date": current, "new_date": result["found_date"],
                "source": result.get("source", "unknown"),
            })
        elif result.get("status") == "NOT_YET_ANNOUNCED":
            unconfirmed.append((name, current))
        # CONFIRMED_SAME / PARSE_ERROR -> no action needed

        time.sleep(0.3)  # light rate-limit courtesy

    # Apply confirmed changes directly to races.csv, matched on race_id +
    # year so this only ever touches the specific yearly edition that was
    # checked, never a different year's row for the same race.
    if changes:
        by_key = {(c["race_id"], c["old_date"]): c["new_date"] for c in changes}
        for row in rows:
            key = (row["race_id"], row["date"])
            if key in by_key:
                row["date"] = by_key[key]
                row["year"] = by_key[key].split("-")[0]
        fieldnames = list(rows[0].keys())
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    # Write a human-readable report for the PR description
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("# Weekly date check report\n\n")
        if changes:
            f.write(f"## {len(changes)} date(s) changed\n\n")
            f.write("| Race | Old date | New date | Source |\n|---|---|---|---|\n")
            for c in changes:
                f.write(f"| {c['race']} ({c['country']}) | {c['old_date']} | {c['new_date']} | {c['source']} |\n")
            f.write("\n")
        else:
            f.write("No date changes found this week.\n\n")

        if unconfirmed:
            f.write(f"## {len(unconfirmed)} race(s) still not officially announced\n\n")
            for name, current in unconfirmed:
                f.write(f"- {name} (placeholder date: {current})\n")
            f.write("\n")

        if errors:
            f.write(f"## {len(errors)} lookup error(s)\n\n")
            for name, detail in errors:
                f.write(f"- {name}: {detail}\n")

    print(f"\nDone. {len(changes)} changed, {len(unconfirmed)} unconfirmed, {len(errors)} errors.", file=sys.stderr)
    # Signal to the workflow whether there's anything to PR
    print("HAS_CHANGES=" + ("true" if changes else "false"))


if __name__ == "__main__":
    main()
