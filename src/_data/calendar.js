import { readFile } from 'node:fs/promises';
import renderImage, { imageMeta } from '../../lib/image.js';

// Artist handles are the site's real "lineup" data — 65 of the 79 external
// links in event bodies are Instagram profiles. Promote them to structured
// data instead of leaving them buried in prose.
function lineup(bodyHtml) {
  const out = [];
  const re = /<a href="(https?:\/\/(?:www\.)?instagram\.com\/([^\/"?]+)[^"]*)"[^>]*>(.*?)<\/a>/gi;
  let m;
  while ((m = re.exec(bodyHtml))) {
    const handle = m[2].replace(/^@/, '');
    if (!out.some((a) => a.handle === handle)) {
      out.push({ handle, url: m[1], label: m[3].replace(/<[^>]+>/g, '').trim() || `@${handle}` });
    }
  }
  return out;
}

// The Squarespace "button block" is used for whatever the promoter felt like
// linking - usually an artist's Instagram, not a ticket page. Only treat a URL
// as a ticket link if it points at an actual ticketing host.
const TICKET_HOSTS = /(tickettailor|eventbrite|dice\.fm|seetickets|tixr|prekindle|bandsintown)\./i;

function ticketUrl(e) {
  const candidates = [];
  if (e.ticket && !e.ticket.mangled_by_wget && /^https?:/.test(e.ticket.href)) {
    candidates.push(e.ticket.href);
  }
  for (const m of e.body_html.matchAll(/href="(https?:\/\/[^"]+)"/gi)) candidates.push(m[1]);
  const hit = candidates.find((u) => TICKET_HOSTS.test(u));
  if (!hit) return null;
  // Strip click-tracking cruft (fbclid, utm_*) the way the earlier telemetry
  // cleanup did — these come from pasting links out of Facebook/Instagram.
  const url = new URL(hit.replace(/&amp;/g, '&'));
  for (const k of [...url.searchParams.keys()]) {
    if (/^(fbclid|gclid|mc_[a-z]+|utm_[a-z]+)$/i.test(k)) url.searchParams.delete(k);
  }
  return url.toString();
}

// Ticket links also appear inline in the event body prose, not just as
// buttons. Tag those too, so "buy-tickets" counts every real ticket click.
function tagTicketLinks(html, slug) {
  // Squarespace emitted some anchors with an empty target attribute, which
  // is invalid. Drop it rather than shipping broken markup.
  html = html.replace(/\s+target=""/g, '');
  return html.replace(/<a\s+href="(https?:\/\/[^"]+)"/gi, (m, href) =>
    TICKET_HOSTS.test(href)
      ? `<a data-umami-event="buy-tickets" data-umami-event-placement="body" data-umami-event-slug="${slug}" href="${href}"`
      : m
  );
}

export default async function () {
  const raw = JSON.parse(
    await readFile(new URL('./events.json', import.meta.url), 'utf8')
  );
  // Hand corrections keyed by slug — ingested data is never the last word.
  const overrides = JSON.parse(
    await readFile(new URL('../../content/overrides.json', import.meta.url), 'utf8')
  );

  const events = await Promise.all(raw.map(async (e) => ({
    ...e,
    ...(overrides[e.slug] || {}),
    body_html: tagTicketLinks(e.body_html || '', e.slug),
    url: `/calendar/${e.slug}/`,
    lineup: lineup(e.body_html),
    ticketUrl: (overrides[e.slug] || {}).ticketUrl || ticketUrl(e),
    // Fields below are ones the Facebook ingest can supply for every future
    // event, so the card renders consistently rather than degrading.
    canceled: Boolean(e.canceled),
    icsUrl: `/calendar/${e.slug}.ics`,
    flyerHtml: await renderImage(e.flyer, { alt: `Flyer for ${e.title}`, sizes: '(max-width: 46rem) 100vw, 46rem', cls: 'flyer' }),
    cardHtml: await renderImage(e.flyer, { sizes: '(max-width: 40rem) 50vw, 15rem' }),
    // Absolute-safe URL for og:image and any non-<picture> use.
    flyerUrl: await imageMeta(e.flyer).then((m) => (m && m.jpeg ? m.jpeg[m.jpeg.length - 1].url : null)),
  })));

  const now = Date.now();
  const upcoming = events
    .filter((e) => new Date(e.end || e.start).getTime() >= now)
    .sort((a, b) => new Date(a.start) - new Date(b.start));
  const past = events
    .filter((e) => new Date(e.end || e.start).getTime() < now)
    .sort((a, b) => new Date(b.start) - new Date(a.start));

  return { all: events, upcoming, past, next: upcoming[0] || null };
}
