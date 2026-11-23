// Film a /3d-video-studio project in headless Chromium. Run from anywhere; <project> holds index.html + video.js.
//
//   node film.mjs stills <project> <out_dir> t1 t2 ...        full-size JPEG stills (1 sample, no blur)
//   node film.mjs sheet  <project> <out.jpg> t1 t2 ... [--w 180] [--cols 6]   small contact sheet only
//   node film.mjs render <project> <out.mp4> <t0> <t1>          one encoded file (H.264, yuv420p, 30 fps)
//   node film.mjs check  <project> <t0> <t1> [step] [--verbose]  numeric frame + shot checks, text only; exit code 1 on any FAIL
//   node film.mjs cues   <project>                           sound cue list -> <project>/audio/cues.json (then audio/mix.py)
//   node film.mjs lookcheck <project> <out_dir> t1 t2 ... [--page lookdev.html]   house-look scores per frame (scene + pixels)
//   --page lookdev.html   (any mode) film another page of the project instead of index.html: the look sheet (step 4)
//
// The server maps /_engine/* to this folder and /node_modules/* to this folder's node_modules,
// everything else to <project>. Playwright comes from the shared kit (~/.claude/kit) or KIT=...
// GL: default uses the GPU through ANGLE; GL=swiftshader forces software rendering.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { spawn, spawnSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const ENGINE = path.dirname(fileURLToPath(import.meta.url));
const KIT = process.env.KIT || [path.join(ENGINE, '..', 'kit'), path.join(os.homedir(), '.claude', 'kit')]
  .find(d => fs.existsSync(path.join(d, 'node_modules', 'playwright'))) || path.join(ENGINE, '..', 'kit');
const { chromium } = createRequire(path.join(KIT, 'node_modules', '/'))('playwright');
const FPS = 30, W = 1080, H = 1920;
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json',
  '.woff2': 'font/woff2', '.woff': 'font/woff', '.png': 'image/png', '.jpg': 'image/jpeg', '.wav': 'audio/wav' };

function serve(root) {
  const srv = http.createServer((req, res) => {
    let p = decodeURIComponent(req.url.split('?')[0]);
    let f;
    if (p.startsWith('/_engine/')) f = path.join(ENGINE, p.slice(9));
    else if (p.startsWith('/node_modules/')) f = path.join(ENGINE, p);
    else f = path.join(root, p === '/' ? 'index.html' : p);
    fs.readFile(f, (e, d) => {
      if (e) { res.writeHead(404); res.end(); return; }
      res.writeHead(200, { 'Content-Type': TYPES[path.extname(f)] || 'application/octet-stream', 'Cache-Control': 'no-store' });
      res.end(d);
    });
  });
  return new Promise((ok) => srv.listen(0, '127.0.0.1', () => ok(srv)));
}

async function open(root, pageFile = 'index.html') {
  const srv = await serve(root);
  const args = process.env.GL === 'swiftshader' ? ['--use-angle=swiftshader', '--enable-unsafe-swiftshader']
    : ['--use-angle=' + (process.platform === 'win32' ? 'd3d11' : process.platform === 'darwin' ? 'metal' : 'gl'), '--ignore-gpu-blocklist', '--enable-gpu'];
  const browser = await chromium.launch({ args });
  const page = await browser.newPage({ viewport: { width: W, height: H } });
  page.on('console', (m) => { const t = m.text(); if (!/GL Driver Message|WebGL|GPU stall/.test(t)) console.log('console:', t.slice(0, 300)); });
  page.on('pageerror', (e) => console.log('PAGEERROR:', String(e).slice(0, 600)));
  await page.goto(`http://127.0.0.1:${srv.address().port}/${pageFile}`);
  await page.waitForFunction('window.ready === true', null, { timeout: 180000 });
  const gl = await page.evaluate(() => { const g = document.createElement('canvas').getContext('webgl2'); const x = g && g.getExtension('WEBGL_debug_renderer_info'); return x ? g.getParameter(x.UNMASKED_RENDERER_WEBGL) : '?'; });
  return { srv, browser, page, gl };
}

async function frame(page, t, n) {
  const d = await page.evaluate(([t, n]) => { window.draw(t, n); return window.grab(0.92); }, [t, n]);
  return Buffer.from(d.split(',', 2)[1], 'base64');
}
const samplesAt = (page, t) => page.evaluate((t) => (window.samplesAt ? window.samplesAt(t) : 1), t);

function tile(files, out, w, cols) {
  const h = Math.round(w * 16 / 9), rows = Math.ceil(files.length / cols);
  const inputs = files.flatMap((f) => ['-i', f]);
  const lab = files.map((f, i) => `[${i}:v]scale=${w}:${h}[v${i}]`).join(';');
  const pads = Array.from({ length: rows * cols - files.length }, (_, k) => `color=black:s=${w}x${h}:d=1[p${k}]`).join(';');
  const all = [...files.map((_, i) => `[v${i}]`), ...Array.from({ length: rows * cols - files.length }, (_, k) => `[p${k}]`)];
  const layout = all.map((_, i) => `${(i % cols) * w}_${Math.floor(i / cols) * h}`).join('|');
  const fc = all.length === 1 ? `[0:v]scale=${w}:${h}[o]` : [lab, pads, `${all.join('')}xstack=inputs=${all.length}:layout=${layout}[o]`].filter(Boolean).join(';');
  const r = spawnSync('ffmpeg', ['-v', 'error', '-y', ...inputs, '-filter_complex', fc, '-map', '[o]', '-frames:v', '1', '-q:v', '4', out]);
  if (r.status) throw new Error(String(r.stderr));
}

const [mode, proj, ...rest] = process.argv.slice(2);
if (!mode || !proj) { console.log(fs.readFileSync(fileURLToPath(import.meta.url), 'utf8').split('\n').slice(0, 9).join('\n')); process.exit(1); }
const flag = (k, d) => { const i = rest.indexOf(k); if (i < 0) return d; const v = rest[i + 1]; rest.splice(i, 2); return v; };
const pageFile = flag('--page', 'index.html');
const { srv, browser, page, gl } = await open(path.resolve(proj), pageFile);
const t0all = Date.now();
try {
  if (mode === 'stills' || mode === 'sheet') {
    const w = +flag('--w', 180), cols = +flag('--cols', 6);
    const out = rest.shift(), times = rest.map(Number);
    const dir = mode === 'stills' ? out : fs.mkdtempSync(path.join(os.tmpdir(), 'sheet-'));
    fs.mkdirSync(dir, { recursive: true });
    const files = [];
    for (const t of times) {
      const f = path.join(dir, `t${t.toFixed(2).padStart(5, '0')}.jpg`);
      fs.writeFileSync(f, await frame(page, t, 1)); files.push(f);
    }
    if (mode === 'sheet') { tile(files, out, w, cols); fs.rmSync(dir, { recursive: true, force: true }); }
    console.log(`${mode}: ${times.length} frames -> ${out}  (${((Date.now() - t0all) / 1000).toFixed(1)} s, ${gl})`);
  } else if (mode === 'render') {
    const out = rest[0], a = +rest[1], b = +rest[2], tmp = out.replace(/\.mp4$/, '.part.mp4');
    const ff = spawn('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y', '-f', 'image2pipe', '-c:v', 'mjpeg', '-framerate', String(FPS), '-i', '-',
      '-c:v', 'libx264', '-crf', '17', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', tmp], { stdio: ['pipe', 'inherit', 'inherit'] });
    const n = Math.round((b - a) * FPS);
    for (let i = 0; i < n; i++) {
      const t = a + i / FPS;
      if (!ff.stdin.write(await frame(page, t, await samplesAt(page, t)))) await new Promise((r) => ff.stdin.once('drain', r));
    }
    ff.stdin.end();
    const rc = await new Promise((r) => ff.on('close', r));
    if (rc === 0) { fs.renameSync(tmp, out); console.log(`render: ${n} frames -> ${out}  (${((Date.now() - t0all) / 1000).toFixed(0)} s, ${gl})`); }
    else { console.log('ffmpeg failed', rc); process.exitCode = 1; }
  } else if (mode === 'check') {
    const verbose = rest.includes('--verbose'); if (verbose) rest.splice(rest.indexOf('--verbose'), 1);
    const a = +rest[0], b = +rest[1], step = +(rest[2] || 0.25);
    const rows = await page.evaluate(([a, b, step]) => window.check(a, b, step), [a, b, step]);
    // voice pace over the speech span (whole video, printed once): the reference reads about 3.8 words a second
    const wf = path.join(path.resolve(proj), 'audio', 'vo.words.json');
    let pace = null;
    if (pageFile === 'index.html' && fs.existsSync(wf)) {
      const ws = JSON.parse(fs.readFileSync(wf, 'utf8')), span = ws.length ? ws[ws.length - 1].e - ws[0].s : 0, wps = span > 0 ? ws.length / span : 0;
      pace = { fail: !(wps >= 3.5 && wps <= 4.1), msg: `${ws.length} words over ${span.toFixed(1)} s of speech = ${wps.toFixed(2)} words/s` };
    }
    const bad = rows.filter((r) => r.level === 'fail' || r.level === 'warn' || (verbose && r.level === 'info'));
    for (const r of bad) console.log(`t=${r.t.toFixed(2).padStart(5)}  ${r.mark.padEnd(16)} ${r.level.toUpperCase().padEnd(4)} ${r.msg}`);
    const fails = rows.filter((r) => r.level === 'fail'), byRule = {};
    for (const r of fails) byRule[r.rule || 'other'] = (byRule[r.rule || 'other'] || 0) + 1;
    if (pace) console.log(`voice: ${pace.msg}` + (pace.fail ? '  FAIL: keep it 3.5-4.1 (reference 3.8); re-read the voice tighter or looser and re-time' : '  ok'));
    if (pace?.fail) { byRule['voice-pace'] = 1; fails.push({ rule: 'voice-pace' }); }
    console.log(`check: ${rows.length} probes, ${fails.length} fail, ${rows.filter((r) => r.level === 'warn').length} warn  (${((Date.now() - t0all) / 1000).toFixed(1)} s)`);
    console.log(fails.length ? 'FAIL rules: ' + Object.entries(byRule).map(([k, n]) => `${k} x${n}`).join(', ') : 'FAIL rules: none');
    if (fails.length) process.exitCode = 1;
  } else if (mode === 'cues') {   // sound cue list -> <project>/audio/cues.json, then: python engine/audio/mix.py <project>
    const c = await page.evaluate(() => window.__cues());
    const f = path.join(path.resolve(proj), 'audio', 'cues.json'); fs.mkdirSync(path.dirname(f), { recursive: true });
    fs.writeFileSync(f, JSON.stringify(c, null, 1));
    console.log(`cues: ${c.events.length} events, ${c.beds.length} beds, ${c.music.acts.length} music acts -> ${f}`);
  } else if (mode === 'lookcheck') {   // scene half in the page (src/lookcheck.js), pixel half in tools/look_score.py
    const dir = rest.shift(), times = rest.map(Number); fs.mkdirSync(dir, { recursive: true });
    const scene = {}, regions = {}, files = [];
    for (const t of times) {
      const name = `look_${t.toFixed(2).padStart(5, '0')}.jpg`, f = path.join(dir, name);
      fs.writeFileSync(f, await frame(page, t, 1)); files.push(f);
      const r = await page.evaluate(async (t) => (await import('/_engine/src/lookcheck.js')).lookcheck(t), t);
      if (r.regions.focus.length) {   // the same frame without lens blur, so the blur can be measured on the same content
        const d = await page.evaluate((t) => { const s = window.__shots.find((x) => t >= x.start && t < x.end); window.__dofSaved = s.dof; s.dof = null; window.draw(t, 1); const g = window.grab(0.92); s.dof = window.__dofSaved; return g; }, t);
        const sharpName = name.replace('.jpg', '_sharp.jpg'); fs.writeFileSync(path.join(dir, sharpName), Buffer.from(d.split(',', 2)[1], 'base64')); r.regions.sharp = sharpName;
      }
      scene[name] = r; regions[name] = r.regions;
    }
    const rf = path.join(dir, 'regions.json'); fs.writeFileSync(rf, JSON.stringify(regions));
    const py = spawnSync(process.env.PYTHON || 'python', ['-I', path.join(ENGINE, '..', 'tools', 'look_score.py'), ...files, '--regions', rf, '--json'], { encoding: 'utf8' });
    if (py.status) throw new Error(py.stderr);
    const px = Object.fromEntries(JSON.parse(py.stdout).map((r) => [r.frame, r]));
    const rows = [];
    for (const name of Object.keys(scene)) {
      const S = scene[name], P = px[name], sc = { ...P.scores };
      if (S.kind === 'indoor') sc.gloss = S.gloss == null ? null : Math.min(10, Math.round(100 * S.gloss / 0.8) / 10);   // the clear coat is read from the scene
      else delete sc.gloss;
      if (!S.inkOk && sc.outlines != null) sc.outlines = Math.min(sc.outlines, 4);
      if (S.kind === 'indoor' && S.wide) sc.light = S.lights > 0 ? 10 : 3;   // a wide interior must show its light sources
      if (S.kind !== 'studio') sc.depth = S.dofOk ? (sc.depth ?? 10) : Math.min(sc.depth ?? 3, 3);
      const low = Object.entries(sc).filter(([, v]) => v != null && v < 8).map(([k]) => k);
      rows.push({ name, kind: S.kind, sc, low });
      console.log(`t=${S.t.toFixed(2).padStart(5)} ${S.kind.padEnd(7)} ` + Object.entries(sc).map(([k, v]) => `${k} ${v == null ? '-' : Math.round(v)}`).join('  ') + (low.length ? `   LOW: ${low.join(', ')}` : ''));
      const notes = [];
      if (S.kind === 'indoor') notes.push(`coat on ${Math.round(100 * (S.gloss || 0))}% of ${S.solid} solids`, `${S.lights} light source(s) in frame`);
      notes.push(`ink ${S.ink}${S.inkCrease ? ' + creases' : ''}${S.inkOk ? '' : ' (wrong for ' + S.kind + ')'}`, S.dofMsg);
      const m = P.metrics; notes.push(Object.entries(m).map(([k, v]) => `${k}=${v}`).join(' '));
      console.log('        ' + notes.join(' | '));
    }
    const all = rows.flatMap((r) => Object.values(r.sc).filter((v) => v != null)), lowN = rows.filter((r) => r.low.length).length;
    console.log(`lookcheck: ${rows.length} frames, mean ${(all.reduce((a, b) => a + b, 0) / Math.max(1, all.length)).toFixed(1)}/10, ${lowN} with a score under 8 -> ${dir}`);
  } else if (mode === 'eval') {   // debugging: node film.mjs eval <project> "<js expression using window.__shots, THREE...>"
    console.log(await page.evaluate(async (code) => { const r = await (0, eval)(code); return typeof r === 'string' ? r : JSON.stringify(r, null, 1); }, rest.join(' ')));
  } else { console.log('unknown mode', mode); process.exitCode = 1; }
} finally { await browser.close(); srv.close(); }
