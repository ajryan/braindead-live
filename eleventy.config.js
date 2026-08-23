// GitHub Pages project sites serve from /<repo>/, so every root-absolute
// URL needs prefixing. Set PATH_PREFIX in CI; empty for a custom domain.
const PATH_PREFIX = process.env.PATH_PREFIX || '';

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

  return {
    pathPrefix: PATH_PREFIX ? `${PATH_PREFIX}/` : '/',
    dir: { input: 'src', output: '_site', includes: '_includes', data: '_data' },
    markdownTemplateEngine: 'njk',
    htmlTemplateEngine: 'njk',
  };
}
