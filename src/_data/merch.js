import renderImage from '../../lib/image.js';

// Show merch is one item at a time, sold through a Square hosted checkout —
// there is no store, and nothing in the Facebook ingest carries it, so it is
// configured here rather than in the event data.
// Three edits are baked into this file, all of them load-bearing:
//   1. cropped from the 3:4 camera original to the flyer's 4:5, so the two
//      landing columns render identically sized — the CSS matches them on
//      height only and assumes both sources share an aspect ratio;
//   2. cut off its brick wall onto #ffffff, the same white the flyer's
//      border carries, so the pair reads as one set not a poster beside a
//      snapshot;
//   3. framed tight, running the sleeves off both edges. A hanging tee is
//      wider than tall, so it cannot fill a 4:5 frame without that — the
//      alternative is a band of dead white above and below it.
// The unedited camera original is NOT in the repo. Keep a copy elsewhere
// before re-editing, and re-crop any replacement to 4:5.
//
// The .png is the cutout with a real alpha channel; the .jpg beside it is the
// same framing flattened onto white. Switching between them is this one line
// plus the `formats` below — but see .lp-shirt in site.css, which supplies the
// glass surface the transparent version needs and the white one does not.
const SHIRT_SRC = 'content/merch/infinity-tribe-nester-seven-teller-shirt.png';
const SHIRT_ALT =
  'Black Brain Dead Live show t-shirt for Infinity Tribe & Nester at the Carroll Creek Amphitheater, Sept 26.';

export default async function () {
  return {
    shirt: {
      // Square hosted checkout. Returning the buyer to /thanks/ after payment
      // is configured on Square's side, not here.
      buyUrl: 'https://square.link/u/29uzrqlq',
      pickup: 'the ticket booth at the Carroll Creek Stage on Sep 26, from 5pm to 10pm',
      // Precomputed for the same reason calendar.js precomputes flyers:
      // Nunjucks {% include %} does not await async shortcodes, so an
      // {% image %} inside a partial renders empty with no error.
      html: await renderImage(SHIRT_SRC, {
        alt: SHIRT_ALT,
        sizes: '(max-width: 52rem) 60vw, 22rem',
        widths: [320, 640, 960],
        // PNG, not JPEG, for the fallback: JPEG has no alpha and sharp would
        // flatten the cutout onto black. avif/webp carry it fine.
        formats: ['avif', 'webp', 'png'],
      }),
    },
  };
}
