# TODO

Status: raw Squarespace mirror, conservatively cleaned (telemetry/unused
cart removed, CSS formatted). Not yet a rebuildable site. See `AGENTS.md`
for constraints discovered while cleaning this up — read it before
touching HTML.

## Redesign prep

- [ ] Pick a static site generator (11ty, Astro, Hugo, etc.) and set up a
      real build.
- [ ] Consolidate the 46 near-identical event pages in `braindead.live/calendar/`
      into a single template + a data file (JSON/YAML/frontmatter per
      event: title, date, venue, flyer image, description, ticket link).
- [ ] Replace the `Static.SQUARESPACE_CONTEXT`-dependent contact form,
      video embed, and marquee text with native implementations — see
      `AGENTS.md` for why removing the context blob outright breaks them.
- [ ] Rebuild layout without the Fluid Engine `container-styles` /
      `transform-vars` inline style soup — real CSS (flexbox/grid), not
      per-block absolute positioning.
- [ ] Drop the Squarespace vendor JS bundles (`common-*.js`,
      `site-bundle.js`, polyfiller, `definitions.sqspcdn.com` component
      scripts) entirely rather than trying to trim them further.

## Assets

- [ ] Self-host fonts or pick system fonts — currently still loads live
      from `file.squarespace-cdn.com` even in this "mirror."
- [ ] Decide a real responsive-image strategy and drop the rest —
      each flyer currently has 6-7 resolution variants (100w-2500w)
      carried over from Squarespace's image API.
- [ ] Rename the `?format=ical` files (literal `?` in the filename is a
      `wget` artifact, awkward outside a mirror context).

## Once the above is done

- [ ] HTML is safe to run through Prettier/a linter only after layout no
      longer depends on Squarespace's whitespace-sensitive inline
      positioning (see AGENTS.md — not safe against the current markup).
- [ ] Add a real lint/format config (stylelint, htmlhint or equivalent)
      as permanent tooling once there's hand-authored markup to lint.
