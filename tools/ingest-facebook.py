#!/usr/bin/env python3
"""Ingest events from the venue's public Facebook events tab.

Facebook server-renders a GraphQL payload into that page containing real
structured Event nodes (id, name, venue, day_time_sentence, canonical url,
cover image). That is a far better source than the FetchRSS post feed, which
carries mostly non-events with dates only in prose.

Design constraints, learned the hard way:

* Only *upcoming* events are server-rendered; the Past collection is lazy
  loaded. So this merges **additively** and never deletes. A show missing
  from the fetch means "not upcoming", not "deleted".
* This is undocumented internal GraphQL, not an API contract. Any failure to
  fetch or parse is a no-op: the committed events.json is left untouched and
  the build carries on. The site must never break because Facebook changed.
* Cover image URLs are signed and expire within days, so they are downloaded
  at ingest rather than hotlinked.
* content/overrides.json stays authoritative; nothing here overwrites it.
"""
import json, re, sys, unicodedata, hashlib
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("America/New_York")
except Exception:
    TZ = None

PAGE_ID = "61559195090068"
URL = f"https://www.facebook.com/profile.php?id={PAGE_ID}&sk=events"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Upgrade-Insecure-Requests": "1",
}
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "src/_data/events.json"
FLYERS = ROOT / "content/flyers"


def fetch(url, tries=3, binary=False):
    last = None
    for attempt in range(tries):
        try:
            with urlopen(Request(url, headers=HEADERS), timeout=45) as r:
                raw = r.read()
            return raw if binary else raw.decode("utf-8", "replace")
        except (URLError, OSError) as e:      # transient HTTP/2 resets are common
            last = e
    raise RuntimeError(f"fetch failed after {tries} tries: {last}")


def json_objects(src, needle):
    """Yield the complete JSON object starting at each occurrence of needle."""
    for m in re.finditer(re.escape(needle), src):
        start, depth, i, in_str = m.start(), 0, m.start(), False
        while i < len(src):
            ch = src[i]
            if in_str:
                if ch == "\\":
                    i += 2
                    continue
                if ch == '"':
                    in_str = False
            elif ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        yield json.loads(src[start:i + 1]), start, i
                    except json.JSONDecodeError:
                        pass
                    break
            i += 1


def parse_when(sentence, now=None):
    """'Sat, Sep 26 at 5:00 PM EDT' -> ISO 8601. Year is inferred."""
    if not sentence:
        return None
    s = sentence.replace(" ", " ").replace(" ", " ")
    s = re.sub(r"\s+", " ", s).strip()
    m = re.match(
        r"^(?:\w{3},\s*)?(\w{3})\s+(\d{1,2})(?:,\s*(\d{4}))?\s+at\s+"
        r"(\d{1,2}):(\d{2})\s*([AP]M)", s, re.I)
    if not m:
        return None
    mon, day, year, hh, mm, ap = m.groups()
    try:
        month = datetime.strptime(mon[:3], "%b").month
    except ValueError:
        return None
    hh = int(hh) % 12 + (12 if ap.upper() == "PM" else 0)
    now = now or datetime.now(TZ) if TZ else (now or datetime.now())
    if year:
        years = [int(year)]
    else:
        # no year given: pick the nearest occurrence that has not long passed
        years = [now.year, now.year + 1, now.year - 1]
    best = None
    for y in years:
        try:
            dt = datetime(y, month, int(day), hh, int(mm), tzinfo=TZ)
        except ValueError:
            continue
        if year or dt >= now - timedelta(days=2):
            best = dt
            break
        best = best or dt
    if not best:
        return None
    return best.strftime("%Y-%m-%dT%H:%M:%S%z")


def slugify(name):
    n = unicodedata.normalize("NFKD", name)
    n = "".join(c for c in n if not unicodedata.combining(c))
    n = unicodedata.normalize("NFKC", n).lower()
    n = re.sub(r"[^a-z0-9]+", "-", n).strip("-")
    return re.sub(r"-{2,}", "-", n)[:80] or "event"


def title_tokens(s):
    n = unicodedata.normalize("NFKC", s).lower()
    return {t for t in re.findall(r"[a-z0-9]{3,}", n)}


def same_event(existing, start_iso, name):
    """Match a Facebook event to an already-known one by date + title overlap."""
    if not existing.get("start") or not start_iso:
        return False
    if existing["start"][:10] != start_iso[:10]:
        return False
    a, b = title_tokens(existing.get("title", "")), title_tokens(name)
    return bool(a & b)


def main():
    events = json.loads(DATA.read_text(encoding="utf-8"))
    try:
        html = fetch(URL)
    except Exception as e:
        print(f"ingest: fetch failed, leaving events.json untouched ({e})", file=sys.stderr)
        return 0

    found, added, updated = 0, 0, 0
    for obj, start_i, end_i in json_objects(html, '{"__typename":"Event","id":"'):
        if obj.get("__typename") != "Event" or not obj.get("id"):
            continue
        found += 1
        name = unicodedata.normalize("NFKC", obj.get("name") or "").strip()
        start = parse_when(obj.get("day_time_sentence"))
        if not name or not start:
            print(f"ingest: skipping {obj.get('id')} - unparseable "
                  f"({obj.get('day_time_sentence')!r})", file=sys.stderr)
            continue
        place = obj.get("event_place") or {}
        venue = place.get("contextual_name")
        city = (((place.get("location") or {}).get("reverse_geocode") or {})
                .get("city"))
        # the cover image sits on the sibling node, just after the event object
        img = None
        tail = html[end_i:end_i + 1200]
        im = re.search(r'"image":\{"uri":"(https:[^"]+)"', tail)
        if im:
            img = im.group(1).replace("\\/", "/")   # JSON-escaped slashes

        target = next((e for e in events
                       if e.get("fbId") == obj["id"] or same_event(e, start, name)), None)
        if target is None:
            target = {"slug": slugify(name), "source": {"adapter": "facebook-events"}}
            if any(e["slug"] == target["slug"] for e in events):
                target["slug"] += "-" + obj["id"][-4:]
            events.append(target)
            added += 1
        else:
            updated += 1

        target["fbId"] = obj["id"]
        target["fbUrl"] = obj.get("url")
        target["title"] = target.get("title") or name
        target["start"] = start
        target.setdefault("end", None)            # FB gives no end time; keep any existing
        if venue:
            target["location"] = venue
        if city:
            target["city"] = city
        target["canceled"] = bool(obj.get("is_canceled"))
        target.setdefault("body_html", "")
        target.setdefault("ticket", None)

        if img and not target.get("flyer"):
            dest = FLYERS / f"{target['slug']}.jpg"
            try:
                dest.write_bytes(fetch(img, binary=True))
                target["flyer"] = f"content/flyers/{dest.name}"
                print(f"ingest: downloaded cover -> {dest.name}")
            except Exception as e:
                print(f"ingest: cover download failed for {target['slug']} ({e})",
                      file=sys.stderr)

    if not found:
        print("ingest: no Event nodes found - page shape may have changed; "
              "leaving events.json untouched", file=sys.stderr)
        return 0

    events.sort(key=lambda e: e.get("start") or "")
    before = DATA.read_bytes()
    after = (json.dumps(events, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    if before == after:
        print(f"ingest: {found} event(s) found, no changes")
        return 0
    DATA.write_bytes(after)
    print(f"ingest: {found} found, {added} added, {updated} updated -> {DATA.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
