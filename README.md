# Global G1 Horse Racing Calendar

128 Group 1 / Grade 1 races across the US, Canada, UK, Ireland, France,
Germany, Italy, Japan, Hong Kong, Australia, UAE, and Saudi Arabia for the
2026 season.

## What's in here
- `races.csv` — the actual data. Edit this to add/remove/correct races.
- `generate_ics.py` — turns races.csv into calendar.ics.
- `calendar.ics` — the file your calendar app subscribes to.

## ⚠️ Important caveat on dates
Some of the dates in here are officially confirmed (I pulled these from
recent racing-authority announcements). Others — especially races whose
2026 fixture hasn't been published yet — are my best estimate based on
where that race has historically sat on the calendar. Treat every date as
provisional until you see it confirmed closer to race day, especially for
anything more than ~2 months out. I'd recommend a quick pass to verify
dates each quarter (or ask me to re-check them).

## One-time setup: get this live on GitHub

1. **Create a free GitHub account** if you don't have one: github.com/join
2. **Create a new repository** — click the "+" top right → "New repository".
   Name it something like `g1-race-calendar`. Keep it **Public** (private
   repos' raw files aren't fetchable by calendar apps without a token).
3. **Upload the three files** (`races.csv`, `generate_ics.py`,
   `calendar.ics`) — on the repo page, click "Add file" → "Upload files",
   drag them in, and commit.
4. **Get the raw URL for calendar.ics** — click on `calendar.ics` in the
   repo, then click the "Raw" button. The URL will look like:
   ```
   https://raw.githubusercontent.com/YOUR_USERNAME/g1-race-calendar/main/calendar.ics
   ```
5. **Turn it into a webcal link** — just swap `https://` for `webcal://`:
   ```
   webcal://raw.githubusercontent.com/YOUR_USERNAME/g1-race-calendar/main/calendar.ics
   ```
6. **Subscribe** — paste that `webcal://` URL into:
   - **Apple Calendar**: File → New Calendar Subscription
   - **Google Calendar**: Other calendars (+) → From URL (use the
     `https://` version, Google doesn't need `webcal://`)
   - **Outlook**: Add calendar → Subscribe from web

Your calendar app will re-fetch this URL periodically (Apple/Google
typically check every few hours to once a day — you can't force a
shorter interval, that's controlled by the subscribing app, not the file).

## Updating the calendar later

1. Edit `races.csv` (add a row, fix a date, or fill in `heat_sheet_url` /
   `watch_url` for a race once you have the links).
2. Run `python3 generate_ics.py` to regenerate `calendar.ics`.
3. Commit and push the updated `calendar.ics` to GitHub (or just
   re-upload it through the web UI — same file path, so it overwrites).
4. Everyone subscribed sees the changes on their next auto-refresh — no
   need to re-subscribe.

If you'd rather not run Python yourself each time, you can also just ask
me in a future chat to update specific rows and regenerate the file for
you — bring the updated `races.csv` and I'll do the rest.

## Adding heat sheets & watch links
Two blank columns are already in the CSV for this: `heat_sheet_url` and
`watch_url`. Fill them in per race and regenerate — they'll show up in
the event description, and `heat_sheet_url` also gets set as the event's
clickable URL field.
