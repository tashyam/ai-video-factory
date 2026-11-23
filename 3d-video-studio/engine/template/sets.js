// The video's sets, built once and shared by the look sheet (lookdev.js, step 4) and the video (video.js, step 8), so
// the detail approved on the look sheet is exactly the detail in the video. Write one function per set from the visual
// bible; every one returns { group, at, items } like addRoom.
//
// heroSet() below is the WORKED EXAMPLE of the house look (look/style-guide.md): a lobby dressed to the reference
// density. Replace it with the story's busiest set, and keep the same layers:
//   back wall in one saturated colour + a band + a wood wainscot, a title sign, 4-8 readable wall items (frames, posters,
//   pegboard), visible light sources (pendants), a patterned floor with a centre emblem, a tiled ceiling, furniture in
//   complementary colours, and lacquer() over all of it.
import { THREE, V3, rng, canvas, ctex } from 'engine/core.js';
import { addRoom } from 'engine/sets/room.js';
import { flat, box, lacquer } from 'engine/materials.js';
import { sign, frame, pendant, chair, plant, panel, counterUnit } from 'engine/props.js';

// The house look for every mood: heavier ink on everything in focus, hard edges inked too (indoors), soft contact
// shadows, warm light pools and a little vignette. Pass it to makeStage: makeStage({ mood: withLook('day') }).
import { MOODS } from 'engine/stage.js';
export const LOOK = {
  indoor: { ink: 1.0, inkWidth: [3.6, 1.6], inkCrease: [48, 62], inkId: 0.6, ao: 0.7, aoRadius: 0.4, bloom: 0.9, vignette: [0.18, 0.42] },
  outdoor: { ink: 0.95, inkWidth: [3.0, 1.4], inkCrease: null, vignette: [0.14, 0.45] },   // no crease lines outdoors: they ink every leaf
};
export const withLook = (mood, where = 'indoor') => ({ ...MOODS[mood], name: mood, paint: { ...MOODS[mood].paint, ...LOOK[where] } });

// Speckled terrazzo floor with coloured chips (reference: police lobby floor).
function terrazzo(seed = 3, base = '#ece8df', chips = ['#2f9e9a', '#e0574a', '#f2c230', '#3b5aa8', '#9aa0a8']) {
  const S = 1024, c = canvas(S, S), g = c.getContext('2d'), r = rng(seed);
  g.fillStyle = base; g.fillRect(0, 0, S, S);
  for (let i = 0; i < 5200; i++) { g.fillStyle = chips[Math.floor(r() * chips.length)]; g.globalAlpha = 0.45 + r() * 0.5;
    const x = r() * S, y = r() * S, s = 2 + r() * 6; g.beginPath(); g.ellipse(x, y, s, s * (0.5 + r() * 0.5), r() * 3, 0, 6.29); g.fill(); }
  g.globalAlpha = 1; g.strokeStyle = 'rgba(120,110,95,0.35)'; g.lineWidth = 3; for (let k = 0; k <= S; k += 256) { g.strokeRect(k, 0, 0, S); g.strokeRect(0, k, S, 0); }
  return ctex(c, [3, 3]);
}
function ceilingTiles() {
  const c = canvas(512, 512), g = c.getContext('2d'); g.fillStyle = '#efece4'; g.fillRect(0, 0, 512, 512);
  g.strokeStyle = '#c9c4b6'; g.lineWidth = 6; for (let k = 0; k <= 512; k += 128) { g.beginPath(); g.moveTo(k, 0); g.lineTo(k, 512); g.moveTo(0, k); g.lineTo(512, k); g.stroke(); }
  return ctex(c, [4, 4]);
}
// A poster with a bold title and a simple picture (every printed thing in the reference is a real little design).
const poster = (title, bg, fg, pic) => panel(0.42, 0.56, { draw: (g, W, H) => {
  g.fillStyle = bg; g.fillRect(0, 0, W, H); g.fillStyle = fg; g.font = `800 ${Math.round(H * 0.09)}px Cap, sans-serif`; g.textAlign = 'center';
  g.fillText(title, W / 2, H * 0.14); g.fillStyle = '#ffffff'; g.fillRect(W * 0.12, H * 0.22, W * 0.76, H * 0.5); pic(g, W, H);
  g.fillStyle = fg; for (let i = 0; i < 3; i++) g.fillRect(W * 0.18, H * (0.79 + i * 0.05), W * (0.64 - i * 0.12), H * 0.02);
  g.strokeStyle = '#1b1712'; g.lineWidth = W * 0.03; g.strokeRect(0, 0, W, H); } });
// Pegboard with hanging packs (reference: shop wall). n packs in rows; colours from `cols`.
const pegboard = (w, h, cols) => panel(w, h, { draw: (g, W, H) => {
  g.fillStyle = '#c99a62'; g.fillRect(0, 0, W, H); g.fillStyle = 'rgba(60,35,15,0.45)';
  for (let x = W * 0.04; x < W; x += W * 0.06) for (let y = H * 0.04; y < H; y += H * 0.06) { g.beginPath(); g.arc(x, y, W * 0.006, 0, 6.29); g.fill(); }
  const cw = W * 0.2, ch = H * 0.27;
  for (let i = 0; i < 4; i++) for (let j = 0; j < 3; j++) { const x = W * 0.06 + i * W * 0.23, y = H * 0.07 + j * H * 0.31;
    const col = cols[(i + j) % cols.length], lx = x + cw / 2, ly = y + ch * 0.6;
    g.fillStyle = col; g.fillRect(x, y, cw, ch); g.fillStyle = '#f4f1ea'; g.fillRect(x + cw * 0.1, y + ch * 0.3, cw * 0.8, ch * 0.6);   // card + clear window
    g.fillStyle = '#ffffff'; g.font = `800 ${Math.round(ch * 0.15)}px Cap, sans-serif`; g.textAlign = 'center'; g.fillText(['SNAP', 'ZIP', 'BOLT', 'GLOW'][(i + j) % 4], lx, y + ch * 0.22);
    g.fillStyle = col; g.beginPath(); g.ellipse(lx, ly, cw * 0.27, ch * 0.11, -0.35, 0, 6.29); g.fill(); g.strokeStyle = '#1b1712'; g.lineWidth = W * 0.005; g.stroke();   // the lure
    g.fillStyle = '#ffffff'; g.beginPath(); g.arc(lx - cw * 0.16, ly - ch * 0.02, cw * 0.05, 0, 6.29); g.fill(); g.fillStyle = '#1b1712'; g.beginPath(); g.arc(lx - cw * 0.16, ly - ch * 0.02, cw * 0.022, 0, 6.29); g.fill();
    g.beginPath(); g.arc(lx + cw * 0.2, ly + ch * 0.17, cw * 0.06, 0, 3.4); g.stroke();   // hook
    g.fillStyle = '#e0574a'; g.beginPath(); g.arc(x + cw * 0.84, y + ch * 0.36, cw * 0.11, 0, 6.29); g.fill(); g.fillStyle = '#fff'; g.font = `800 ${Math.round(ch * 0.08)}px Cap, sans-serif`; g.fillText('$4', x + cw * 0.84, y + ch * 0.385);
    g.strokeStyle = '#1b1712'; g.lineWidth = W * 0.007; g.strokeRect(x, y, cw, ch); g.fillStyle = '#5a5248'; g.beginPath(); g.arc(lx, y - H * 0.012, W * 0.008, 0, 6.29); g.fill(); }
  g.strokeStyle = '#1b1712'; g.lineWidth = W * 0.012; g.strokeRect(0, 0, W, H); } });

export function heroSet(scene, o = {}) {
  const w = o.w ?? 6.4, d = o.d ?? 4.6, h = o.h ?? 3.3, cast = o.cast ?? [];
  const room = addRoom(scene, { kind: 'empty', w, d, h, wall: o.wall ?? 0xf0c43a, floor: 'tile', window: false, light: false, seed: o.seed ?? 7 });
  const G = room.group, at = room.at, items = room.items;
  G.traverse((m) => { if (m.isMesh && m.geometry.type === 'PlaneGeometry' && Math.abs(m.rotation.x + Math.PI / 2) < 0.01) m.material = new THREE.MeshStandardMaterial({ map: terrazzo(), roughness: 0.35 }); });
  const ceil = new THREE.Mesh(new THREE.PlaneGeometry(w, d + 0.6), new THREE.MeshStandardMaterial({ map: ceilingTiles(), roughness: 0.9 })); ceil.rotation.x = Math.PI / 2; ceil.position.set(0, h - 0.002, -d / 2 + 0.3); G.add(ceil);
  // wall layers: wood wainscot to 0.9 m with a cap rail, a white stripe, a teal band at 0.9-1.05 m
  const wood = flat(0xb7834d, 0.5), cap = flat(0x8a5a30, 0.45);
  G.add(box(w, 0.9, 0.04, wood, 0, 0.45, -d + 0.02)); G.add(box(w, 0.05, 0.07, cap, 0, 0.92, -d + 0.035));
  G.add(box(w, 0.14, 0.02, flat(0x2f9e9a, 0.5), 0, 1.02, -d + 0.012)); G.add(box(w, 0.025, 0.022, flat(0xf4f1ea, 0.5), 0, 1.105, -d + 0.013));
  for (const s of [-1, 1]) { G.add(box(0.04, 0.9, d, wood, s * (w / 2 - 0.02), 0.45, -d / 2)); G.add(box(0.07, 0.05, d, cap, s * (w / 2 - 0.035), 0.92, -d / 2)); }
  // title sign and a row of framed portraits of the cast (gag slot: what the wall celebrates)
  const title = sign(o.title ?? 'WALL OF FAME', { post: false, w: 2.6, h: 0.42, bg: '#f0c43a', fg: '#1d2f6b' }); title.position.set(0, 2.72, -d + 0.03); G.add(title); items.title = title;
  items.frames = [];
  const fx = [-2.35, -1.3, 1.3, 2.35];
  fx.forEach((x, i) => { const who = cast[i % Math.max(1, cast.length)] ?? { shirt: 0x7a45e0 };
    const f = frame({ photoOf: { ...who, bg: ['#d7ecff', '#ffe0c8', '#d9f2dc', '#f2d9f0'][i] } }); f.position.set(x, 1.95, -d + 0.03); G.add(f); items.frames.push(f); });
  // a door in the middle of the back wall (frame + panel), a pegboard and a poster on the side walls, a red alarm box
  const doorM = flat(0xdfe6ea, 0.4), jamb = flat(0x3b4a5a, 0.4);
  G.add(box(0.95, 2.05, 0.03, doorM, 0, 1.025, -d + 0.03)); G.add(box(0.07, 2.12, 0.06, jamb, -0.51, 1.06, -d + 0.04)); G.add(box(0.07, 2.12, 0.06, jamb, 0.51, 1.06, -d + 0.04)); G.add(box(1.09, 0.07, 0.06, jamb, 0, 2.1, -d + 0.04));
  G.add(box(0.03, 0.03, 0.05, flat(0xc9ccd2, 0.2), 0.36, 1.0, -d + 0.06));
  const peg = pegboard(1.3, 0.95, ['#2f7de0', '#e0574a', '#f2c230', '#31a36b']); peg.position.set(-w / 2 + 0.03, 1.75, -d * 0.45); peg.rotation.y = Math.PI / 2; G.add(peg); items.pegboard = peg;
  const pst = poster('SAFETY FIRST', '#2f9e9a', '#ffffff', (g, W, H) => { g.fillStyle = '#e0574a'; g.beginPath(); g.arc(W / 2, H * 0.47, W * 0.2, 0, 6.29); g.fill(); g.fillStyle = '#1b1712'; g.fillRect(W * 0.47, H * 0.36, W * 0.06, H * 0.13); g.fillRect(W * 0.47, H * 0.52, W * 0.06, H * 0.04); });
  pst.position.set(w / 2 - 0.03, 1.8, -d * 0.55); pst.rotation.y = -Math.PI / 2; G.add(pst); items.poster = pst;
  G.add(box(0.12, 0.16, 0.05, new THREE.MeshStandardMaterial({ color: 0xd9342b, roughness: 0.3 }), 1.0, 1.45, -d + 0.04));
  const clock = panel(0.36, 0.36, { draw: (g, W) => { g.fillStyle = '#ffffff'; g.beginPath(); g.arc(W / 2, W / 2, W * 0.47, 0, 6.29); g.fill(); g.strokeStyle = '#1b1712'; g.lineWidth = W * 0.05; g.stroke();
    g.lineWidth = W * 0.035; g.lineCap = 'round'; for (let k = 0; k < 12; k++) { const a = k * Math.PI / 6; g.beginPath(); g.moveTo(W / 2 + Math.cos(a) * W * 0.36, W / 2 + Math.sin(a) * W * 0.36); g.lineTo(W / 2 + Math.cos(a) * W * 0.41, W / 2 + Math.sin(a) * W * 0.41); g.stroke(); }
    g.beginPath(); g.moveTo(W / 2, W / 2); g.lineTo(W / 2, W * 0.2); g.moveTo(W / 2, W / 2); g.lineTo(W * 0.68, W * 0.56); g.stroke(); } });
  clock.material.transparent = true; clock.position.set(-1.85, 2.62, -d + 0.03); G.add(clock); items.clock = clock;
  // furniture in complementary colours: a row of chairs, a reception counter, a plant
  const chairCols = [0xe0574a, 0x2f9e9a, 0xe0574a, 0x2f9e9a];
  items.chairs = chairCols.map((c, i) => { const ch = chair({ color: c }); ch.position.set(-1.6 + i * 0.62, 0, -d * 0.32); G.add(ch); return ch; });
  const ctr = counterUnit({ w: 1.5, color: 0x1d2f6b }); ctr.position.set(1.9, 0, -d * 0.55); G.add(ctr); items.counter = ctr;
  const bell = new THREE.Mesh(new THREE.SphereGeometry(0.05, 20, 10, 0, 6.29, 0, Math.PI / 2), new THREE.MeshStandardMaterial({ color: 0xd8c27a, metalness: 0.9, roughness: 0.2 })); bell.position.set(1.7, ctr.top, -d * 0.55 + 0.12); G.add(bell); items.bell = bell;
  const pl = plant({ h: 1.1 }); pl.position.set(-w / 2 + 0.45, 0, -d + 0.45); G.add(pl);
  // floor emblem: a gold star in a teal ring (decal just above the floor)
  const em = canvas(512, 512), eg = em.getContext('2d'); eg.fillStyle = '#2f9e9a'; eg.beginPath(); eg.arc(256, 256, 250, 0, 6.29); eg.fill(); eg.fillStyle = '#ece8df'; eg.beginPath(); eg.arc(256, 256, 205, 0, 6.29); eg.fill();
  eg.fillStyle = '#f2c230'; eg.strokeStyle = '#1b1712'; eg.lineWidth = 8; eg.beginPath(); for (let i = 0; i < 10; i++) { const a = -Math.PI / 2 + i * Math.PI / 5, rr = i % 2 ? 80 : 190; eg.lineTo(256 + Math.cos(a) * rr, 256 + Math.sin(a) * rr); } eg.closePath(); eg.fill(); eg.stroke();
  const decal = new THREE.Mesh(new THREE.PlaneGeometry(1.5, 1.5), new THREE.MeshStandardMaterial({ map: ctex(em), transparent: true, roughness: 0.3, polygonOffset: true, polygonOffsetFactor: -4 })); decal.rotation.x = -Math.PI / 2; decal.position.set(0.3, 0.003, -d * 0.62); G.add(decal);
  // visible light sources: two pendants (warm pools), plus a soft fill so the corners are not black
  for (const x of [-0.85, 0.95]) { const p = pendant({ color: 0xf4f1ea, r: 0.26, cord: 0.4, intensity: 7, range: 6 }); p.position.set(x, h, -d * 0.3); G.add(p); }
  const fill = new THREE.PointLight(0xfff0dc, 10, 10, 1.2); fill.position.set(0, h * 0.6, -0.4); G.add(fill);
  at.chairs = items.chairs.map((c) => c.getWorldPosition(V3())); at.counter = ctr.getWorldPosition(V3()); at.door = V3(0, 0, -d + 0.3).add(G.position);
  lacquer(G);   // the glassy coat on everything solid
  return room;
}
