#!/usr/bin/env python3
"""
Regenerates calendar.ics from races.csv.

Usage:
    python3 generate_ics.py

To update the calendar: edit races.csv (add/remove/edit rows), then re-run
this script and commit+push calendar.ics to GitHub. Anyone subscribed via
the webcal:// link will see the new events next time their calendar app
refreshes (Apple ~hourly, Outlook ~1-4 hrs, Google ~8-24 hrs -- not
configurable by the publisher).

CSV columns:
    race_id, race_name, year, date, country, track, all_day, category,
    notes, heat_sheet_url, watch_url

- race_id: stable slug identifying the RACE regardless of year, e.g.
  "kentucky-derby". Every yearly edition of a race shares the same
  race_id but is its own row (its own year + date). This is what lets
  the file hold multiple years of the same race without them colliding
  or overwriting each other.
- year / date: date is the full YYYY-MM-DD for that edition; year is
  redundant with date but kept as its own column to make filtering and
  sorting by season easy to read/edit by hand.

heat_sheet_url / watch_url are optional -- leave blank until you have them.
When filled in, they're added as clickable links in the event description.

ROLLING WINDOW: only events within [today - PAST_DAYS, today + FUTURE_DAYS]
are written to calendar.ics. This keeps the feed from growing forever as
more years of data accumulate in races.csv -- old editions simply age out
of the published calendar (they stay in the CSV as history if you want it,
they just aren't published).
"""

import csv
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid5, NAMESPACE_DNS

HERE = Path(__file__).parent
CSV_PATH = HERE / "races.csv"
ICS_PATH = HERE / "calendar.ics"

# Rolling window: don't publish events older or further out than this.
PAST_DAYS = 90
FUTURE_DAYS = 548  # ~18 months


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

    now = datetime.utcnow()
    now_stamp = now.strftime("%Y%m%dT%H%M%SZ")
    window_start = now - timedelta(days=PAST_DAYS)
    window_end = now + timedelta(days=FUTURE_DAYS)

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

    included, skipped_out_of_window, skipped_bad_row = 0, 0, 0

    for row in rows:
        name = (row.get("race_name") or "").strip()
        race_id = (row.get("race_id") or "").strip()
        date_str = (row.get("date") or "").strip()
        if not name or not date_str:
            skipped_bad_row += 1
            continue

        dt = datetime.strptime(date_str, "%Y-%m-%d")
        if dt < window_start or dt > window_end:
            skipped_out_of_window += 1
            continue

        dtstart = dt.strftime("%Y%m%d")
        dtend = (dt + timedelta(days=1)).strftime("%Y%m%d")

        # UID keyed on race_id + the specific year, so each yearly edition
        # gets a distinct, STABLE id across regenerations (re-running this
        # script never creates duplicate events in subscribers' calendars,
        # and never collides two different years of the same race).
        year = (row.get("year") or date_str.split("-")[0]).strip()
        uid_key = race_id or name  # fall back to name if race_id missing
        uid = str(uuid5(NAMESPACE_DNS, f"{uid_key}-{year}")) + "@g1races"

        location = f"{row.get('track','')}, {row.get('country','')}"
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
        included += 1

    lines.append("END:VCALENDAR")

    with open(ICS_PATH, "w", newline="", encoding="utf-8") as f:
        f.write("\r\n".join(lines) + "\r\n")

    print(
        f"Wrote {ICS_PATH}: {included} events published, "
        f"{skipped_out_of_window} outside the {PAST_DAYS}d-past/"
        f"{FUTURE_DAYS}d-future window, {skipped_bad_row} skipped "
        f"(missing name/date)"
    )


if __name__ == "__main__":
    main()
