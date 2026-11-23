// Characters in the painted-cartoon look: a big round white head drawn on a 2D canvas every frame (always faces the
// camera, sits in front of the shoulders; features shift with the angle between where the character faces and the
// camera; hidden from behind), a softly shaded clothing torso (collar, buttons, belt, suit, uniform...) with a dark
// brown ink outline, thin ink limbs with small hands and shoes. Characters render on CHAR_LAYER, crisp on top of the
// painted world (core.js renderStage).
//
// makeChar({ R, shirt, hair, hair2, style, glasses, acc, outfit, role, girth, torso, legs }) -> Group with
//   .pose({ hip, neck, face, expr, arms: [[ctrl, hand], [ctrl, hand]], legs: [[ctrl, foot], [ctrl, foot]] }, camera)
//     all points in the parent's local space; face = the direction the character looks.
//   .headWorld() -> head centre in world space (for checks), .R head radius in metres.
// outfit: 'plain' | 'tee' | 'polo' | 'shirt' | 'suit' | 'uniform' | 'hoodie' (default from role, else from the shirt colour)
// Expressions: PRE presets, exprAt([[t, 'name'], ...], t) blends over 0.13 s (4 frames). talkAt() = anime mouth flaps.
import { THREE, V3, clamp, lerp, ease, rng, canvas, ctex, CHAR_LAYER, CHAR_UNI } from './core.js';

export const INK = '#2b1a12';
const SKIN = '#f8f3ea', SKIN_SHADE = '#e6d6c3';
// Hand-drawn heads, every character its own (measured on 23 reference heads): height/width 0.83-1.01, an egg taper
// (narrower at the chin), a slightly pointed crown (superellipse n 1.5-2.0) over a fuller jaw (n 2.05-2.5), one cheek
// bulging (toward the side the face turns to), a small tilt, and a fixed low-frequency wobble of about 1 % of the head
// width, like a line drawn by hand (it never boils from frame to frame). headShapeFor(o) seeds it from the character;
// makeChar({ head: { hw, egg, nTop, nBot, asym, rot } }) overrides any of it.
const SHAPE0 = { hw: 0.92, egg: -0.1, nTop: 1.8, nBot: 2.3, asym: 0.07, rot: -0.03, wob: [], ink: [] };
let SH = SHAPE0, SH_DIR = 1;
function headXY(cx, cy, R, a) {
  const ca = Math.cos(a), sa = Math.sin(a), n = sa > 0 ? SH.nBot : SH.nTop;
  let X = Math.sign(ca) * Math.pow(Math.abs(ca), 2 / n), Y = Math.sign(sa) * Math.pow(Math.abs(sa), 2 / n);
  X *= (1 + SH.egg * Y) * (1 + SH.asym * 0.8 * Math.sign(X) * SH_DIR);
  let w = 1; for (const [k, amp, ph] of SH.wob) w += amp * Math.cos(k * a + ph);
  const A = R * 1.04, B = A * SH.hw, x = A * X * w, y = B * Y * w, cr = Math.cos(SH.rot), sr = Math.sin(SH.rot);
  return [cx + x * cr - y * sr, cy + x * sr + y * cr];
}
function headPath(c, cx, cy, R) {
  c.beginPath();
  for (let i = 0; i <= 96; i++) { const [x, y] = headXY(cx, cy, R, (i / 96) * 6.2832); if (i) c.lineTo(x, y); else c.moveTo(x, y); }
  c.closePath();
}
export function headShapeFor(o) {
  let h = 2166136261 >>> 0;
  for (const ch of JSON.stringify([o.style, o.hair, o.shirt, o.R, o.build, o.role, o.acc])) h = Math.imul(h ^ ch.charCodeAt(0), 16777619) >>> 0;
  const r = rng(o.headSeed ?? h), L = (a, b) => a + (b - a) * r();
  return { hw: L(0.85, 1.0), egg: L(-0.17, -0.05), nTop: L(1.5, 2.0), nBot: L(2.05, 2.5), asym: L(0.04, 0.11), rot: L(-0.12, 0.05),
    wob: [3, 4, 5, 6].map((k) => [k, L(0.004, 0.009), L(0, 6.283)]), ink: [1, 2, 3].map((k) => [k, L(0.05, 0.14), L(0, 6.283)]) };
}
// Brush outline: a filled ring around the contour, about 3x thicker along the bottom curve (chin and jaw) than at the top,
// with a little uneven pressure per character (reference: thick/thin 2.9-3.5, thickest near 64 degrees).
function inkOutline(c, cx, cy, R) {
  const N = 120, P = [];
  for (let i = 0; i < N; i++) P.push(headXY(cx, cy, R, (i / N) * 6.2832));
  const out = [], inn = [];
  for (let i = 0; i < N; i++) {
    const a = P[(i + N - 1) % N], b = P[(i + 1) % N], q = P[i];
    let nx = b[1] - a[1], ny = -(b[0] - a[0]); const L = Math.hypot(nx, ny) || 1; nx /= L; ny /= L;
    if (nx * (q[0] - cx) + ny * (q[1] - cy) < 0) { nx = -nx; ny = -ny; }
    const th = Math.atan2(q[1] - cy, q[0] - cx);
    let f = 0.3 + 0.7 * Math.pow((1 + Math.cos(th - 1.45)) / 2, 1.1);   // heaviest along the whole bottom curve (chin and jaw), thin on top
    for (const [k, amp, ph] of SH.ink) f *= 1 + amp * Math.cos(k * th + ph);
    const w = R * 0.14 * f;
    out.push([q[0] + nx * w * 0.5, q[1] + ny * w * 0.5]); inn.push([q[0] - nx * w * 0.5, q[1] - ny * w * 0.5]);
  }
  c.fillStyle = INK; c.beginPath();
  out.forEach((q, i) => (i ? c.lineTo(q[0], q[1]) : c.moveTo(q[0], q[1]))); c.closePath();
  for (let i = N - 1; i >= 0; i--) { const q = inn[i]; if (i === N - 1) c.moveTo(q[0], q[1]); else c.lineTo(q[0], q[1]); }
  c.closePath(); c.fill();
}                 // outline / limb colour: dark brown ink, not pure black
const INK_HEX = 0x2b1a12, EYE = '#25160f', MOUTH = '#4a1810', TONGUE = '#c9566a';

// eo eye open, lid upper lid, sq squint (> shape), pup pupil size, px/py pupil offset, ba brow angle (+ = angry, inner
// end down) / by brow height, mw/mc/mo mouth width/curve/open, mt teeth, mg clenched teeth, ms smirk, mr round "o", sw sweat
// Eyes: eo < 0.9 = solid dark almond eyes (lid cuts the top); eo >= 0.9 = round white eyes with a pupil (surprise).
export const PRE = {
  smug: { eo: 0.62, lid: 0.50, sq: 0, pup: 1.0, px: 0.75, py: -0.3, ba: 0.12, by: 0.02, mw: 0.26, mc: 0.10, mo: 0, mt: 0, mg: 0, ms: 1.0, mr: 0, sw: 0 },
  grit: { eo: 0.55, lid: 0.38, sq: 0, pup: 0.9, px: 0.3, py: 0.2, ba: 0.55, by: -0.05, mw: 0.40, mc: 0.02, mo: 0.30, mt: 1, mg: 1, ms: 0, mr: 0, sw: 0 },
  grin: { eo: 0.60, lid: 0.45, sq: 0, pup: 1.0, px: -0.2, py: 0.1, ba: 0.42, by: 0.0, mw: 0.52, mc: 0.34, mo: 0.30, mt: 1, mg: 0, ms: 0, mr: 0, sw: 0 },
  jolt: { eo: 0.5, lid: 0, sq: 1, pup: 1, px: 0, py: 0, ba: -0.3, by: 0.06, mw: 0.30, mc: 0.05, mo: 0.42, mt: 0, mg: 0, ms: 0, mr: 0, sw: 0 },
  calm: { eo: 0.70, lid: 0.22, sq: 0, pup: 1.0, px: 0.0, py: 0.25, ba: -0.05, by: 0.04, mw: 0.16, mc: 0.02, mo: 0, mt: 0, mg: 0, ms: 0, mr: 0, sw: 0 },
  shock: { eo: 1.25, lid: 0, sq: 0, pup: 0.55, px: 0, py: 0, ba: -0.35, by: 0.14, mw: 0.14, mc: 0, mo: 0.35, mt: 0, mg: 0, ms: 0, mr: 1, sw: 1 },
  dazed: { eo: 0.5, lid: 0, sq: 1, pup: 1, px: 0, py: 0, ba: -0.45, by: 0.05, mw: 0.22, mc: -0.12, mo: 0, mt: 0, mg: 0, ms: 0.6, mr: 0, sw: 1 },
  flat: { eo: 0.62, lid: 0.42, sq: 0, pup: 0.9, px: 0, py: 0.1, ba: 0, by: 0, mw: 0.18, mc: 0, mo: 0, mt: 0, mg: 0, ms: 0, mr: 0, sw: 0 },     // the quiet victim
  pain: { eo: 0.5, lid: 0, sq: 1, pup: 1, px: 0, py: 0, ba: -0.5, by: 0.08, mw: 0.34, mc: -0.18, mo: 0.2, mt: 1, mg: 1, ms: 0, mr: 0, sw: 1 },   // fake injury
  innocent: { eo: 0.95, lid: 0, sq: 0, pup: 1.1, px: 0, py: -0.6, ba: -0.25, by: 0.12, mw: 0.12, mc: 0.08, mo: 0, mt: 0, mg: 0, ms: 0, mr: 0, sw: 0 },
  stern: { eo: 0.55, lid: 0.45, sq: 0, pup: 0.85, px: 0, py: 0, ba: 0.5, by: -0.06, mw: 0.22, mc: -0.06, mo: 0, mt: 0, mg: 0, ms: 0, mr: 0, sw: 0 },
  worried: { eo: 0.85, lid: 0, sq: 0, pup: 0.8, px: 0, py: 0, ba: -0.4, by: 0.1, mw: 0.2, mc: -0.12, mo: 0, mt: 0, mg: 0, ms: 0, mr: 0, sw: 1 },
  talk: { eo: 0.65, lid: 0.3, sq: 0, pup: 1, px: 0, py: 0, ba: 0.1, by: 0, mw: 0.24, mc: 0.04, mo: 0.32, mt: 0, mg: 0, ms: 0, mr: 0, sw: 0 },
};
export function blend(a, b, u) { const o = {}; for (const k in a) o[k] = lerp(a[k], b[k], u); return o; }
export function exprAt(keys, t, o = {}) { // keys: [[t, name], ...]; o.blink: false turns the automatic blinks off
  let i = 0; while (i < keys.length - 1 && keys[i + 1][0] <= t) i++;
  let e = i === 0 ? PRE[keys[0][1]] : blend(PRE[keys[i - 1][1]], PRE[keys[i][1]], ease(keys[i][0], keys[i][0] + 0.13, t));
  // expression change: the head does a quick bounce (pose() reads e.pop, 0..1 over 0.35 s); o.pop: false turns it off
  if (i > 0 && o.pop !== false && t - keys[i][0] >= 0 && t - keys[i][0] < 0.35) e = { ...e, pop: (t - keys[i][0]) / 0.35 };
  if (o.blink === false || e.sq > 0.5) return e;
  const bl = blinkAt(keys, t);
  return bl > 0 ? { ...e, bl } : e;
}
// Blinks as measured on the reference shorts: every 0.5-2.3 s (seeded per character from its expression keys), 4 frames
// shaped half / shut / shut / half, plus one blink across every expression change.
const BLINK = [0.5, 1, 1, 0.5];
function blinkAt(keys, t) {
  for (let k = 1; k < keys.length; k++) { const f = Math.floor((t - keys[k][0]) * 30) + 1; if (f >= 0 && f < 4) return BLINK[f]; }
  let h = 7; for (const [kt, nm] of keys) { h = (h * 31 + Math.round(kt * 100)) >>> 0; for (const ch of String(nm)) h = (h * 31 + ch.charCodeAt(0)) >>> 0; }
  const r = rng(h); let b = 0.3 + r() * 1.6, last = -9;
  while (b <= t) { last = b; b += 0.5 + 1.8 * r(); }
  const f = Math.floor((t - last) * 30); return f >= 0 && f < 4 ? BLINK[f] : 0;
}
// Lip-sync, anime style: the mouth snaps between shapes (no easing) about 4 times a second (one per syllable; 7 read as
// chattering on close-ups) while a word is spoken, shape picked from the word's vowels (a: open D with top teeth, e/i/y: gritted
// teeth, o/u: small o), shut briefly between flaps.
// words: [{ w, s, e }] (only the spoken lines). Eyes and brows stay from `base`.
const VIS = {
  A: { mo: 0.36, mw: 0.22, mc: 0.04, mt: 1, mg: 0, mr: 0, ms: 0 },   // open "D", top teeth and tongue
  E: { mo: 0.26, mw: 0.25, mc: 0.0, mt: 1, mg: 1, mr: 0, ms: 0 },    // gritted teeth, both rows (the reference's favourite)
  O: { mo: 0.06, mw: 0.12, mc: 0, mt: 0, mg: 0, mr: 1, ms: 0 },      // small "o" with tongue
};
export function talkAt(base, words, t, o = {}) {   // o.rate: mouth shapes per second (default 4, about one per syllable)
  const w = words.find((w) => t >= w.s && t < w.e); if (!w) return base;
  const dur = Math.max(0.08, w.e - w.s), n = Math.max(1, Math.round(dur * (o.rate ?? 4))), u = ((t - w.s) / dur) * n, i = Math.floor(u), ph = u - i;
  if (ph > 0.78) return { ...base, mo: 0, mr: 0, mt: 0, mg: 0, mw: Math.min(base.mw, 0.2), ms: 0 };
  const vow = String(w.w).toLowerCase().replace(/[^aeiouy]/g, '') || 'a', ch = vow[i % vow.length];
  return { ...base, ...VIS[ch === 'o' || ch === 'u' ? 'O' : ch === 'e' || ch === 'i' || ch === 'y' ? 'E' : 'A'] };
}

// ------------------------------------------------------------------ painted hair
// paintCap: hair over the top of the head with a hairline that dips at the temples, a fringe of pointed locks, darker
// strand strokes and a few light highlight strokes. back (0..1) lowers the hairline when seen from behind.
function shade(hex, k) { const c = new THREE.Color(hex); if (k < 0) c.lerp(new THREE.Color(0x000000), -k); else c.lerp(new THREE.Color(0xffffff), k); return '#' + c.getHexString(); }
function paintCap(c, cx, cy, R, o, back, opt = {}) {
  // The hairline is centred on the FACE (it turns with the head): the forehead stays high above the eyes and the dip
  // toward the temples falls on the far side, over the back of the head. It never comes below the brows over the face.
  const k = opt.k ?? 1, tips = opt.tips ?? 7, fr = opt.fringe ?? 1, sh = o.ox * R * 0.5 + (opt.part ?? 0) * R * 0.15;
  const fy0 = cy - R * (0.4 * k) + back * R * 1.35, drop = R * (opt.drop ?? 0.5) * (1 - back * 0.6);
  const fxF = cx + o.ox * R * 0.52, browCap = cy + R * 0.10 - o.oy * R * 0.45 - R * 0.36, faceVis = clamp((o.front + 0.2) / 0.3);
  const yAt = (x) => { const y = fy0 + drop * Math.min(1.3, ((x - (cx + sh)) / R) ** 2), inFace = clamp(1 - Math.abs(x - fxF) / (R * 0.62));
    return lerp(y, Math.min(y, browCap), inFace * faceVis); };
  const x0 = cx - R * 1.08, x1 = cx + R * 1.08, top = cy - R * 1.3;
  c.fillStyle = o.hair; c.beginPath(); c.moveTo(x0 - R * 0.2, top); c.lineTo(x0 - R * 0.2, yAt(x0));
  for (let i = 0; i < tips; i++) {
    const a = x0 + (x1 - x0) * (i / tips), b = x0 + (x1 - x0) * ((i + 1) / tips), m = (a + b) / 2 + (opt.sweep ?? 0) * R * 0.06;
    c.lineTo(a, yAt(a) - R * 0.02); c.quadraticCurveTo(m - R * 0.02, yAt(m) + R * 0.05 * fr, m + R * 0.015, yAt(m) + R * 0.13 * fr); c.quadraticCurveTo(m + R * 0.03, yAt(b), b, yAt(b) - R * 0.02);
  }
  c.lineTo(x1 + R * 0.2, yAt(x1)); c.lineTo(x1 + R * 0.2, top); c.closePath(); c.fill();
  { const hg = c.createRadialGradient(cx - R * 0.35 + sh * 0.5, cy - R * 0.85, R * 0.05, cx, cy - R * 0.5, R * 1.1); hg.addColorStop(0, 'rgba(255,255,255,0.32)'); hg.addColorStop(0.55, 'rgba(255,255,255,0.08)'); hg.addColorStop(1, 'rgba(0,0,0,0.12)');
    c.save(); c.clip(); c.fillStyle = hg; c.fillRect(cx - R * 1.4, cy - R * 1.4, R * 2.8, R * 2.8); c.restore(); }
  if (opt.strands !== false) {
    c.strokeStyle = o.hair2; c.lineWidth = R * 0.026; c.globalAlpha = 0.85;
    for (let i = 0; i < tips; i++) { const m = x0 + (x1 - x0) * ((i + 0.5) / tips); c.beginPath(); c.moveTo(cx + sh * 0.5 + (m - cx) * 0.35, cy - R * 0.98); c.quadraticCurveTo(cx + sh + (m - cx) * 0.85, yAt(m) - R * 0.25, m + R * 0.01, yAt(m) + R * 0.08 * fr); c.stroke(); }
    c.strokeStyle = shade(o.hair, 0.35); c.lineWidth = R * 0.022; c.globalAlpha = 0.55;
    for (let i = -1; i <= 1; i++) { c.beginPath(); c.arc(cx + sh * 0.6 + i * R * 0.22, cy - R * 0.62 + back * R * 0.5, R * 0.2, Math.PI * 1.1, Math.PI * 1.55); c.stroke(); }
    c.globalAlpha = 1;
  }
}
// hairMass: hair as the reference shorts draw it. One solid shape in flat colour that hugs the top of the skull (a little
// volume above it), comes down the sides to about eye level, and carries its own thick ink outline, the fringe edge
// included. The fringe is one clean shape per style (side swoop, centre-part curtains, straight bowl, a few big locks),
// with 3-5 thin strand lines following the flow from the part. It turns with the face, covers more of the head on the
// far side, never comes below the brows, and covers the whole top when seen from behind.
//   st: { kind: 'swoop'|'part'|'bowl'|'locks'|'spiky'|'curly'|'buzz'|'flat', vol, side, fore, part, locks, strands }
function hpt(cx, cy, R, a) { return headXY(cx, cy, R, a); }
function sideAngle(R, yOff) { // angle below (+) or above (-) the horizontal where the head edge sits at cy + yOff
  return yOff >= 0 ? Math.asin(Math.min(0.95, Math.pow(yOff / (0.93 * R), 2.55 / 2))) : -Math.asin(Math.min(0.95, Math.pow(-yOff / (0.98 * R), 1.1)));
}
function hairMass(c, cx, cy, R, o, back, st) {
  const ox = o.ox || 0, near = ox >= 0 ? 1 : -1, kind = st.kind || 'swoop';
  const fx = cx + ox * R * 0.52, browCap = cy + R * 0.10 - (o.oy || 0) * R * 0.45 - R * 0.62, faceVis = clamp((o.front + 0.2) / 0.3);
  // sideburn depth: the face side stops near eye level, the far side (back of the head) comes lower
  const sideN = R * (st.side ?? 0.05) + back * R * 0.35, sideF = R * (st.side ?? 0.05) + Math.abs(ox) * R * 0.32 + back * R * 0.35;
  const yR = Math.min(R * 0.42, near > 0 ? sideN : sideF), yL = Math.min(R * 0.42, near > 0 ? sideF : sideN);
  const aL = Math.PI - sideAngle(R, yL), aR = 2 * Math.PI + sideAngle(R, yR);
  const vol = st.vol ?? 0.06, out = [];
  for (let i = 0; i <= 64; i++) {
    const a = aL + (aR - aL) * (i / 64), up = Math.max(0, -Math.sin(a));
    let f = 1.035 + vol * Math.pow(up, 1.6);
    if (kind === 'curly') f += 0.055 * Math.pow(Math.abs(Math.sin(a * 7.5)), 0.6) * (0.4 + 0.6 * up);
    if (kind === 'spiky') { const d = a - 1.5 * Math.PI; f += 0.3 * Math.pow(Math.max(0, Math.cos(d * 5.5)), 5) * clamp(1 - Math.abs(d) / 1.25); }
    const [px, py] = hpt(cx, cy, R, a);
    let x = cx + (px - cx) * f, y = cy + (py - cy) * f;
    if (kind === 'flat') y = Math.max(y, cy - R * 1.08);
    out.push([x, y]);
  }
  const xR = out[out.length - 1][0], xL = out[0][0], yEndR = out[out.length - 1][1], yEndL = out[0][1];
  const p = (st.part ?? 0) * near, fore = st.fore ?? 0.4;
  const foreAt = (u) => {   // u: across the forehead in head radii from the face centre (+ = toward the face side)
    const d = u - p;
    if (kind === 'swoop') return cy - R * fore + R * (st.amp ?? 0.36) * clamp((-d * near + 0.2) / 1.05) ** 0.9 - R * 0.06 * Math.exp(-(d * d) / 0.012);
    if (kind === 'part') return cy - R * fore - R * 0.08 * Math.exp(-(d * d) / 0.02) + R * 0.20 * clamp(Math.abs(d) / 0.75) ** 1.4;
    if (kind === 'bowl' || kind === 'flat') return cy - R * fore + R * 0.025 * Math.abs(Math.sin(u * 9));
    if (kind === 'locks' || kind === 'spiky') {
      const n = st.locks ?? 3, w = (u + 0.95) / 1.9 * n, ph = w - Math.floor(w);
      return cy - R * fore + R * (kind === 'spiky' ? 0.17 : 0.19) * (1 - Math.pow(Math.abs(ph - 0.5) * 2, kind === 'spiky' ? 0.7 : 1.3));
    }
    if (kind === 'curly') { const w = (u + 1) * 3.2; return cy - R * fore + R * 0.07 * Math.abs(Math.sin(w * Math.PI)); }
    return cy - R * fore;   // buzz
  };
  const inner = [];
  for (let i = 0; i <= 56; i++) {
    const x = xR + (xL - xR) * (i / 56), u = (x - fx) / R;
    const e = ease(0.5, 0.98, Math.abs(x - cx) / (R * 1.05)), yEdge = x > cx ? yEndR : yEndL;
    let y = lerp(foreAt(u), yEdge, e) + back * R * 1.25 * (1 - e);
    const inFace = clamp(1 - Math.abs(x - fx) / (R * 0.62));
    y = lerp(y, Math.min(y, browCap), inFace * faceVis);
    inner.push([x, y]);
  }
  const path = () => { c.beginPath(); c.moveTo(out[0][0], out[0][1]); for (const q of out) c.lineTo(q[0], q[1]); for (const q of inner) c.lineTo(q[0], q[1]); c.closePath(); };
  c.save();
  path(); c.fillStyle = o.hair; c.fill();
  // strands: thin lines in a lighter (dark hair) or darker (light hair) tone, flowing from the part / crown to the fringe
  if (st.strands !== false) {
    c.save(); path(); c.clip();
    const lum = new THREE.Color(o.hair).getHSL({}).l;
    c.strokeStyle = shade(o.hair, lum < 0.45 ? 0.2 : -0.22); c.lineWidth = R * 0.02; c.lineCap = 'round';
    const px0 = fx + p * R, py0 = cy - R * 0.92 + back * R * 0.6, n = st.strandN ?? 3;
    for (let k = 0; k < n; k++) {
      const v = (k + 0.5) / n, side = kind === 'part' ? (k % 2 ? 1 : -1) : -near * (kind === 'swoop' ? 1 : (k % 2 ? 1 : -1));
      const ex = px0 + side * R * (0.25 + 0.6 * v), ey = cy - R * (fore + 0.02) + R * 0.18 * v + back * R * 0.9;
      c.beginPath(); c.moveTo(px0 + side * R * 0.05 * v, py0 + R * 0.06);
      c.quadraticCurveTo(px0 + side * R * (0.18 + 0.55 * v), py0 + R * 0.05, ex, ey); c.stroke();
    }
    c.restore();
  }
  if (kind === 'curly') {   // curl marks
    c.save(); path(); c.clip(); c.strokeStyle = shade(o.hair, 0.28); c.lineWidth = R * 0.026;
    for (let i = 0; i < 12; i++) { const x = cx + ((i % 4) - 1.5) * R * 0.42 + (Math.floor(i / 4) % 2) * R * 0.2, y = cy - R * (1.0 - Math.floor(i / 4) * 0.2) + back * R * 0.5; c.beginPath(); c.arc(x, y, R * 0.08, 0.4, 4.0); c.stroke(); }
    c.restore();
  }
  if (kind === 'buzz') {    // short stubble dots
    c.save(); path(); c.clip(); c.fillStyle = shade(o.hair, -0.22);
    for (let i = 0; i < 70; i++) { const a = Math.PI * (1.02 + 0.96 * ((i * 0.618) % 1)), r = R * (0.62 + 0.36 * ((i * 0.37) % 1)); c.fillRect(cx + Math.cos(a) * r, cy + Math.sin(a) * r, R * 0.02, R * 0.02); }
    c.restore();
  }
  c.strokeStyle = INK; c.lineWidth = R * (kind === 'buzz' ? 0.05 : 0.06); c.lineJoin = 'round'; path(); c.stroke();
  if (st.cowlick && back < 0.8) {
    const bx = cx + (p * 0.6 - ox * 0.3) * R, by = cy - R * (0.96 + vol * 0.9), w = R * 0.13, dir = near;
    c.beginPath(); c.moveTo(bx - w, by + R * 0.08);
    c.bezierCurveTo(bx - w * 0.8, by - R * 0.2, bx + dir * R * 0.05, by - R * 0.3, bx + dir * R * 0.34, by - R * 0.2);   // a lock curling over (fits the head canvas)
    c.bezierCurveTo(bx + dir * R * 0.12, by - R * 0.18, bx + w * 0.5, by - R * 0.1, bx + w, by + R * 0.08); c.closePath();
    c.fillStyle = o.hair; c.fill(); c.stroke();
  }
  c.restore();
}
const inked = (c, R) => { c.strokeStyle = INK; c.lineWidth = R * 0.045; };
const outlineFill = (c) => { c.fill(); c.stroke(); };
export const HAIR = {
  none: {},
  bald: { cap(c, cx, cy, R) { c.fillStyle = 'rgba(255,255,255,0.7)'; c.beginPath(); c.ellipse(cx - R * 0.38, cy - R * 0.62, R * 0.2, R * 0.08, -0.5, 0, 7); c.fill(); } },
  buzz: { mass: { kind: 'buzz', vol: 0.0, side: -0.36, fore: 0.62, strands: false } },
  mess: { mass: { kind: 'part', vol: 0.15, side: -0.24, fore: 0.56, part: 0.05, cowlick: true, strandN: 2 } },
  bowl: { mass: { kind: 'bowl', vol: 0.13, side: -0.08, fore: 0.47, strandN: 3 } },
  side: { mass: { kind: 'swoop', vol: 0.15, side: -0.22, fore: 0.64, part: 0.42, amp: 0.24, strandN: 2 } },
  spiky: { mass: { kind: 'spiky', vol: 0.1, side: -0.3, fore: 0.6, locks: 5, strandN: 2 } },
  curly: { mass: { kind: 'curly', vol: 0.2, side: -0.2, fore: 0.56, strands: false } },
  afro: {
    behind(c, cx, cy, R, o) { c.beginPath(); c.arc(cx - o.ox * R * 0.2, cy - R * 0.22, R * 1.2, 0, 7); outlineFill(c); },
    mass: { kind: 'curly', vol: 0.34, side: -0.08, fore: 0.54, strands: false } },
  bun: {
    behind(c, cx, cy, R, o) { c.beginPath(); c.arc(cx - o.ox * R * 0.3, cy - R * 1.12, R * 0.27, 0, 7); outlineFill(c); },
    mass: { kind: 'part', vol: 0.07, side: -0.24, fore: 0.6, part: -0.1, strandN: 2 } },
  ponytail: {
    behind(c, cx, cy, R, o) { const sd = o.ox >= 0 ? -1 : 1; c.beginPath(); c.ellipse(cx + sd * R * 1.0, cy - R * 0.05, R * 0.2, R * 0.48, sd * -0.35, 0, 7); outlineFill(c); },
    mass: { kind: 'swoop', vol: 0.08, side: -0.2, fore: 0.6, part: -0.38, amp: 0.22, strandN: 2 } },
  long: {
    behind(c, cx, cy, R, o) { c.beginPath(); c.roundRect(cx - R * 1.14 - o.ox * R * 0.2, cy - R * 0.75, R * 2.28, R * 1.62, R * 0.5); outlineFill(c); },
    mass: { kind: 'part', vol: 0.1, side: 0.38, fore: 0.56, part: 0.12, strandN: 3 } },
  flattop: { mass: { kind: 'flat', vol: 0.26, side: -0.3, fore: 0.6, strandN: 2 } },
};
export const HAIR_STYLES = Object.keys(HAIR).filter((k) => k !== 'none');

// ------------------------------------------------------------------ accessories (drawn on the head canvas)
// acc entries: 'name' or 'name:#colour'. 'neckbrace' is a 3D collar. Face accessories only show from the front.
const face = (cx, cy, R, o) => ({ fx: cx + o.ox * R * 0.52, fy: cy + R * 0.10 - o.oy * R * 0.45, sq: 0.62 + 0.38 * clamp(o.front) });
export const ACC = {
  sunglasses(c, cx, cy, R, o, col = '#15151a') {
    if (o.front < 0) return; const { fx, fy, sq } = face(cx, cy, R, o), ey = fy - R * 0.08;
    c.fillStyle = col; inked(c, R);
    for (const s of [-1, 1]) { c.beginPath(); c.roundRect(fx + s * R * 0.31 * sq - R * 0.2 * sq, ey - R * 0.13, R * 0.4 * sq, R * 0.24, R * 0.08); outlineFill(c); }
    c.beginPath(); c.moveTo(fx - R * 0.11 * sq, ey - R * 0.05); c.lineTo(fx + R * 0.11 * sq, ey - R * 0.05); c.stroke();
    c.fillStyle = 'rgba(255,255,255,0.45)'; for (const s of [-1, 1]) c.fillRect(fx + s * R * 0.31 * sq - R * 0.1 * sq, ey - R * 0.09, R * 0.07, R * 0.05);
  },
  shadesUp(c, cx, cy, R, o, col = '#ffcf2e') {
    const x = cx - o.ox * R * 0.3, y = cy - R * 0.78; inked(c, R); c.fillStyle = '#1d1d24';
    for (const s of [-1, 1]) { c.beginPath(); c.ellipse(x + s * R * 0.27, y, R * 0.19, R * 0.12, 0, 0, 7); outlineFill(c); }
    c.strokeStyle = col; c.lineWidth = R * 0.05; c.beginPath(); c.moveTo(x - R * 0.08, y); c.lineTo(x + R * 0.08, y); c.stroke();
  },
  cap(c, cx, cy, R, o, col = '#d8342c') {
    const x = cx - o.ox * R * 0.35, y = cy - R * 0.58; c.fillStyle = col; inked(c, R);
    c.beginPath(); c.ellipse(x, y, R * 1.0, R * 0.56, 0, Math.PI, 0); c.closePath(); outlineFill(c);
    c.strokeStyle = shade(col, -0.35); c.lineWidth = R * 0.025; c.beginPath(); c.moveTo(x, y - R * 0.55); c.lineTo(x, y); c.stroke();
    const fr = o.front > 0.3, bx = x + (fr ? 0 : o.ox * R * 0.6); inked(c, R); c.fillStyle = shade(col, -0.15);
    c.beginPath(); c.ellipse(bx, y + R * 0.02, R * (fr ? 0.82 : 0.6), R * 0.12, 0, 0, 7); outlineFill(c);
  },
  ranger(c, cx, cy, R, o, col = '#8a6a3a') {
    const x = cx - o.ox * R * 0.3, y = cy - R * 0.62; c.fillStyle = col; inked(c, R);
    c.beginPath(); c.ellipse(x, y, R * 1.34, R * 0.22, 0, 0, 7); outlineFill(c);
    c.beginPath(); c.moveTo(x - R * 0.55, y); c.lineTo(x - R * 0.42, y - R * 0.5); c.lineTo(x, y - R * 0.38); c.lineTo(x + R * 0.42, y - R * 0.5); c.lineTo(x + R * 0.55, y); c.closePath(); outlineFill(c);
    c.fillStyle = '#3a2a16'; c.fillRect(x - R * 0.55, y - R * 0.1, R * 1.1, R * 0.08);
  },
  beanie(c, cx, cy, R, o, col = '#2f7de0') {
    const x = cx - o.ox * R * 0.3; c.fillStyle = col; inked(c, R);
    c.beginPath(); c.arc(x, cy - R * 0.38, R * 0.95, Math.PI * 1.05, Math.PI * 1.95); c.closePath(); outlineFill(c);
    c.fillStyle = shade(col, -0.15); c.beginPath(); c.roundRect(x - R * 0.98, cy - R * 0.5, R * 1.96, R * 0.24, R * 0.08); outlineFill(c);
    c.strokeStyle = shade(col, -0.35); c.lineWidth = R * 0.02; for (let i = -4; i <= 4; i++) { c.beginPath(); c.moveTo(x + i * R * 0.2, cy - R * 0.48); c.lineTo(x + i * R * 0.2, cy - R * 0.28); c.stroke(); }
    inked(c, R); c.fillStyle = col; c.beginPath(); c.arc(x, cy - R * 1.3, R * 0.14, 0, 7); outlineFill(c);
  },
  headset(c, cx, cy, R, o, col = '#222') {
    c.strokeStyle = col; c.lineWidth = R * 0.07; c.beginPath(); c.arc(cx, cy - R * 0.05, R * 1.02, Math.PI * 1.1, Math.PI * 1.9); c.stroke();
    const s = o.ox >= 0 ? -1 : 1; c.fillStyle = col; c.beginPath(); c.ellipse(cx + s * R * 0.95, cy, R * 0.14, R * 0.22, 0, 0, 7); c.fill();
    if (o.front > 0) { const { fx, fy } = face(cx, cy, R, o); c.lineWidth = R * 0.035; c.beginPath(); c.moveTo(cx + s * R * 0.95, cy + R * 0.1); c.quadraticCurveTo(cx + s * R * 0.7, fy + R * 0.45, fx + s * R * 0.25, fy + R * 0.42); c.stroke(); c.beginPath(); c.arc(fx + s * R * 0.25, fy + R * 0.42, R * 0.05, 0, 7); c.fill(); }
  },
  mustache(c, cx, cy, R, o, col) {
    if (o.front < 0) return; const { fx, fy, sq } = face(cx, cy, R, o); c.fillStyle = col || o.hair; inked(c, R); c.lineWidth = R * 0.03;
    const m0 = fy + R * 0.16;   // just above the mouth
    c.beginPath(); c.moveTo(fx, m0); c.quadraticCurveTo(fx - R * 0.2 * sq, m0 - R * 0.06, fx - R * 0.3 * sq, m0 + R * 0.09); c.quadraticCurveTo(fx - R * 0.12 * sq, m0 + R * 0.06, fx, m0 + R * 0.06);
    c.quadraticCurveTo(fx + R * 0.12 * sq, m0 + R * 0.06, fx + R * 0.3 * sq, m0 + R * 0.09); c.quadraticCurveTo(fx + R * 0.2 * sq, m0 - R * 0.06, fx, m0); outlineFill(c);
  },
  beard(c, cx, cy, R, o, col) {
    if (o.front < -0.1) return; const { fx, fy, sq } = face(cx, cy, R, o); c.save(); headPath(c, cx, cy, R); c.clip(); c.fillStyle = col || o.hair;
    c.beginPath(); c.moveTo(fx - R * 0.5 * sq, fy + R * 0.3); c.quadraticCurveTo(fx - R * 0.45 * sq, fy + R * 0.95, fx, fy + R * 0.98); c.quadraticCurveTo(fx + R * 0.45 * sq, fy + R * 0.95, fx + R * 0.5 * sq, fy + R * 0.3);
    c.quadraticCurveTo(fx + R * 0.26 * sq, fy + R * 0.6, fx, fy + R * 0.58); c.quadraticCurveTo(fx - R * 0.26 * sq, fy + R * 0.6, fx - R * 0.5 * sq, fy + R * 0.3); c.fill();
    c.strokeStyle = INK; c.lineWidth = R * 0.032; c.lineJoin = 'round'; c.stroke();   // thin ink outline (reference)
    c.strokeStyle = o.hair2 || shade(col || o.hair, -0.3); c.lineWidth = R * 0.02; for (let i = -3; i <= 3; i++) { c.beginPath(); c.moveTo(fx + i * R * 0.14 * sq, fy + R * 0.62); c.lineTo(fx + i * R * 0.12 * sq, fy + R * 0.85); c.stroke(); }
    c.restore();
  },
  bandage(c, cx, cy, R, o) {
    if (o.front < 0) return; const { fx, fy } = face(cx, cy, R, o); c.save(); c.translate(fx + R * 0.32, fy - R * 0.48); c.rotate(-0.5);
    c.fillStyle = '#f3d6b0'; inked(c, R); c.lineWidth = R * 0.03; c.beginPath(); c.roundRect(-R * 0.22, -R * 0.07, R * 0.44, R * 0.14, R * 0.05); outlineFill(c); c.restore();
  },
  blush(c, cx, cy, R, o) {
    if (o.front < 0.2) return; const { fx, fy, sq } = face(cx, cy, R, o); c.fillStyle = 'rgba(255,110,130,0.32)';
    for (const s of [-1, 1]) { c.beginPath(); c.ellipse(fx + s * R * 0.42 * sq, fy + R * 0.18, R * 0.12, R * 0.07, 0, 0, 7); c.fill(); }
  },
};
export const ACC_NAMES = [...Object.keys(ACC), 'neckbrace'];
function accDrawer(list) {
  const items = list.map((a) => { const [k, col] = String(a).split(':'); return [ACC[k], col]; }).filter(([f]) => f);
  return items.length ? (c, S, R, cx, cy, front, o) => { for (const [f, col] of items) f(c, cx, cy, R, o, col); } : null;
}

// ------------------------------------------------------------------ ready-made poses
// All return a pose for ch.pose(p, camera), in the character's parent space, character standing at (x, 0, z)
// facing +x of that space unless `face` says otherwise. Sizes scale with the head radius (designed at R = 0.2).
// arms: 'down' | 'hips' | 'wave' | 'up' | 'point' | 'neck' | 'phone' | 'cross' | 'shrug', or [left, right].
// target: point for 'point' (parent space). walk: phase in radians (legs and arms swing), or undefined.
// Arm reach (reference: an arm is a little longer than the torso, a leg a little longer than an arm)
const ARM = {   // control point = where the arm bends out of the top of the body; it leaves the outline right under the head
  down: (k, s, sh, hip) => [V3(0.03 * k, sh.y - 0.16 * k, s * 0.25 * k), V3(0.04 * k, hip.y - 0.17 * k, s * 0.28 * k)],   // out through the side outline near the top, then straight down
  hips: (k, s, sh, hip) => [V3(-0.05 * k, sh.y - 0.12 * k, s * 0.36 * k), V3(0.0, hip.y + 0.05 * k, s * 0.2 * k)],
  wave: (k, s, sh) => [V3(0.04 * k, sh.y + 0.04 * k, s * 0.4 * k), V3(0.05 * k, sh.y + 0.4 * k, s * 0.42 * k)],
  up: (k, s, sh) => [V3(0.02 * k, sh.y + 0.15 * k, s * 0.28 * k), V3(0.03 * k, sh.y + 0.52 * k, s * 0.21 * k)],
  neck: (k, s, sh) => [V3(0.18 * k, sh.y - 0.14 * k, s * 0.24 * k), V3(0.04 * k, sh.y + 0.02 * k, s * 0.1 * k)],
  phone: (k, s, sh, hip, R) => [V3(0.16 * k, sh.y - 0.14 * k, s * 0.26 * k), V3(0.02 * k, sh.y + R * 0.75, s * R * 1.0)],
  cross: (k, s, sh) => [V3(0.2 * k, sh.y - 0.16 * k, s * 0.22 * k), V3(0.14 * k, sh.y - 0.14 * k, -s * 0.12 * k)],
  shrug: (k, s, sh) => [V3(0.04 * k, sh.y - 0.16 * k, s * 0.34 * k), V3(0.14 * k, sh.y - 0.02 * k, s * 0.46 * k)],
};
export function stand(ch, o = {}) {
  const k = ch.R / 0.2, x = o.x || 0, z = o.z || 0, lean = o.lean || 0, legs = (ch.opts.legs || 1);
  const hip = V3(x, 0.64 * k * legs + (o.bob || 0), z);
  const neck = hip.clone().add(V3(Math.sin(lean) * 0.36 * k * (ch.opts.torso || 1), Math.cos(lean) * 0.36 * k * (ch.opts.torso || 1), 0));
  const sh = neck.clone(); sh.y -= ch.R * 0.12;
  const modes = Array.isArray(o.arms) ? o.arms : [o.arms || 'down', o.arms || 'down'];
  const arms = modes.map((m, i) => {
    const s = i ? 1 : -1;
    if (m === 'point') { const tg = (o.target || V3(x + 2, sh.y, z)).clone(); const d = tg.sub(sh).normalize(); return [sh.clone().addScaledVector(d, 0.27 * k).add(V3(0, -0.04 * k, s * 0.05 * k)), sh.clone().addScaledVector(d, 0.56 * k)]; }
    const r = (ARM[m] || ARM.down)(k, s, sh, hip, ch.R).map((v) => v.add(V3(x, 0, z)).setY(v.y));
    if (o.walk !== undefined && m === 'down') { const w = Math.sin(o.walk + (i ? Math.PI : 0)) * 0.1 * k; r[0].x += w * 0.5; r[1].x += w; }
    return r;
  });
  const legsP = [-1, 1].map((s, i) => {
    const sw = o.walk !== undefined ? Math.sin(o.walk + (i ? 0 : Math.PI)) * 0.12 * k : 0, lift = o.walk !== undefined ? Math.max(0, Math.cos(o.walk + (i ? 0 : Math.PI))) * 0.05 * k : 0;
    return [V3(x + sw * 0.5, hip.y * 0.5 + lift, z + s * 0.09 * k), V3(x + sw, 0.03 * k + lift, z + s * 0.1 * k)];
  });
  return { hip, neck, face: o.face || V3(1, 0, 0), expr: o.expr || PRE.calm, arms, legs: legsP };
}
// Seated driver (or passenger, side = 1) in a car built with addInterior(car, I): hands on the wheel rim.
export function sit(ch, I, rig, o = {}) {
  const side = o.side || -1, z = side * I.seatZ, lean = o.lean ?? 0.1, k = ch.R / 0.2;
  const hip = V3(I.seatX - 0.05, I.seatY + 0.13, z);
  const neck = hip.clone().add(V3(Math.sin(lean) * 0.3 * k, Math.cos(lean) * 0.3 * k, 0));
  let arms;
  if (side < 0 && rig && !o.arms) { const a = o.grip ?? 0.55; arms = [[V3(hip.x + 0.3, hip.y + 0.09, z - 0.22), rig.rimPoint(Math.PI - a)], [V3(hip.x + 0.3, hip.y + 0.09, z + 0.22), rig.rimPoint(a)]]; }
  else { const st = stand(ch, { arms: o.arms || 'down', target: o.target }); const d = neck.clone().sub(st.neck); arms = st.arms.map(([c, h]) => [c.add(d), h.add(d)]); }
  const fx = I.fireX - 0.22, fy = I.floorY + 0.07;
  const legs = [-1, 1].map((s) => [V3(hip.x + 0.56, hip.y + 0.08, z + s * 0.09), V3(fx, fy, z + s * 0.1)]);
  return { hip, neck, face: o.face || V3(1, 0, 0), expr: o.expr || PRE.calm, arms, legs };
}
// Seated on a chair, sofa, bed or bench: sitOn(ch, { x, z, seat: seat height, arms, target, lean, face, expr })
// Faces +x of the parent space like stand(); rotate the character (rotation.y = -PI/2 faces +z).
export function sitOn(ch, o = {}) {
  const k = ch.R / 0.2, x = o.x || 0, z = o.z || 0, seat = o.seat ?? 0.33, lean = o.lean ?? 0.05;
  const hip = V3(x, seat + 0.06 * k, z), neck = hip.clone().add(V3(Math.sin(lean) * 0.34 * k * (ch.opts.torso || 1), Math.cos(lean) * 0.34 * k * (ch.opts.torso || 1), 0));
  const st = stand(ch, { arms: o.arms || 'down', target: o.target }); const dv = neck.clone().sub(st.neck);
  const arms = st.arms.map(([c, h]) => [c.add(dv), h.add(dv)]);
  const modes = Array.isArray(o.arms) ? o.arms : [o.arms || 'down', o.arms || 'down'];
  arms.forEach((a, i) => { if (modes[i] === 'down') { a[1].x += 0.16 * k; a[1].y = Math.max(a[1].y, seat + 0.1 * k); } });
  const legs = [-1, 1].map((s) => [V3(x + 0.3 * k, seat + 0.04 * k, z + s * 0.09 * k), V3(x + 0.3 * k, 0.03 * k, z + s * 0.11 * k)]);
  return { hip, neck, face: o.face || V3(1, 0, 0), expr: o.expr || PRE.calm, arms, legs };
}

// ------------------------------------------------------------------ the head
// The face circle fills HEAD_FRAC of the square head canvas; the rest is room for hair, hats and buns above the skull.
// Anything drawn past the canvas edge is cut flat, so makeChar() checks the edges (g.clipped) and film.mjs check FAILs it.
export const HEAD_FRAC = 0.6;
function drawHead(c, S, o, e) {
  const cx = S / 2, cy = S / 2, R = S * HEAD_FRAC / 2, TAU = 6.2832;
  c.clearRect(0, 0, S, S); c.lineCap = 'round'; c.lineJoin = 'round';
  SH = o.shape || SHAPE0; SH_DIR = clamp((o.ox || 0) * 4, -1, 1) || 1;
  const front = o.front, back = clamp((0.35 - front) / 1.1);
  const HS = HAIR[o.style] || HAIR.mess;
  // ear, behind the head on the side away from the face
  if (Math.abs(o.ox) > 0.12 && front > -0.35) {
    const s = o.ox > 0 ? -1 : 1, ex = cx + s * R * 0.96, ey = cy + R * 0.12;
    c.fillStyle = SKIN_SHADE; c.strokeStyle = INK; c.lineWidth = R * 0.05; c.beginPath(); c.ellipse(ex + s * R * 0.06, ey, R * 0.12, R * 0.16, 0, 0, TAU); c.fill(); c.stroke();
    c.lineWidth = R * 0.025; c.beginPath(); c.arc(ex - s * R * 0.01, ey, R * 0.07, s > 0 ? -1.2 : 1.9, s > 0 ? 1.2 : 4.3); c.stroke();
  }
  if (HS.behind) { c.fillStyle = o.hair; c.strokeStyle = INK; c.lineWidth = R * 0.045; HS.behind(c, cx, cy, R, o, back); }
  // head: soft painted shading, light from the upper left
  const g = c.createRadialGradient(cx - R * 0.3, cy - R * 0.36, R * 0.15, cx + R * 0.05, cy + R * 0.05, R * 1.12);
  g.addColorStop(0, '#fffdf8'); g.addColorStop(0.6, SKIN); g.addColorStop(1, SKIN_SHADE);
  c.fillStyle = g; headPath(c, cx, cy, R); c.fill();
  c.save(); headPath(c, cx, cy, R); c.clip();
  if (HS.cap && !HS.mass) HS.cap(c, cx, cy, R, o, back);
  if (front > -0.2) {
    const vis = ease(-0.2, 0.05, front), sq = 0.62 + 0.38 * clamp(front);
    const fx = cx + o.ox * R * 0.52, fy = cy + R * 0.10 - o.oy * R * 0.45;
    c.globalAlpha = vis; c.strokeStyle = INK; c.fillStyle = EYE;
    const ey = fy - R * 0.08;
    for (const s of [-1, 1]) {
      const ex = fx + s * R * 0.275 * sq;
      let browBase;
      if ((e.bl || 0) > 0.75 && e.sq <= 0.5) {   // blink: a soft closed lid (not the squeezed-shut face)
        c.strokeStyle = EYE; c.lineWidth = R * 0.045; const rx = R * 0.085 * sq;
        c.beginPath(); c.moveTo(ex - rx, ey - R * 0.005); c.quadraticCurveTo(ex, ey + R * 0.045, ex + rx, ey - R * 0.005); c.stroke();
        browBase = ey - R * 0.13;
      } else if (e.sq > 0.5) {         // squeezed shut: a heavy curved lid with a crease line under it
        c.strokeStyle = EYE; c.lineWidth = R * 0.055; const rx = R * 0.1 * sq;
        c.beginPath(); c.moveTo(ex - rx, ey + R * 0.02); c.quadraticCurveTo(ex, ey - R * 0.07, ex + rx, ey + R * 0.02); c.stroke();
        c.lineWidth = R * 0.025; c.beginPath(); c.moveTo(ex - rx * 0.6, ey + R * 0.075); c.quadraticCurveTo(ex, ey + R * 0.045, ex + rx * 0.6, ey + R * 0.075); c.stroke();
        browBase = ey - R * 0.12;
      } else if (e.eo >= 0.9 && !(e.bl > 0)) { // shock: big round white eyes, nearly touching, small dot pupils, no catch-light
        const rr = R * 0.235 * Math.min(1.1, 0.85 + 0.15 * e.eo) * (0.8 + 0.2 * sq);
        c.fillStyle = '#ffffff'; c.beginPath(); c.arc(ex, ey, rr, 0, TAU); c.fill();
        c.strokeStyle = INK; c.lineWidth = R * 0.04; c.stroke();
        c.fillStyle = EYE; c.beginPath(); c.arc(ex + e.px * rr * 0.35, ey + e.py * rr * 0.35, R * 0.065 * e.pup, 0, TAU); c.fill();
        browBase = ey - rr - R * 0.12;
      } else {
        const ox = e.px * R * 0.03, oy = e.py * R * 0.025, ecx = ex + ox, ecy = ey + oy;
        const lid = clamp(Math.max(e.lid, (e.bl || 0) > 0 ? 0.62 : 0));
        if (lid > 0.28) {       // deadpan: a straight lid line with a dark half-disc under it (the reference's default look)
          // reference: the lid line is 2-2.5x the dot's width and runs well past it on the OUTER side; the dot is a small
          // half-disc hanging under the inner part of the line
          const rx = R * 0.125 * sq, ry = R * 0.165 * (1.1 - 0.3 * (lid - 0.28) / 0.72), lidY = ecy - R * 0.05, tilt = s * e.ba * R * 0.05;
          const li = ecx - s * R * 0.15 * sq, lo = ecx + s * R * 0.27 * sq, dcx = ecx - s * R * 0.02 * sq;   // inner end, outer end, dot centre
          const yAt = (x) => lidY + tilt * (x - ecx) / (R * 0.19);
          c.save(); c.beginPath(); c.moveTo(li - s * R * 0.05, yAt(li) ); c.lineTo(lo, yAt(lo)); c.lineTo(lo, ecy + R); c.lineTo(li - s * R * 0.05, ecy + R); c.closePath(); c.clip();
          c.fillStyle = EYE; c.beginPath(); c.ellipse(dcx, yAt(dcx), rx, ry, 0, 0, TAU); c.fill(); c.restore();
          c.strokeStyle = EYE; c.lineWidth = R * 0.062; c.lineCap = 'round';
          c.beginPath(); c.moveTo(li, yAt(li)); c.lineTo(lo, yAt(lo)); c.stroke();
          browBase = lidY - R * 0.22;
        } else {                // plain dot eyes: solid dark vertical ovals
          const rx = R * 0.095 * sq, ry = R * 0.14 * clamp(e.eo / 0.7, 0.35, 1.25);
          c.fillStyle = EYE; c.beginPath(); c.ellipse(ecx, ecy, rx, ry, 0, 0, TAU); c.fill();
          browBase = ecy - ry - R * 0.16;
        }
      }
      // tapered painted brow (thick at the inner end); ba > 0 = angry (inner end low)
      const bY = Math.min(browBase, ey - R * 0.36) - e.by * R, sl = R * 0.12 * Math.tan(e.ba), xi = ex - s * R * 0.16, xo = ex + s * R * 0.2;
      c.fillStyle = EYE; c.beginPath();
      c.moveTo(xi, bY + sl - R * 0.055); c.quadraticCurveTo(ex, bY - R * 0.06, xo, bY - sl - R * 0.026);
      c.lineTo(xo, bY - sl + R * 0.022); c.quadraticCurveTo(ex, bY + R * 0.03, xi, bY + sl + R * 0.05); c.closePath(); c.fill();
      if (o.glasses) { c.strokeStyle = INK; c.lineWidth = R * 0.035; c.beginPath(); c.arc(ex, ey, R * 0.21, 0, TAU); c.stroke(); c.fillStyle = 'rgba(200,225,255,0.18)'; c.fill(); }
    }
    if (o.glasses) { c.strokeStyle = INK; c.lineWidth = R * 0.035; c.beginPath(); c.moveTo(fx - R * 0.08 * sq, ey); c.lineTo(fx + R * 0.08 * sq, ey); c.stroke(); }
    // mouth
    const my = ey + R * 0.4, mw = e.mw * R * sq * 0.6;
    c.strokeStyle = INK;
    if (e.mr > 0.5) {
      const rx = R * 0.06 * (1 + e.mo), ry = R * 0.08 * (1 + e.mo);
      c.fillStyle = MOUTH; c.beginPath(); c.ellipse(fx, my + R * 0.03, rx, ry, 0, 0, TAU); c.fill();
      c.save(); c.clip(); c.fillStyle = TONGUE; c.beginPath(); c.ellipse(fx, my + R * 0.03 + ry * 0.75, rx * 0.8, ry * 0.5, 0, 0, TAU); c.fill(); c.restore();
      c.lineWidth = R * 0.035; c.beginPath(); c.ellipse(fx, my + R * 0.03, rx, ry, 0, 0, TAU); c.stroke();
    } else if (e.mo < 0.06) {
      c.lineWidth = R * 0.045; c.beginPath(); c.moveTo(fx - mw, my + e.ms * R * 0.06); c.quadraticCurveTo(fx, my + e.mc * R * 0.55, fx + mw, my - e.ms * R * 0.08); c.stroke();
    } else {
      const bot = my + (e.mc * 0.9 + e.mo * 1.4) * R;
      if (e.mt > 0.5 && e.mg > 0.5) {   // gritted teeth: a rounded box, top and bottom rows, dark gaps
        const h = R * (0.1 + e.mo * 0.32), y0 = my - h * 0.25, bx = () => { c.beginPath(); c.roundRect(fx - mw, y0, mw * 2, h, h * 0.3); };
        bx(); c.fillStyle = MOUTH; c.fill(); c.save(); bx(); c.clip();
        c.fillStyle = '#fbf8f1'; c.fillRect(fx - mw, y0, mw * 2, h * 0.44); c.fillRect(fx - mw, y0 + h * 0.56, mw * 2, h * 0.44);
        c.strokeStyle = INK; c.lineWidth = R * 0.018; for (let x = fx - mw + R * 0.075; x < fx + mw - R * 0.02; x += R * 0.075) { c.beginPath(); c.moveTo(x, y0); c.lineTo(x, y0 + h); c.stroke(); }
        c.restore(); c.strokeStyle = INK; c.lineWidth = R * 0.038; bx(); c.stroke();
      } else {
      const path = () => { c.beginPath(); c.moveTo(fx - mw, my); c.quadraticCurveTo(fx, my + e.mc * R * 0.22, fx + mw, my); c.quadraticCurveTo(fx, bot, fx - mw, my); c.closePath(); };
      path(); c.fillStyle = MOUTH; c.fill();
      c.save(); path(); c.clip();
      if (e.mt > 0.5) { c.fillStyle = '#fbf8f1'; c.fillRect(fx - mw, my - R, mw * 2, R + (bot - my) * 0.36 + R * 0.01); }
      c.fillStyle = TONGUE; c.beginPath(); c.ellipse(fx, bot - (bot - my) * 0.12, mw * 0.55, (bot - my) * 0.42, 0, 0, TAU); c.fill();
      c.restore();
      c.strokeStyle = INK; c.lineWidth = R * 0.04; path(); c.stroke();
      }
    }
    c.globalAlpha = 1;
  }
  c.restore();
  // brush outline, heavier on the shadow side
  inkOutline(c, cx, cy, R);
  if (HS.mass) hairMass(c, cx, cy, R, o, back, HS.mass);
  if (e.sw > 0.5 && front > 0) { const dx = cx - R * 0.70, dy = cy - R * 0.52; c.fillStyle = '#62bdff'; c.strokeStyle = INK; c.lineWidth = R * 0.03; c.beginPath(); c.moveTo(dx, dy - R * 0.2); c.quadraticCurveTo(dx + R * 0.14, dy + R * 0.02, dx, dy + R * 0.1); c.quadraticCurveTo(dx - R * 0.14, dy + R * 0.02, dx, dy - R * 0.2); c.fill(); c.stroke(); c.fillStyle = 'rgba(255,255,255,0.8)'; c.beginPath(); c.arc(dx - R * 0.03, dy - R * 0.02, R * 0.025, 0, 7); c.fill(); }
  if (o.extra) o.extra(c, S, R, cx, cy, front, o); // hats, sunglasses: drawn on top
}

// ------------------------------------------------------------------ body materials and clothing
// Toon-shaded cloth: two soft tones from the stage's sun direction, a faint rim; ignores the world lights so the
// characters keep their flat cartoon colour in every mood (CHAR_UNI.tint darkens night and rain slightly).
// Faces stamp stencil 1; every body material refuses to draw there, so a torso, collar or arm never covers a face.
function bodyMask(m) { Object.assign(m, { stencilWrite: true, stencilRef: 1, stencilFunc: THREE.NotEqualStencilFunc, stencilFail: THREE.KeepStencilOp, stencilZFail: THREE.KeepStencilOp, stencilZPass: THREE.KeepStencilOp }); return m; }
function cloth(color, map = null) {
  return bodyMask(new THREE.ShaderMaterial({
    uniforms: { col: { value: new THREE.Color(color) }, lightDir: CHAR_UNI.lightDir, tint: CHAR_UNI.tint, map: { value: map }, useMap: { value: map ? 1 : 0 } },
    vertexShader: 'varying vec3 vN; varying vec3 vW; varying vec2 vUv; void main(){ vUv = uv; vN = normalize(mat3(modelMatrix) * normal); vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }',
    fragmentShader: `uniform vec3 col, lightDir, tint; uniform sampler2D map; uniform float useMap; varying vec3 vN; varying vec3 vW; varying vec2 vUv;
      void main(){ vec3 n = normalize(vN); float d = dot(n, normalize(lightDir)); float lit = smoothstep(-0.2, 0.3, d);
        vec3 col = useMap > 0.5 ? texture2D(map, vUv).rgb : col;
        vec3 v = normalize(cameraPosition - vW); float rim = pow(1.0 - max(dot(n, v), 0.0), 3.0);
        float wv = fract(sin(dot(floor(vW * 140.0), vec3(12.9898, 78.233, 37.719))) * 43758.5453);
        vec3 c = col * mix(0.68, 1.0, lit) * (0.97 + 0.05 * wv) * tint + vec3(rim * 0.05);
        gl_FragColor = vec4(c, 1.0);
        #include <colorspace_fragment>
      }`,
  }));
}
const inkMat = bodyMask(new THREE.MeshBasicMaterial({ color: INK_HEX, toneMapped: false }));
const inkBack = bodyMask(new THREE.MeshBasicMaterial({ color: INK_HEX, toneMapped: false, side: THREE.BackSide }));
// Outfits. 3D-detail kinds: plain tee polo shirt suit uniform hoodie. Painted costumes (a texture wrapped on the torso,
// thin ink seams like the reference): jacket vest stripes plaid overalls apron sweater cardigan hivis tracksuit labcoat dress.
// A role picks from its list (seeded by the shirt colour) unless the character sets `outfit`.
const ROLE_OUTFIT = { schemer: ['jacket', 'stripes', 'tracksuit', 'polo'], agent: ['suit', 'vest', 'cardigan'], officer: ['uniform'], quiet: ['cardigan', 'sweater', 'plaid'],
  doctor: ['labcoat'], victim: ['plaid', 'overalls', 'hivis', 'tee', 'jacket'], buddy: ['tracksuit', 'stripes', 'hoodie'], extra: ['apron', 'dress', 'sweater', 'vest', 'stripes', 'plaid'] };
const OUTFITS = ['plain', 'tee', 'polo', 'shirt', 'stripes', 'plaid', 'sweater', 'jacket'];
export const OUTFIT_NAMES = ['plain', 'tee', 'polo', 'shirt', 'suit', 'uniform', 'hoodie', 'jacket', 'vest', 'stripes', 'plaid', 'overalls', 'apron', 'sweater', 'cardigan', 'hivis', 'tracksuit', 'labcoat', 'dress'];
function outfitOf(o) {
  if (o.outfit) return o.outfit;
  const list = ROLE_OUTFIT[o.role]; const h = hashHex(o.shirt);
  return list ? list[h % list.length] : OUTFITS[h % OUTFITS.length];
}
// Costume painter: 512 x 256 canvas; x = around the body (front centre at x = 128, back at 384), y = down the body
// (top of the torso at y = 0). Colours: o.shirt = the main garment, o.shirt2 = what shows underneath.
const COSTUMES = new Set(['jacket', 'vest', 'stripes', 'plaid', 'overalls', 'apron', 'sweater', 'cardigan', 'hivis', 'tracksuit', 'labcoat', 'dress']);
// Garments are real layers: a shell a little outside the body (its own ink hull, inked hem and opening edges) so they
// read as clothes worn over the body, with the shirt or trousers showing where the garment ends or opens.
// shellGeo(prof, TH, y0, y1, range(v) -> [phi0, phi1], k, flare(y)) builds the shell between heights y0..y1; phi runs
// around the spine with the front at PI/2 (+x). UVs match costumeTex (u = phi / 2PI, v = height over the torso).
const FRONT = Math.PI / 2;
const R_FULL = () => [FRONT - Math.PI, FRONT + Math.PI], R_OPEN = (a) => [FRONT + a, FRONT + 2 * Math.PI - a], R_PATCH = (b) => [FRONT - b, FRONT + b];
function shellGeo(prof, TH, y0, y1, range, k = 1.07, flare = null, nY = 30, nP = 56) {
  const pos = [], uv = [], idx = [], rows = [];
  for (let j = 0; j <= nY; j++) {
    const v = j / nY, y = y0 + (y1 - y0) * v, [p0, p1] = range(v), r = Math.max(prof(y), 1e-3) * k * (flare ? flare(y) : 1), row = [];
    for (let i = 0; i <= nP; i++) { const ph = p0 + (p1 - p0) * (i / nP); pos.push(Math.sin(ph) * r, y, Math.cos(ph) * r); uv.push(ph / (2 * Math.PI), (y + TH / 2) / TH); row.push(new THREE.Vector3(Math.sin(ph) * r, y, Math.cos(ph) * r)); }
    rows.push(row);
  }
  for (let j = 0; j < nY; j++) for (let i = 0; i < nP; i++) { const a = j * (nP + 1) + i, b = a + 1, c = a + nP + 1, d = c + 1; idx.push(a, b, c, b, d, c); }   // outward normals
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2)); g.setIndex(idx); g.computeVertexNormals();
  g.userData.rows = rows; return g;
}
function addGarment(torso, prof, TH, R, spec, mat) {
  const geo = shellGeo(prof, TH, spec.y0, spec.y1, spec.range, spec.k ?? 1.07, spec.flare);
  mat.side = THREE.DoubleSide; const m = new THREE.Mesh(geo, mat); m.castShadow = true; torso.add(m);
  const hull = new THREE.Mesh(shellGeo(prof, TH, spec.y0 - R * 0.012, spec.y1, spec.range, (spec.k ?? 1.07) + R * 0.07 / Math.max(prof(0), 1e-3), spec.flare), inkBack); torso.add(hull);
  // inked edges: hem, and the opening / panel sides
  const rows = geo.userData.rows, edge = (pts) => { if (pts.length < 2) return; const t = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), Math.max(8, pts.length * 2), R * 0.024, 6, false), inkMat); torso.add(t); };
  edge(rows[0]);
  if (spec.edges !== 'hem') { edge(rows.map((r) => r[0])); edge(rows.map((r) => r[r.length - 1])); if (spec.topEdge) edge(rows[rows.length - 1]); }
  return m;
}
// pattern textures for garment layers (pockets, buttons, stripes, bands; the shirt under them is real geometry)
function garmentTex(kind, o) {
  const W = 512, H = 256, c = canvas(W, H), g = c.getContext('2d'), F = 128;
  const hex = (h) => '#' + new THREE.Color(h).getHexString(), main = kind === 'labcoat' ? '#f4f2ee' : kind === 'hivis' ? '#ff7a1a' : kind === 'overalls' ? '#3d5f93' : kind === 'apron' ? (o.shirt2 != null ? hex(o.shirt2) : '#f4f1ea') : hex(o.shirt);
  const SEAM = 'rgba(43,26,18,0.9)', y = (v) => H * (1 - v);
  g.fillStyle = main; g.fillRect(0, 0, W, H);
  const seam = (pts, w = 2.5) => { g.strokeStyle = SEAM; g.lineWidth = w; g.beginPath(); pts.forEach(([x, v], i) => (i ? g.lineTo(x, y(v)) : g.moveTo(x, y(v)))); g.stroke(); };
  const pocket = (x, v, w = 36, h = 0.12) => { seam([[x - w / 2, v], [x - w / 2, v - h], [x + w / 2, v - h], [x + w / 2, v]], 2); seam([[x - w / 2 - 2, v], [x + w / 2 + 2, v]], 3); };
  const button = (x, v, col) => { g.fillStyle = col; g.beginPath(); g.arc(x, y(v), 4.5, 0, 7); g.fill(); };
  if (kind === 'jacket' || kind === 'suit' || kind === 'labcoat' || kind === 'cardigan') {
    pocket(F - 60, 0.42); pocket(F + 60, 0.42); if (kind === 'labcoat') { pocket(F - 52, 0.76, 28, 0.08); g.fillStyle = '#2f6fe0'; g.fillRect(F - 58, y(0.8), 4, 18); }
    for (const v of kind === 'cardigan' ? [0.72, 0.56, 0.4, 0.24] : [0.5, 0.32]) button(F + 46, v, shade(main, -0.45));
    if (kind === 'cardigan') { g.strokeStyle = shade(main, -0.16); g.lineWidth = 1.5; for (let x = 0; x < W; x += 7) { g.beginPath(); g.moveTo(x, y(0.16)); g.lineTo(x, y(0)); g.stroke(); } }
  }
  if (kind === 'vest') { for (const v of [0.4, 0.28, 0.16]) button(F + 6, v, shade(main, -0.5)); pocket(F - 46, 0.38, 26, 0.04); pocket(F + 46, 0.38, 26, 0.04); }
  if (kind === 'hivis') for (const v of [0.3, 0.5]) { g.fillStyle = '#e2e6eb'; g.fillRect(0, y(v + 0.06), W, H * 0.06); seam([[0, v], [W, v]], 1.5); seam([[0, v + 0.06], [W, v + 0.06]], 1.5); }
  if (kind === 'overalls') { g.strokeStyle = '#e0b84a'; g.lineWidth = 1.5; g.setLineDash([4, 4]); g.strokeRect(F - 40, y(0.8), 80, y(0.52) - y(0.8)); g.setLineDash([]); pocket(F, 0.74, 40, 0.12); }
  if (kind === 'apron') pocket(F, 0.4, 46, 0.12);
  if (kind === 'stripes') { g.fillStyle = new THREE.Color(o.shirt).getHSL({}).l < 0.5 ? shade(main, 0.55) : '#fbf7ef'; for (let x = 6; x < W; x += 30) g.fillRect(x, 0, 12, H); }
  if (kind === 'plaid') { const dk = shade(main, -0.42); g.globalAlpha = 0.55; g.fillStyle = dk; for (let x = 0; x < W; x += 42) g.fillRect(x, 0, 14, H); for (let yy = 0; yy < H; yy += 42) g.fillRect(0, yy, W, 14);
    g.globalAlpha = 0.6; g.fillStyle = '#fbf7ef'; for (let x = 24; x < W; x += 42) g.fillRect(x, 0, 3, H); for (let yy = 24; yy < H; yy += 42) g.fillRect(0, yy, W, 3); g.globalAlpha = 1; seam([[F, 0.95], [F, 0.25]], 2); }
  if (kind === 'sweater') { g.fillStyle = o.shirt2 != null ? hex(o.shirt2) : '#fbf7ef'; g.fillRect(0, y(0.74), W, H * 0.12); g.fillStyle = shade(main, -0.25);
    for (let x = 0; x < W; x += 16) { g.beginPath(); g.moveTo(x, y(0.64)); g.lineTo(x + 8, y(0.72)); g.lineTo(x + 16, y(0.64)); g.closePath(); g.fill(); }
    g.strokeStyle = shade(main, -0.2); g.lineWidth = 1.5; for (let x = 0; x < W; x += 7) { g.beginPath(); g.moveTo(x, y(0.3)); g.lineTo(x, y(0.2)); g.stroke(); } }
  if (kind === 'tracksuit') { const st = new THREE.Color(o.shirt).getHSL({}).l < 0.5 ? '#fbf7ef' : shade(main, -0.55); g.fillStyle = st; for (const x0 of [0, 256, 512]) { g.fillRect(x0 - 9, 0, 5, H); g.fillRect(x0 + 4, 0, 5, H); } seam([[F, 0.2], [F, 0.99]], 2.5); }
  if (kind === 'dress') { g.fillStyle = shade(main, 0.35); for (let i = 0; i < 90; i++) { const x = (i * 73) % W, v = ((i * 37) % 44) / 100; g.beginPath(); g.arc(x, y(v), 4, 0, 7); g.fill(); }
    g.fillStyle = o.shirt2 != null ? hex(o.shirt2) : '#fbf7ef'; g.fillRect(0, y(0.5), W, H * 0.05); }
  const t = ctex(c); t.wrapS = THREE.RepeatWrapping; return t;
}
const LAYERED = new Set(['jacket', 'suit', 'labcoat', 'cardigan', 'vest', 'hivis', 'overalls', 'apron', 'sweater', 'stripes', 'plaid', 'tracksuit', 'dress']);
function underColor(kind, o) {   // what the body (torso) shows under the garment
  const lum = new THREE.Color(o.shirt).getHSL({}).l;
  if (kind === 'suit') return 0xf3efe6;
  if (['sweater', 'stripes', 'plaid', 'tracksuit'].includes(kind)) return o.pants ?? (kind === 'tracksuit' ? new THREE.Color(o.shirt).multiplyScalar(0.55).getHex() : 0x3a4152);   // trousers below the hem
  if (kind === 'dress') return o.pants ?? new THREE.Color(o.shirt).getHex();
  return o.shirt2 ?? (kind === 'overalls' || kind === 'apron' ? o.shirt : lum < 0.45 ? 0xf2ede4 : new THREE.Color(o.shirt).lerp(new THREE.Color(0xffffff), 0.65).getHex());
}
function wearGarment(torso, o, kind, prof, TH, tr, R) {
  const bot = -TH / 2, top = TH / 2, main = cloth(kind === 'labcoat' ? 0xf4f2ee : kind === 'hivis' ? 0xff7a1a : kind === 'overalls' ? 0x3d5f93 : o.shirt, garmentTex(kind, o));
  const sm = (a, b, v) => { const t = clamp((v - a) / (b - a)); return t * t * (3 - 2 * t); };
  if (kind === 'jacket' || kind === 'suit' || kind === 'labcoat' || kind === 'cardigan') {
    const long = kind === 'labcoat', open = kind === 'cardigan' ? 0.2 : 0.24;
    addGarment(torso, prof, TH, R, { y0: bot + tr * (long ? 0.12 : 0.42), y1: top - tr * 0.05, k: 1.08, flare: long ? (y) => 1 + 0.08 * clamp((bot + tr * 0.9 - y) / (tr * 0.8)) : null,
      range: (v) => R_OPEN(open + (kind === 'cardigan' ? 0.12 : 0.42) * sm(0.5, 1.0, v)) }, main);
    if (kind !== 'cardigan') for (const sd of [-1, 1]) {   // lapels: folded-back flaps on the opening, a step in front of the coat
      const sh = new THREE.Shape(); sh.moveTo(0, 0); sh.lineTo(R * 0.16, -R * 0.08); sh.lineTo(R * 0.03, -R * 0.5); sh.closePath();
      const lp = new THREE.Mesh(new THREE.ShapeGeometry(sh), cloth(new THREE.Color(kind === 'labcoat' ? 0xf4f2ee : o.shirt).multiplyScalar(0.82))), y = top - tr * 0.2, ph = FRONT + sd * 0.62, r = prof(y) * 1.1;
      lp.position.set(Math.sin(ph) * r, y, Math.cos(ph) * r); lp.rotation.set(0, Math.PI / 2 + sd * 0.55, 0); if (sd < 0) lp.scale.x = -1; torso.add(lp);
      const ed = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3([V3(0, 0, 0), V3(R * 0.16, -R * 0.08, 0), V3(R * 0.03, -R * 0.5, 0)]), 12, R * 0.02, 5, false), inkMat); lp.add(ed);
    }
  }
  if (kind === 'vest' || kind === 'hivis')
    addGarment(torso, prof, TH, R, { y0: bot + tr * 0.4, y1: top - tr * 0.1, k: 1.07, range: (v) => R_OPEN(0.06 + 0.95 * sm(0.35, 1.0, v)) }, main);
  if (kind === 'overalls') {
    const waist = bot + TH * 0.42;
    addGarment(torso, prof, TH, R, { y0: bot + tr * 0.25, y1: waist, k: 1.08, range: R_FULL, edges: 'hem', topEdge: false }, main);
    addGarment(torso, prof, TH, R, { y0: waist - R * 0.02, y1: bot + TH * 0.78, k: 1.08, range: () => R_PATCH(0.62), topEdge: true }, main);
    for (const sd of [-1, 1]) addGarment(torso, prof, TH, R, { y0: bot + TH * 0.76, y1: top - tr * 0.08, k: 1.085, range: () => [FRONT + sd * 0.42 - 0.09, FRONT + sd * 0.42 + 0.09] }, main);
  }
  if (kind === 'apron') {
    addGarment(torso, prof, TH, R, { y0: bot + tr * 0.25, y1: bot + TH * 0.62, k: 1.08, range: () => R_PATCH(0.85) }, main);
    addGarment(torso, prof, TH, R, { y0: bot + TH * 0.6, y1: bot + TH * 0.8, k: 1.085, range: (v) => R_PATCH(0.85 - 0.35 * v), topEdge: true }, main);
    for (const sd of [-1, 1]) { const y = bot + TH * 0.8, r = prof(y) * 1.09, ph = FRONT + sd * 0.48;
      torso.add(new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3([V3(Math.sin(ph) * r, y, Math.cos(ph) * r), V3(Math.sin(FRONT + sd * 0.3) * prof(top - tr * 0.3) * 1.1, top - tr * 0.3, Math.cos(FRONT + sd * 0.3) * prof(top - tr * 0.3) * 1.1)]), 6, R * 0.03, 5, false), inkMat)); }
  }
  if (['sweater', 'stripes', 'plaid', 'tracksuit'].includes(kind))
    addGarment(torso, prof, TH, R, { y0: bot + tr * (kind === 'tracksuit' ? 0.3 : 0.55), y1: top - tr * 0.05, k: 1.06, range: R_FULL, edges: 'hem' }, main);
  if (kind === 'dress')
    addGarment(torso, prof, TH, R, { y0: bot - tr * 0.35, y1: top - tr * 0.05, k: 1.06, range: R_FULL, edges: 'hem', flare: (y) => 1 + 0.42 * clamp((bot + TH * 0.45 - y) / (TH * 0.5)) ** 1.2 }, main);
}
function costumeTex(kind, o) {
  const W = 512, H = 256, c = canvas(W, H), g = c.getContext('2d'), F = 128, B = 384;
  const hex = (h) => '#' + new THREE.Color(h).getHexString(), main = hex(o.shirt), lum = new THREE.Color(o.shirt).getHSL({}).l;
  const under = o.shirt2 != null ? hex(o.shirt2) : (lum < 0.45 ? '#f2ede4' : shade(main, -0.5));
  const SEAM = 'rgba(43,26,18,0.9)', y = (v) => H * (1 - v);             // v: 0 = bottom of the torso, 1 = top
  const rect = (col, x0, v0, x1, v1) => { g.fillStyle = col; g.fillRect(x0, y(v1), x1 - x0, y(v0) - y(v1)); };
  const both = (fn) => { fn(0); fn(W); };   // things that cross the wrap seam
  const seam = (pts, w = 2.5) => { g.strokeStyle = SEAM; g.lineWidth = w; g.lineJoin = 'round'; g.beginPath(); pts.forEach(([x, v], i) => (i ? g.lineTo(x, y(v)) : g.moveTo(x, y(v)))); g.stroke(); };
  const poly = (col, pts, ink = true) => { g.fillStyle = col; g.beginPath(); pts.forEach(([x, v], i) => (i ? g.lineTo(x, y(v)) : g.moveTo(x, y(v)))); g.closePath(); g.fill(); if (ink) { g.strokeStyle = SEAM; g.lineWidth = 2.5; g.stroke(); } };
  const button = (x, v, col = SEAM, r = 4.5) => { g.fillStyle = col; g.beginPath(); g.arc(x, y(v), r, 0, 7); g.fill(); };
  const pocket = (x, v, w = 34, h = 0.1, col = null) => { if (col) rect(col, x - w / 2, v - h, x + w / 2, v); seam([[x - w / 2, v], [x - w / 2, v - h], [x + w / 2, v - h], [x + w / 2, v]], 2); seam([[x - w / 2 - 2, v], [x + w / 2 + 2, v]], 3); };
  const knit = (col) => { g.strokeStyle = col; g.lineWidth = 1.5; for (let x = 0; x < W; x += 7) { g.beginPath(); g.moveTo(x, y(0.12)); g.lineTo(x, y(0)); g.stroke(); } };
  rect(main, 0, 0, W, 1);
  if (kind === 'jacket' || kind === 'labcoat' || kind === 'cardigan') {
    const base = kind === 'labcoat' ? '#f4f2ee' : main; rect(base, 0, 0, W, 1);
    const open = kind === 'cardigan' ? 18 : 26, top = kind === 'cardigan' ? 0.97 : 0.97;
    rect(under, F - open, 0.16, F + open, top);                                                 // the shirt in the opening
    if (kind !== 'cardigan') { poly(shade(base, -0.12), [[F - open, 0.97], [F - open - 34, 0.86], [F - open - 6, 0.6], [F - open, 0.62]]);   // lapels
      poly(shade(base, -0.12), [[F + open, 0.97], [F + open + 34, 0.86], [F + open + 6, 0.6], [F + open, 0.62]]); }
    seam([[F - open, 0.16], [F - open, 0.98]]); seam([[F + open, 0.16], [F + open, 0.98]]);
    pocket(F - 58, 0.4, 36, 0.12); pocket(F + 58, 0.4, 36, 0.12);
    for (const v of kind === 'cardigan' ? [0.75, 0.6, 0.45, 0.3] : [0.52, 0.34]) button(F + open + 8, v, kind === 'labcoat' ? '#9aa3ad' : shade(base, -0.45));
    if (kind === 'labcoat') { pocket(F - 52, 0.74, 28, 0.08); g.fillStyle = '#2f6fe0'; g.fillRect(F - 58, y(0.79), 4, 18); }
    if (kind === 'cardigan') knit(shade(base, -0.18));
    if (o.bow == null && kind === 'jacket') { g.fillStyle = shade(under, -0.35); g.beginPath(); g.moveTo(F - 8, y(0.95)); g.lineTo(F + 8, y(0.95)); g.lineTo(F + 5, y(0.55)); g.lineTo(F, y(0.5)); g.lineTo(F - 5, y(0.55)); g.closePath(); g.fill(); }   // a tie
  }
  if (kind === 'vest' || kind === 'hivis') {
    const vc = kind === 'hivis' ? '#ff7a1a' : main; rect(under, 0, 0, W, 1); rect(vc, 0, 0, W, 0.86);
    both((o0) => { rect(vc, o0 + F + 40, 0.86, o0 + B - 40, 1); });                                 // shoulders / back
    poly(under, [[F - 42, 1.01], [F + 42, 1.01], [F, 0.5]], false); seam([[F - 42, 0.99], [F, 0.5], [F + 42, 0.99]]);   // V neck
    if (kind === 'vest') { for (const v of [0.44, 0.32, 0.2]) button(F + 4, v, shade(main, -0.5)); seam([[F, 0.5], [F, 0.08]], 2); pocket(F - 44, 0.42, 26, 0.04); pocket(F + 44, 0.42, 26, 0.04); }
    else for (const v of [0.34, 0.52]) { rect('#dfe3e8', 0, v, W, v + 0.06); seam([[0, v], [W, v]], 1.5); seam([[0, v + 0.06], [W, v + 0.06]], 1.5); }
  }
  if (kind === 'stripes') { const st = lum < 0.5 ? shade(main, 0.55) : '#fbf7ef'; g.fillStyle = st; for (let x = 6; x < W; x += 30) g.fillRect(x, 0, 12, H); button(F, 0.8, SEAM, 4); button(F, 0.68, SEAM, 4); }
  if (kind === 'plaid') { const dk = shade(main, -0.42); g.globalAlpha = 0.55; g.fillStyle = dk; for (let x = 0; x < W; x += 42) g.fillRect(x, 0, 14, H); for (let yy = 0; yy < H; yy += 42) g.fillRect(0, yy, W, 14);
    g.globalAlpha = 0.6; g.fillStyle = '#fbf7ef'; for (let x = 24; x < W; x += 42) g.fillRect(x, 0, 3, H); for (let yy = 24; yy < H; yy += 42) g.fillRect(0, yy, W, 3); g.globalAlpha = 1;
    seam([[F, 0.95], [F, 0.1]], 2); for (const v of [0.8, 0.62, 0.44, 0.26]) button(F + 5, v, '#fbf7ef', 3.5); }
  if (kind === 'overalls') {
    const den = '#3d5f93'; rect(den, 0, 0, W, 0.48); rect(den, F - 46, 0.48, F + 46, 0.84); seam([[F - 46, 0.48], [F - 46, 0.84], [F + 46, 0.84], [F + 46, 0.48]]);
    for (const dx of [-34, 34]) { const sx = F + dx; poly(den, [[sx - 8, 0.84], [sx + 8, 0.84], [sx + 8, 1.01], [sx - 8, 1.01]]); button(sx, 0.8, '#e0b84a', 5); }
    both((o0) => { poly(den, [[o0 + B - 50, 0.48], [o0 + B - 30, 1.01], [o0 + B - 14, 1.01], [o0 + B - 34, 0.48]]); poly(den, [[o0 + B + 50, 0.48], [o0 + B + 30, 1.01], [o0 + B + 14, 1.01], [o0 + B + 34, 0.48]]); });
    seam([[0, 0.48], [F - 46, 0.48]]); seam([[F + 46, 0.48], [W, 0.48]]); pocket(F, 0.74, 40, 0.14); g.strokeStyle = '#e0b84a'; g.lineWidth = 1.5; g.setLineDash([4, 4]); g.strokeRect(F - 42, y(0.82), 84, y(0.5) - y(0.82)); g.setLineDash([]);
  }
  if (kind === 'apron') { const ap = o.shirt2 != null ? under : '#f4f1ea'; poly(ap, [[F - 52, 0.1], [F + 52, 0.1], [F + 52, 0.62], [F + 32, 0.8], [F - 32, 0.8], [F - 52, 0.62]]);
    seam([[F - 32, 0.8], [F - 18, 1.0]]); seam([[F + 32, 0.8], [F + 18, 1.0]]); rect(ap, 0, 0.5, F - 52, 0.54); rect(ap, F + 52, 0.5, W, 0.54); pocket(F, 0.42, 44, 0.12); }
  if (kind === 'sweater') { const band = o.shirt2 != null ? under : '#fbf7ef'; rect(band, 0, 0.6, W, 0.72);
    g.fillStyle = shade(main, -0.25); for (let x = 0; x < W; x += 16) { g.beginPath(); g.moveTo(x, y(0.62)); g.lineTo(x + 8, y(0.7)); g.lineTo(x + 16, y(0.62)); g.closePath(); g.fill(); }
    seam([[0, 0.6], [W, 0.6]], 1.5); seam([[0, 0.72], [W, 0.72]], 1.5); knit(shade(main, -0.2)); rect(shade(main, -0.15), 0, 0.93, W, 1); }
  if (kind === 'tracksuit') { const st = lum < 0.5 ? '#fbf7ef' : shade(main, -0.55); for (const x0 of [0, 256]) { rect(st, x0 - 9, 0, x0 - 4, 1); rect(st, x0 + 4, 0, x0 + 9, 1); } rect(st, W - 9, 0, W, 1);
    seam([[F, 0.08], [F, 0.99]], 2.5); g.fillStyle = '#c9ced6'; g.fillRect(F - 3, y(0.96), 6, 14); rect(shade(main, -0.18), 0, 0.92, W, 1); }
  if (kind === 'dress') { const acc = o.shirt2 != null ? under : '#fbf7ef'; rect(acc, 0, 0.44, W, 0.5); seam([[0, 0.44], [W, 0.44]], 1.5); seam([[0, 0.5], [W, 0.5]], 1.5);
    g.fillStyle = shade(main, 0.35); for (let i = 0; i < 70; i++) { const x = (i * 73) % W, v = 0.06 + ((i * 37) % 36) / 100; g.beginPath(); g.arc(x, y(v), 4, 0, 7); g.fill(); }
    g.strokeStyle = shade(main, -0.3); g.lineWidth = 1.5; for (let x = 10; x < W; x += 26) { g.beginPath(); g.moveTo(x, y(0.44)); g.lineTo(x - 4, y(0.02)); g.stroke(); }
    poly(acc, [[F - 30, 1.01], [F + 30, 1.01], [F, 0.84]], false); }
  const t = ctex(c); t.wrapS = THREE.RepeatWrapping; return t;
}
function hashHex(h) { let x = Number(h) >>> 0; x = ((x >>> 16) ^ x) * 0x45d9f3b; return (x >>> 0) % 997; }
// Details sit on the torso's front (+x in torso space); y runs up the body from -tl/2 to +tl/2 (+ caps of radius tr).
// Body builds measured on reference shorts (adults ~3.5 head-heights tall: torso 0.9-1.23 HH, legs 1.2-1.54 HH, torso
// width 0.58-0.97 of the head width; kids 2.7-3.0 HH). girth/torso/legs multiply the base body; taper = top width / bottom
// width of the bean torso (narrow under the chin, widest low, round bottom); belly = extra bulge low on the front.
export const BUILDS = {
  average: { girth: 1.0, torso: 1.0, legs: 1.0, taper: 0.92, belly: 0.0 },
  slim: { girth: 0.8, torso: 1.06, legs: 1.08, taper: 0.95, belly: 0.0 },
  tall: { girth: 0.9, torso: 1.14, legs: 1.16, taper: 0.93, belly: 0.0 },
  short: { girth: 1.02, torso: 0.86, legs: 0.84, taper: 0.92, belly: 0.02 },
  stout: { girth: 1.2, torso: 1.12, legs: 0.92, taper: 0.94, belly: 0.04 },
  big: { girth: 1.36, torso: 1.2, legs: 0.86, taper: 0.93, belly: 0.03 },
  kid: { girth: 0.84, torso: 0.72, legs: 0.66, taper: 0.94, belly: 0.0 },
};
export const BUILD_NAMES = Object.keys(BUILDS);
// torso profile (reference: a long, even capsule with round ends; only the top end narrows a little under the chin, and
// heavy builds get a slight belly in the middle). Radius at local height y (y along the spine, centre 0, total height H)
function beanProfile(tr, H, taper, belly) {
  const rb = tr, rt = tr * taper, hb = rb * 0.62 / H, ht = rt / H;   // a flatter base: a shorter, squarer bottom cap (not a bulb)
  return (y) => {
    const s = clamp(y / H + 0.5);
    let r;
    if (s < hb) r = rb * Math.pow(Math.max(0, 1 - ((hb - s) / hb) ** 3), 1 / 3);
    else if (s > 1 - ht) r = rt * Math.sqrt(Math.max(0, 1 - ((s - (1 - ht)) / ht) ** 2));
    else { const u = (s - hb) / Math.max(1e-4, 1 - hb - ht), w = clamp((u - 0.6) / 0.4); r = rb + (rt - rb) * w * w * (3 - 2 * w); }
    return r * (1 + belly * Math.exp(-(((s - 0.45) / 0.26) ** 2)));
  };
}
function beanGeo(prof, H, pad = 0) {   // pad > 0: the ink hull, about 3x thicker at the bottom than at the top (like the face outline)
  const base = [];
  for (let i = 0; i <= 56; i++) { const y = -H / 2 + (i / 56) * H; base.push([Math.max(prof(y), 0), y]); }
  const pts = base.map(([r, y], i) => {
    if (!pad) return new THREE.Vector2(Math.max(r, 1e-4), y);
    const [r0, y0] = base[Math.max(0, i - 1)], [r1, y1] = base[Math.min(56, i + 1)];
    let nx = y1 - y0, ny = -(r1 - r0); const L = Math.hypot(nx, ny) || 1; nx /= L; ny /= L;        // outward normal of the profile
    if (i === 0) { nx = 0; ny = -1; } if (i === 56) { nx = 0; ny = 1; }
    const pw = pad * (1.45 - 1.05 * (i / 56));                                                       // thick at the bottom, thin on top
    return new THREE.Vector2(Math.max(r + nx * pw, 1e-4), y + ny * pw);
  });
  return new THREE.LatheGeometry(pts, 36);
}
function dress(torso, o, tr, tl, R) {
  const kind = outfitOf(o);
  const base = new THREE.Color(o.shirt), dark = cloth(base.clone().multiplyScalar(0.7)), light = cloth(0xf3efe6);
  const add = (geo, mat, x, y, z, rx = 0, ry = 0, rz = 0) => { const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); m.rotation.set(rx, ry, rz); torso.add(m); return m; };
  const top = tl / 2 + tr * 0.55, rA = torso.userData.rAt || (() => tr), Fy = (y) => rA(y) * 0.995, F = Fy(0), rTop = rA(top - R * 0.04);
  const belt = () => { const by = -tl / 2 + R * 0.04, br = rA(by) * 1.012; add(new THREE.CylinderGeometry(br, br, R * 0.11, 28, 1, true), cloth(0x3b2618), 0, by, 0);
    add(new THREE.BoxGeometry(R * 0.03, R * 0.1, R * 0.12), cloth(0xd9b44a), Fy(by) + R * 0.02, by, 0); };
  const buttons = (n, mat, y0, step) => { for (let i = 0; i < n; i++) add(new THREE.SphereGeometry(R * 0.028, 8, 6), mat, Fy(y0 - i * step) + R * 0.012, y0 - i * step, 0); };
  if (kind === 'tee') add(new THREE.TorusGeometry(rTop * 0.62, R * 0.03, 6, 20, Math.PI), dark, rTop * 0.5, top - R * 0.02, 0, Math.PI / 2, 0, Math.PI / 2 + 0.55);
  if (kind === 'polo' || kind === 'shirt') {
    const colMat = kind === 'shirt' ? light : dark;
    for (const s of [-1, 1]) add(new THREE.BoxGeometry(R * 0.05, R * 0.2, R * 0.2), colMat, rTop * 0.86, top - R * 0.06, s * R * 0.12, s * 0.5, 0, -0.75);
    { const py = kind === 'shirt' ? 0 : top - tr * 0.55 - R * 0.17; add(new THREE.BoxGeometry(R * 0.012, kind === 'shirt' ? tl * 0.9 : R * 0.34, R * 0.05), dark, Fy(py) + R * 0.005, py, 0); }
    buttons(kind === 'shirt' ? 4 : 2, light, top - tr * 0.6, kind === 'shirt' ? tl * 0.24 : R * 0.13);
    belt();
  }
  if (kind === 'plain') belt();
  if (kind === 'jacket') { const tie = new THREE.Shape(); tie.moveTo(-R * 0.03, 0); tie.lineTo(R * 0.03, 0); tie.lineTo(R * 0.05, -R * 0.4); tie.lineTo(0, -R * 0.47); tie.lineTo(-R * 0.05, -R * 0.4); tie.closePath();
    add(new THREE.ShapeGeometry(tie), cloth(new THREE.Color(o.shirt).multiplyScalar(0.55)), Fy(top - R * 0.22) + R * 0.008, top - R * 0.02, 0, 0, Math.PI / 2, 0); }
  if (o.bow != null) {   // bow tie under the chin
    const bm = cloth(o.bow), y0 = tl / 2 - R * 0.05, x0 = rA(y0) * 0.98;   // just below the chin, where the head no longer covers it
    for (const sd of [-1, 1]) { const w = new THREE.Mesh(new THREE.ConeGeometry(R * 0.085, R * 0.16, 4), bm); w.position.set(x0, y0, sd * R * 0.08); w.rotation.set(sd * Math.PI / 2, 0, 0); torso.add(w);
      const wi = new THREE.Mesh(new THREE.ConeGeometry(R * 0.1, R * 0.18, 4), inkBack); wi.position.copy(w.position); wi.rotation.copy(w.rotation); torso.add(wi); }
    { const kn = new THREE.Mesh(new THREE.SphereGeometry(R * 0.04, 10, 8), bm); kn.position.set(x0 + R * 0.01, y0, 0); torso.add(kn); }
  }
  if (kind === 'suit') {
    const v = new THREE.Shape(); v.moveTo(-R * 0.16, 0); v.lineTo(R * 0.16, 0); v.lineTo(0, -R * 0.5); v.closePath();
    const tie = new THREE.Shape(); tie.moveTo(-R * 0.03, 0); tie.lineTo(R * 0.03, 0); tie.lineTo(R * 0.05, -R * 0.4); tie.lineTo(0, -R * 0.47); tie.lineTo(-R * 0.05, -R * 0.4); tie.closePath();
    add(new THREE.ShapeGeometry(tie), cloth(0xc0302c), Fy(top - R * 0.22) + R * 0.008, top - R * 0.02, 0, 0, Math.PI / 2, 0);
    buttons(2, dark, top - R * 0.62, R * 0.16);
  }
  if (kind === 'uniform') {
    for (const s of [-1, 1]) add(new THREE.BoxGeometry(R * 0.015, R * 0.16, R * 0.17), dark, Fy(top - tr * 0.75) + R * 0.005, top - tr * 0.75, s * R * 0.17);
    add(new THREE.CylinderGeometry(R * 0.05, R * 0.05, R * 0.015, 12), cloth(0xe0b84a), Fy(top - tr * 0.62) + R * 0.012, top - tr * 0.62, -R * 0.17, 0, 0, Math.PI / 2);
    buttons(3, cloth(0xe0b84a), top - tr * 0.55, tl * 0.25);
    belt();
  }
  if (kind === 'hoodie') {
    add(new THREE.TorusGeometry(rTop * 0.85, R * 0.1, 8, 22), dark, -rTop * 0.15, top - R * 0.05, 0, Math.PI / 2, 0.35, 0);
    for (const s of [-1, 1]) add(new THREE.CylinderGeometry(R * 0.012, R * 0.012, R * 0.28, 6), light, Fy(top - tr * 0.6 - R * 0.14) + R * 0.01, top - tr * 0.6 - R * 0.14, s * R * 0.08);
    add(new THREE.BoxGeometry(R * 0.012, R * 0.22, R * 0.42), dark, Fy(-tl / 2 + R * 0.12) + R * 0.004, -tl / 2 + R * 0.12, 0);
  }
}

export function makeChar(o) {
  { const B = BUILDS[o.build] || BUILDS.average; o = { ...o, girth: B.girth * (o.girth ?? 1), torso: B.torso * (o.torso ?? 1), legs: B.legs * (o.legs ?? 1), taper: o.taper ?? B.taper, belly: o.belly ?? B.belly }; }
  const g = new THREE.Group(), S = 640, HSHAPE = { ...headShapeFor(o), ...(o.head || {}) };
  const cv = canvas(S, S), tex = ctex(cv);
  // the head is an opaque cut-out (alpha-to-coverage keeps the edge smooth) drawn before the body and stamped into the
  // stencil: the body never shows through the face; collar and shoulders tuck in behind the chin like the reference
  const head = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ map: tex, alphaTest: 0.5, alphaToCoverage: true, toneMapped: false,
    stencilWrite: true, stencilRef: 1, stencilFunc: THREE.AlwaysStencilFunc, stencilZPass: THREE.ReplaceStencilOp }));
  head.renderOrder = -2; const HEAD_SCALE = o.R * 2 / HEAD_FRAC; g.add(head);
  const hs = new THREE.Mesh(new THREE.SphereGeometry(o.R, 16, 12), new THREE.MeshBasicMaterial({ colorWrite: false, depthWrite: false })); hs.castShadow = true; g.add(hs);
  const tr = o.R * 0.66 * (o.girth || 1), tl = Math.max(o.R * 0.5, o.R * 1.38 * (o.torso || 1) - 0.9 * o.R * ((o.girth || 1) - 1)), TH = tl + 2 * tr;   // wide builds keep a straight middle (a capsule, not an egg)
  const prof = beanProfile(tr, TH, o.taper, o.belly);
  const extra = o.extra || (o.acc && accDrawer(o.acc));
  const kindO = outfitOf(o), torso = new THREE.Mesh(beanGeo(prof, TH), cloth(LAYERED.has(kindO) ? underColor(kindO, o) : o.shirt, !LAYERED.has(kindO) && COSTUMES.has(kindO) ? costumeTex(kindO, o) : null)); torso.castShadow = true; torso.userData.rAt = prof;
  if (LAYERED.has(kindO)) wearGarment(torso, o, kindO, prof, TH, tr, o.R);
  { const hull = new THREE.Mesh(beanGeo(prof, TH, o.R * 0.08), inkBack); torso.add(hull); }   // body ink as heavy as the face's: heaviest along the bottom and sides
  g.add(torso);
  dress(torso, o, tr, tl, o.R);
  const limbs = [], ends = [];
  for (let i = 0; i < 4; i++) {
    const m = new THREE.Mesh(new THREE.BufferGeometry(), inkMat); m.castShadow = true; g.add(m); limbs.push(m);
    const h = new THREE.Mesh(new THREE.SphereGeometry(o.R * (i < 2 ? 0.125 : 0.13), 12, 10), inkMat);
    if (i >= 2) h.scale.set(1.7, 0.78, 1.1);   // shoes (hands: round ink dots, reference 0.08-0.15 head widths)
    g.add(h); ends.push(h);
    const cap = new THREE.Mesh(new THREE.SphereGeometry(1, 10, 8), inkMat); g.add(cap); h.userData.cap = cap;   // round start of the stroke
  }
  const lw = o.R * 0.08, up = V3(0, 1, 0), tmp = V3(), q = new THREE.Quaternion(), mtx = new THREE.Matrix4();
  g.R = o.R; g.headMesh = head; g.opts = o;
  let brace = null;
  if (o.acc && o.acc.some((a) => String(a).startsWith('neckbrace'))) {
    brace = new THREE.Mesh(new THREE.CylinderGeometry(o.R * 0.5, o.R * 0.6, o.R * 0.34, 24), cloth(0xf1ece0));
    brace.add(new THREE.Mesh(new THREE.CylinderGeometry(o.R * 0.535, o.R * 0.635, o.R * 0.36, 24), inkBack));
    const strap = new THREE.Mesh(new THREE.CylinderGeometry(o.R * 0.505, o.R * 0.605, o.R * 0.07, 24, 1, true), cloth(0xb9b1a0)); brace.add(strap);
    g.add(brace);
  }
  g.traverse((ob) => ob.layers.set(CHAR_LAYER));
  g.headWorld = () => hs.getWorldPosition(V3());
  g.pose = (p, cam) => {
    const axis = tmp.copy(p.neck).sub(p.hip).normalize().clone();
    // torso frame: y along the spine, x toward where the character faces
    let fwd = p.face.clone().addScaledVector(axis, -p.face.dot(axis)); if (fwd.lengthSq() < 1e-6) fwd = V3(1, 0, 0).addScaledVector(axis, -axis.x);
    fwd.normalize(); const side = fwd.clone().cross(axis).normalize();
    mtx.makeBasis(fwd, axis, side); torso.quaternion.setFromRotationMatrix(mtx);
    torso.position.copy(p.hip).lerp(p.neck, 0.5);
    const hc = p.neck.clone().addScaledVector(axis, o.R * 0.86); hs.position.copy(hc);
    if (brace) { brace.position.copy(p.neck).addScaledVector(axis, o.R * 0.06); brace.quaternion.copy(torso.quaternion); }
    g.updateWorldMatrix(true, true);
    // the head plane sits in front of the shoulders, toward the camera, scaled so it keeps its apparent size
    const camPos = cam.getWorldPosition(V3()), hcw = hs.getWorldPosition(V3()), dist = camPos.distanceTo(hcw);
    const pull = Math.min(o.R * 0.25, dist * 0.3), toCam = camPos.clone().sub(hcw).normalize();
    const hpw = hcw.clone().addScaledVector(toCam, pull); head.position.copy(g.worldToLocal(hpw.clone()));
    { const ex0 = typeof p.expr === 'string' ? null : p.expr, u = ex0 && ex0.pop != null ? ex0.pop : -1, sc = HEAD_SCALE * (dist - pull) / dist / g.getWorldScale(V3()).x;
      if (u >= 0) {   // the bounce: up with a stretch, then down with a little squash, settling
        const bob = Math.sin(Math.PI * u) * (1 - 0.35 * u), sq = Math.sin(2 * Math.PI * u) * (1 - u);
        head.position.addScaledVector(axis, o.R * 0.22 * bob); head.scale.set(sc * (1 - 0.07 * sq), sc * (1 + 0.12 * sq), sc);
      } else head.scale.setScalar(sc); }
    g.updateWorldMatrix(true, true); head.lookAt(camPos);
    const hq = head.getWorldQuaternion(q);
    const right = V3(1, 0, 0).applyQuaternion(hq), upv = V3(0, 1, 0).applyQuaternion(hq), view = toCam;
    const f = p.face.clone().applyQuaternion(g.getWorldQuaternion(new THREE.Quaternion())).normalize();
    // expr may be a preset name ('flat') or a preset object; a name used to draw a face with no eyes, brows or mouth
    const ex = typeof p.expr === 'string' ? (PRE[p.expr] || PRE.calm) : (p.expr || PRE.calm);
    const c2d = cv.getContext('2d');
    drawHead(c2d, S, { ox: f.dot(right), oy: f.dot(upv), front: f.dot(view), hair: o.hair, hair2: o.hair2, style: o.style, glasses: o.glasses, extra, shape: HSHAPE }, ex);
    tex.needsUpdate = true;
    if ((g._edgeChecks = (g._edgeChecks || 0) + 1) <= 4) {   // hair and hats don't change with the expression: check the first few draws
      const edge = [c2d.getImageData(0, 0, S, 2), c2d.getImageData(0, S - 2, S, 2), c2d.getImageData(0, 0, 2, S), c2d.getImageData(S - 2, 0, 2, S)];
      for (const d of edge) for (let i = 3; i < d.data.length; i += 4) if (d.data[i] > 40) { g.clipped = true; break; }
    }
    // Limb roots are drawn ON the body like the reference's 2D strokes: on the surface facing the camera, a little in front
    // of any garment layer, inside the outline (arms at the top corners right under the head-body joint, legs just
    // above the bottom edge), so where an arm or leg starts is always visible whatever the character wears.
    const camL = g.worldToLocal(camPos.clone()), tcen = torso.position.clone(), spine = p.neck.distanceTo(p.hip);
    let nC = camL.sub(tcen); nC.addScaledVector(axis, -nC.dot(axis)); if (nC.lengthSq() < 1e-8) nC.copy(fwd); nC.normalize();
    const latC = axis.clone().cross(nC).normalize();
    const tgt = [p.arms[0], p.arms[1], p.legs[0], p.legs[1]];
    for (let i = 0; i < 4; i++) {
      const yl = i < 2 ? 0.5 * spine - o.R * 0.24 : -TH / 2 + tr * 0.32, rr = prof(yl) * 1.1 + o.R * 0.01, f = i < 2 ? 0.8 : 0.42;   // just inside the outline: arms near the sides below the head line, legs near the bottom edge
      const sgn = Math.sign(tgt[i][1].clone().sub(tcen).dot(latC)) || (i % 2 ? 1 : -1);
      const s0 = tcen.clone().addScaledVector(axis, yl).addScaledVector(latC, sgn * rr * f).addScaledVector(nC, rr * Math.sqrt(1 - f * f) + o.R * 0.015);
      ends[i].userData.cap.position.copy(s0); ends[i].userData.cap.scale.setScalar(lw);
      limbs[i].geometry.dispose();
      limbs[i].geometry = new THREE.TubeGeometry(new THREE.QuadraticBezierCurve3(s0, tgt[i][0], tgt[i][1]), 16, lw, 6, false);
      ends[i].position.copy(tgt[i][1]);
      if (i >= 2) { const fw = V3(fwd.x, 0, fwd.z); if (fw.lengthSq() < 1e-6) fw.set(1, 0, 0); fw.normalize(); ends[i].position.addScaledVector(fw, o.R * 0.07); ends[i].position.y += o.R * 0.03; ends[i].rotation.set(0, Math.atan2(-fw.z, fw.x), 0); }
    }
  };
  return g;
}
