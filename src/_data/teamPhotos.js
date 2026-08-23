import { readFile } from 'node:fs/promises';
import renderImage from '../../lib/image.js';

export default async function () {
  const team = JSON.parse(await readFile(new URL('./team.json', import.meta.url), 'utf8'));
  return Promise.all(
    team.map(async (m) => ({
      ...m,
      photoHtml: await renderImage(m.photo, {
        alt: `${m.name}, ${m.role}`,
        sizes: '(max-width: 40rem) 50vw, 16rem',
        widths: [320, 640, 960],
      }),
    }))
  );
}
