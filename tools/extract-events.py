#!/usr/bin/env python3
"""Extract structured event data from the Squarespace mirror into events.json.

This is the first `source adapter`: it reads the wget mirror under reference/
(or braindead.live/ pre-move) and emits the normalized event schema the 11ty
build consumes. Later adapters (FetchRSS/Facebook ingest) emit the same shape.
"""
import re, json, glob, html, os, sys, unicodedata
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else 'braindead.live')
CAL = ROOT / 'calendar'

def unesc(x):
    return html.unescape(html.unescape(x or '')).strip()

# Facebook/Squarespace titles use mathematical-alphanumeric Unicode as styling.
# Fold it to ASCII so titles are searchable, sortable and screen-reader safe.
def defancy(s):
    out = []
    for ch in s:
        d = unicodedata.decomposition(ch)
        n = unicodedata.normalize('NFKC', ch)
        out.append(n if n.isascii() or not ch.isascii() is False else ch)
    return unicodedata.normalize('NFKC', s)

def jsonld_event(src):
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', src, re.S):
        raw = m.group(1)
        if '"Event"' not in raw:
            continue
        try:
            d = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if d.get('@type') == 'Event':
            return d
    return None

def content_region(src):
    i = src.find('eventitem-column-content')
    j = src.find('</article>', i)
    return src[i:j] if i > 0 else ''

def body_html(region):
    parts = re.findall(r'<div class="sqs-html-content"[^>]*>(.*?)</div>', region, re.S)
    return '\n'.join(p.strip() for p in parts).strip()

def ticket_link(region, slug):
    m = re.search(r'data-definition-name="website\.components\.button".*?<a href="([^"]+)"', region, re.S)
    if not m:
        return None
    href = unesc(m.group(1))
    # wget --convert-links rewrote off-site ticket URLs to local paths.
    if not href.startswith('http'):
        return {'href': href, 'mangled_by_wget': True}
    return {'href': href, 'mangled_by_wget': False}

def flyer(region, ld):
    m = re.search(r'<img[^>]*data-src="([^"]+)"', region)
    src = unesc(m.group(1)) if m else (ld.get('image') or [None])[0]
    return src

def ical(slug):
    p = CAL / f'{slug}?format=ical'
    if not p.exists():
        return {}
    t = p.read_text(encoding='utf-8', errors='replace')
    g = lambda k: (re.search(rf'^{k}:(.*)$', t, re.M) or [None, None])[1]
    out = {}
    for k in ('UID', 'DTSTART', 'DTEND', 'LOCATION', 'GEO'):
        v = g(k)
        if v:
            out[k.lower()] = v.strip().replace('\\,', ',').replace('\;', ';')
    return out

events = []
for f in sorted(CAL.glob('*.html')):
    slug = f.stem
    src = f.read_text(encoding='utf-8', errors='replace')
    ld = jsonld_event(src)
    if not ld:
        print(f'  !! no Event JSON-LD: {slug}', file=sys.stderr)
        continue
    region = content_region(src)
    title = unesc(ld.get('name', ''))
    title = re.sub(r'\s*[—–-]\s*Brain Dead Live\s*$', '', title)
    ic = ical(slug)
    events.append({
        'slug': slug,
        'title': defancy(title),
        'start': ld.get('startDate'),
        'end': ld.get('endDate'),
        'flyer': flyer(region, ld),
        'ticket': ticket_link(region, slug),
        'location': ic.get('location') or None,
        'geo': ic.get('geo') or None,
        'uid': ic.get('uid'),
        'body_html': body_html(region),
        'source': {'adapter': 'squarespace-mirror', 'path': str(f)},
    })

events.sort(key=lambda e: e['start'] or '')
out = Path('src/_data/events.json')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(events, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print(f'wrote {out} — {len(events)} events')
