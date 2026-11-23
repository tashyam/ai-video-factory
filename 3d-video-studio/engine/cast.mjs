// Cast and car looks for a video, avoiding what the last 5 videos used (registry.json next to this file).
//
//   node cast.mjs new <project> --chars schemer,quiet,officer,agent,victim --cars schemer,upgrade,quiet,buddy,traffic,traffic [--seed N] [--palette name]
//   node cast.mjs reroll <project> <key>        new look for one entry (e.g. victim_2), keeps the rest
//   node cast.mjs show <project>                 one line per entry
//   node cast.mjs register <project> [title]     after the final render: log what this video used
//
// Writes <project>/cast.json. In video.js:
//   import CAST from './cast.json' with { type: 'json' };
//   const schemer = makeChar(CAST.characters.schemer); const car = buildCar(CAST.cars.schemer);
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const V = await import(pathToFileURL(path.join(HERE, 'src', 'variety.js')).href);
const REG = path.join(HERE, 'registry.json');
const reg = fs.existsSync(REG) ? JSON.parse(fs.readFileSync(REG, 'utf8')) : { videos: [] };
const [mode, proj, ...rest] = process.argv.slice(2);
const flag = (k) => { const i = rest.indexOf(k); return i < 0 ? undefined : rest[i + 1]; };
const file = proj && path.join(path.resolve(proj), 'cast.json');
const hex = (n) => '#' + n.toString(16).padStart(6, '0');

function show(c) {
  console.log(`palette ${c.palette}, seed ${c.seed}`);
  for (const [k, v] of Object.entries(c.characters)) console.log(`  ${k.padEnd(12)} ${v.style.padEnd(9)} ${(v.build || "average").padEnd(8)} ${(v.outfit || "-").padEnd(9)} shirt ${hex(v.shirt)}  R ${v.R}  girth ${v.girth}  ${v.acc.join(' ') || '-'}`);
  for (const [k, v] of Object.entries(c.cars)) console.log(`  ${k.padEnd(12)} ${v.type.padEnd(9)} paint ${hex(v.color)}  ${Object.keys(v.skin).join(' ') || '-'}  interior ${v.interior || '-'}  "${v.plate}"`);
}

if (mode === 'new') {
  const chars = (flag('--chars') || 'schemer,quiet').split(',').filter(Boolean), cars = (flag('--cars') || '').split(',').filter(Boolean);
  const seed = flag('--seed') ? +flag('--seed') : V.hashSeed(path.basename(path.resolve(proj)) + Date.now());
  const c = V.cast({ seed, chars, cars, recent: reg.videos.slice(-5), palette: flag('--palette') });
  c.request = { chars, cars };
  fs.writeFileSync(file, JSON.stringify(c, null, 1)); show(c);
} else if (mode === 'reroll') {
  const c = JSON.parse(fs.readFileSync(file, 'utf8')), key = rest[0];
  const isChar = key in c.characters, entry = isChar ? c.characters[key] : c.cars[key];
  if (!entry) { console.log('no entry', key); process.exit(1); }
  const others = [...Object.values(c.characters).map((v) => `${v.role}|${v.style}|${V.hueBucket(v.shirt)}`), ...Object.values(c.cars).map((v) => `${v.role}|${v.type}|${V.hueBucket(v.color)}`)];
  const one = V.cast({ seed: (c.seed + V.hashSeed(key + Date.now())) >>> 0, palette: c.palette, chars: isChar ? [entry.role] : [], cars: isChar ? [] : [entry.role],
    recent: [...reg.videos.slice(-5), { signatures: others }] });
  const fresh = Object.values(isChar ? one.characters : one.cars)[0];
  (isChar ? c.characters : c.cars)[key] = fresh;
  fs.writeFileSync(file, JSON.stringify(c, null, 1)); show(c);
} else if (mode === 'show') {
  show(JSON.parse(fs.readFileSync(file, 'utf8')));
} else if (mode === 'register') {
  const c = JSON.parse(fs.readFileSync(file, 'utf8'));
  const sigs = [...Object.values(c.characters).map((v) => `${v.role}|${v.style}|${V.hueBucket(v.shirt)}`), ...Object.values(c.cars).map((v) => `${v.role}|${v.type}|${V.hueBucket(v.color)}`)];
  reg.videos.push({ title: rest[0] || path.basename(path.resolve(proj)), date: new Date().toISOString().slice(0, 10), palette: c.palette, signatures: sigs });
  fs.writeFileSync(REG, JSON.stringify(reg, null, 1));
  console.log(`registered "${reg.videos.at(-1).title}" (${sigs.length} looks). ${reg.videos.length} videos in the registry.`);
} else {
  console.log(fs.readFileSync(fileURLToPath(import.meta.url), 'utf8').split('\n').slice(0, 11).join('\n'));
}
