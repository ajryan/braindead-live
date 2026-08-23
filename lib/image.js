import Image from '@11ty/eleventy-img';

const PATH_PREFIX = process.env.PATH_PREFIX || '';

/**
 * Generate responsive <picture> markup at build time.
 *
 * This is called from _data files rather than a template shortcode on
 * purpose: Nunjucks {% include %} does not await async shortcodes, so an
 * async {% image %} inside a partial renders as an empty string with no
 * error. Precomputing keeps templates synchronous and partials safe.
 */
export async function imageMeta(src, widths = [320, 640, 960, 1400]) {
  if (!src) return null;
  return Image(src, {
    widths,
    formats: ['jpeg'],
    outputDir: '_site/img/',
    urlPath: `${PATH_PREFIX}/img/`,
    sharpJpegOptions: { quality: 82, progressive: true },
  });
}

export default async function renderImage(src, { alt = '', sizes, cls = '', widths = [320, 640, 960, 1400] } = {}) {
  if (!src) return '';
  const metadata = await Image(src, {
    widths,
    formats: ['avif', 'webp', 'jpeg'],
    outputDir: '_site/img/',
    urlPath: `${PATH_PREFIX}/img/`,
    sharpJpegOptions: { quality: 82, progressive: true },
  });
  return Image.generateHTML(metadata, {
    alt, sizes, class: cls, loading: 'lazy', decoding: 'async',
  });
}
