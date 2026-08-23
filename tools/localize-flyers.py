#!/usr/bin/env python3
"""Copy each event's flyer out of the mirror into srccontent/flyers/.

Squarespace serves one source image in 6-7 widths (?format=100w..2500w).
We keep only the largest and let the build derive any sizes it needs, which
is TODO's "decide a real responsive-image strategy and drop the rest".
"""
import json, re, shutil, sys
from pathlib import Path
from urllib.parse import urlparse, unquote

MIRROR = Path('reference/images.squarespace-cdn.com')
OUT = Path('content/flyers')
DATA = Path('src/_data/events.json')
WIDTHS = [2500, 1500, 1000, 750, 500, 300, 100]

events = json.loads(DATA.read_text(encoding='utf-8'))
OUT.mkdir(parents=True, exist_ok=True)

def candidates(url):
    """Local paths that might hold this image, largest first."""
    p = urlparse(url)
    # AGENTS.md: refs use %26 / &amp; where the file on disk has a literal &.
    rel = unquote(p.path).lstrip('/')
    rel = rel.replace('&amp;', '&')
    base = MIRROR / rel.replace('content/v1/', 'content/v1/', 1)
    for w in WIDTHS:
        yield base.with_name(base.name + f'?format={w}w'), w
    yield base, 0

resolved, missed = 0, []
for e in events:
    url = e.get('flyer')
    if not url:
        continue
    picked = None
    for path, w in candidates(url):
        if path.is_file() and path.stat().st_size > 0:
            picked = (path, w)
            break
    if not picked:
        missed.append((e['slug'], url))
        continue
    src, w = picked
    ext = Path(urlparse(url).path).suffix.lower() or '.jpg'
    dest = OUT / f"{e['slug']}{ext}"
    shutil.copyfile(src, dest)
    e['flyer'] = f'content/flyers/{dest.name}'
    e['flyer_source_width'] = w or None
    resolved += 1

DATA.write_text(json.dumps(events, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print(f'localized {resolved}/{len(events)} flyers -> {OUT}')
for slug, url in missed:
    print(f'  !! unresolved: {slug}  {url[:90]}', file=sys.stderr)
