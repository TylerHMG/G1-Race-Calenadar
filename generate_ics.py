#!/usr/bin/env python3
"""
Regenerates calendar.ics from races.csv.

Usage:
    python3 generate_ics.py

To update the calendar: edit races.csv (add/remove/edit rows), then re-run
this script and commit+push calendar.ics to GitHub. Anyone subscribed via
the webcal:// link will see the new events next time their calendar app
refreshes (refresh interval is set by the calendar app, typically every
few hours to once a day).

CSV columns:
    race_name, country, track, date_2026, all_day, category, notes,
    heat_sheet_url, watch_url

heat_sheet_url / watch_url are optional -- leave blank until you have them.
When filled in, they're added as clickable links in the event description.
"""

import csv
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid5, NAMESPACE_DNS

HERE = Path(__file__).parent
CSV_PATH = HERE / "races.csv"
ICS_PATH = HERE / "calendar.ics"

def esc(text: str) -> str:
    """Escape text per RFC 5545."""
    return (text or "").replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")

def fold(line: str) -> str:
    """Fold lines longer than 75 octets per RFC 5545."""
    out, cur = [], ""
    for ch in line:
        if len(cur.encode("utf-8")) >= 74:
            out.append(cur)
            cur = " " + ch
        else:
            cur += ch
    out.append(cur)
    return "\r\n".join(out)

def build_description(row: dict) -> str:
    parts = []
    if row.get("category"):
        parts.append(f"Category: {row['category']}")
    if row.get("notes"):
        parts.append(row["notes"])
    if row.get("heat_sheet_url"):
        parts.append(f"Heat sheet: {row['heat_sheet_url']}")
    if row.get("watch_url"):
        parts.append(f"Watch: {row['watch_url']}")
    return " | ".join(parts)

def main():
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    now_stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//G1 Horse Racing Calendar//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Global G1 Horse Races",
        "X-WR-CALDESC:Group 1 / Grade 1 horse races worldwide",
        "X-WR-TIMEZONE:UTC",
        "REFRESH-INTERVAL;VALUE=DURATION:PT12H",
        "X-PUBLISHED-TTL:PT12H",
    ]

    for row in rows:
        name = row["race_name"].strip()
        if not name:
            continue
        date_str = row["date_2026"].strip()
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        dtstart = dt.strftime("%Y%m%d")
        dtend = (dt + timedelta(days=1)).strftime("%Y%m%d")

        uid = str(uuid5(NAMESPACE_DNS, f"{name}-{row['country']}-2026")) + "@g1races"
        location = f"{row['track']}, {row['country']}"
        description = build_description(row)

        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{uid}")
        lines.append(f"DTSTAMP:{now_stamp}")
        lines.append(fold(f"DTSTART;VALUE=DATE:{dtstart}"))
        lines.append(fold(f"DTEND;VALUE=DATE:{dtend}"))
        lines.append(fold(f"SUMMARY:{esc(name)} (G1)"))
        lines.append(fold(f"LOCATION:{esc(location)}"))
        if description:
            lines.append(fold(f"DESCRIPTION:{esc(description)}"))
        if row.get("heat_sheet_url"):
            lines.append(fold(f"URL:{row['heat_sheet_url']}"))
        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")

    with open(ICS_PATH, "w", newline="", encoding="utf-8") as f:
        f.write("\r\n".join(lines) + "\r\n")

    print(f"Wrote {ICS_PATH} with {len(rows)} events")

if __name__ == "__main__":
    main()
