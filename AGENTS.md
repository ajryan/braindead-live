# AGENTS.md

Guidance for AI coding agents working in this repository.

## What this repo is

A static mirror of https://braindead.live (a live-music venue site built on
Squarespace), fetched with `wget --mirror --convert-links --page-requisites
--span-hosts`. It is **not** a live Squarespace site and has no backend —
it's raw HTML/CSS/JS/images meant to be rebuilt into something simpler.

Top-level layout:

- `braindead.live/` — the actual pages: `index.html` (homepage),
  `calendar.html` (events list), `calendar/*.html` (46 individual event
  pages, one per show, each with a matching `?format=ical` file for
  calendar export).
- `assets.squarespace.com/`, `static1.squarespace.com/`,
  `definitions.sqspcdn.com/`, `images.squarespace-cdn.com/` — mirrored
  third-party assets (Squarespace's CDN domains), named to match the
  original hostnames so relative links in the HTML resolve correctly.

Every event page is the same template with different content (flyer image,
date, venue, description). There is no build system — this is raw output.

## History / what's already been done

1. Initial mirror (`wget`), including CDN assets so pages render offline.
2. A conservative cleanup pass removed Squarespace's own first-party
   telemetry (performance/RUM beacon, JS error reporter, the unused
   member-account system, CLDR locale pack) and the vestigial cart
   icon/page (the site sells nothing). CSS was reformatted with Prettier.

See `TODO.md` for what's left before this is ready for a real redesign.

## Hard-won constraints — read before touching HTML/CSS/JS here

- **Do not run Prettier (or any HTML reformatter) on the `.html` files.**
  Verified empirically: even with `--html-whitespace-sensitivity strict`,
  reformatting shifts page layout by 100+ px. This markup relies on custom
  CSS `display` semantics (Squarespace's Fluid Engine block system) that a
  generic formatter can't infer, so it silently breaks whitespace-sensitive
  inline layout. CSS files are safe to reformat; HTML is not, until it's
  rewritten with sane layout in the redesign.
- **`Static.SQUARESPACE_CONTEXT` (the `<script data-name="static-context">`
  blob) is load-bearing, not dead weight.** `site-bundle.js` reads it at
  runtime to hydrate the contact form fields, the video embed, and the
  marquee text. Removing it silently breaks all three with no console
  error. Leave it alone until those components are rebuilt natively.
- **The vendor JS bundles bake telemetry into the same file as core
  rendering code.** `common-*.js` fires Squarespace's own
  `/api/census/*` analytics calls; there's no clean way to strip just the
  telemetry from a minified bundle. Don't try — replace the whole bundle
  when rebuilding instead.
- **Any change to a page's visible rendering must be verified with a
  real headless-browser screenshot, not just an HTML diff.** Use
  Playwright, serve the repo over `python3 -m http.server` (not
  `file://` — `crossorigin` script tags get CORS-blocked under the `null`
  origin `file://` gives you, which produces false failures), and compare
  `document.body.scrollHeight` plus a full-page screenshot before/after.
  A byte-level diff of the HTML tells you nothing about whether the page
  still looks right.
- Image files under `images.squarespace-cdn.com/` are frequently
  referenced with `&` in the filename but `%26` or `&amp;` in the HTML
  that links to them — a plain substring search for "is this file
  referenced" will produce false-positive orphans unless you account for
  that encoding mismatch.

## Environment notes

This machine had none of node/npm/gh/wget/lxml/bs4/playwright preinstalled;
they were added via Homebrew/pip as needed. Don't assume a fresh clone or a
different machine has them — check before relying on any of them.
