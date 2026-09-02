import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import path from 'node:path';

// Cache-bust by content hash, not by build time: the URL changes only when
// the file's bytes change, so unchanged assets keep their cached copy.
const hashes = new Map();
function contentHash(siteRootPath) {
  if (hashes.has(siteRootPath)) return hashes.get(siteRootPath);
  const file = path.join('src', siteRootPath.replace(/^\//, ''));
  let h = '';
  try {
    h = createHash('sha256').update(readFileSync(file)).digest('hex').slice(0, 8);
  } catch {
    h = ''; // asset generated at build time rather than checked in
  }
  hashes.set(siteRootPath, h);
  return h;
}

export default function (eleventyConfig) {
  eleventyConfig.addPassthroughCopy({ 'src/assets': 'assets' });

  const TZ = 'America/New_York';
  const fmt = (opts) => new Intl.DateTimeFormat('en-US', { timeZone: TZ, ...opts });

  eleventyConfig.addFilter('day', (d) =>
    fmt({ weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' }).format(new Date(d)));
  eleventyConfig.addFilter('clock', (d) =>
    fmt({ hour: 'numeric', minute: '2-digit' }).format(new Date(d)));
  eleventyConfig.addFilter('isoDate', (d) => new Date(d).toISOString().slice(0, 10));
  eleventyConfig.addFilter('monthKey', (d) =>
    fmt({ month: 'long', year: 'numeric' }).format(new Date(d)));

  // Group a list of events into [{ month, events }] preserving input order.
  eleventyConfig.addFilter('byMonth', function (events) {
    const key = (d) => fmt({ month: 'long', year: 'numeric' }).format(new Date(d));
    const out = [];
    for (const e of events) {
      const m = key(e.start);
      if (!out.length || out[out.length - 1].month !== m) out.push({ month: m, events: [] });
      out[out.length - 1].events.push(e);
    }
    return out;
  });

  // iCal wants UTC basic-format timestamps and escapes , ; \ and newlines.
  eleventyConfig.addFilter('icsStamp', (d) =>
    new Date(d).toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, ''));
  eleventyConfig.addFilter('icsEscape', (s) =>
    String(s).replace(/\\/g, '\\\\').replace(/;/g, '\\;').replace(/,/g, '\\,').replace(/\r?\n/g, '\\n'));


  // The first upcoming show is rendered as the highlight; this yields the rest.
  eleventyConfig.addFilter('slice_after_first', (arr) => (arr || []).slice(1));

  eleventyConfig.addFilter('bust', (url) => {
    const h = contentHash(url);
    return h ? `${url}?v=${h}` : url;
  });

  return {
    pathPrefix: '/',
    dir: { input: 'src', output: '_site', includes: '_includes', data: '_data' },
    markdownTemplateEngine: 'njk',
    htmlTemplateEngine: 'njk',
  };
}
