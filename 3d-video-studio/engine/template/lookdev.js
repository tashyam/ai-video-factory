// Look sheet (step 4): one still "card" per second, so `film.mjs sheet <project> review/look.jpg 0.5 1.5 2.5 ... --page lookdev.html`
// shows the whole visual design before the storyboard: every character from cast.json in lineups of three, the lead's
// faces, the hero set (wide, medium with lens blur, a prop close-up) and the hero car. Cards are built from the same
// sets.js the video will use. Add a card for any other set or prop the visual bible calls new.
import { THREE, V3, DEG, run } from 'engine/core.js';
import { makeStage } from 'engine/stage.js';
import { addHighway } from 'engine/sets/highway.js';
import { addRoom } from 'engine/sets/room.js';
import { lacquer, blobShadow } from 'engine/materials.js';
import { buildCar } from 'engine/cars.js';
import { makeChar, stand, sitOn } from 'engine/chars.js';
import { panel } from 'engine/props.js';
import CAST from './cast.json' with { type: 'json' };
import { heroSet, withLook } from './sets.js';

const FACE_CAM = -Math.PI / 2;
function person(scn, spec) { const g = new THREE.Group(), ch = makeChar(spec); g.add(ch); scn.add(g); ch.holder = g; return ch; }
function place(ch, x, z, yaw = FACE_CAM, y = 0) { ch.holder.position.set(x, y, z); ch.holder.rotation.y = yaw; }
function aimCam(stage, pos, look, fov = 40, near = 0.1) {
  const c = stage.camera; c.position.copy(pos); c.fov = fov; c.near = near; c.updateProjectionMatrix();
  c.up.set(0, 1, 0); c.lookAt(look); c.updateMatrixWorld(true); stage.frame();
}
const HF = (fov) => 2 * Math.atan(Math.tan(fov * DEG / 2) * 1080 / 1920);   // horizontal field of view
const roles = Object.keys(CAST.characters), lead = CAST.characters.schemer ? 'schemer' : roles[0];
const shots = [], labels = [];   // labels[i] = { title, tags: [[worldPointFn, text]] }
let T = 0;
const onCard = [];   // [card index, characters]: studio characters show only on their own card
const showOnly = (t) => { for (const [i, cs] of onCard) for (const ch of cs) ch.holder.visible = Math.floor(t) === i; };
const card = (stage, update, title, extra = {}) => { const i = T++; shots.push({ start: i, end: i + 1, stage, update, grade: stage.grade, locked: true, ...extra }); labels[i] = { title, tags: extra.tags || [] }; return i; };

// ---------------------------------------------------------------- cast lineups: three per card, height chart behind
const studio = makeStage({ mood: withLook('day') });
{
  const r = addRoom(studio.scene, { kind: 'empty', w: 7, d: 3.2, h: 3.4, wall: 0xe9e2d2, floor: 'wood', window: false, seed: 3 });
  const chart = panel(4.2, 1.9, { draw: (g, W, H) => { g.fillStyle = '#e9e2d2'; g.fillRect(0, 0, W, H); g.strokeStyle = '#8a8172'; g.fillStyle = '#8a8172'; g.font = `700 ${Math.round(H * 0.035)}px Cap, sans-serif`;
    for (let k = 0; k <= 19; k++) { const y = H - (k / 19) * H; g.lineWidth = k % 5 ? 2 : 5; g.beginPath(); g.moveTo(0, y); g.lineTo(W, y); g.stroke(); if (k % 5 === 0 && k) g.fillText((k / 10).toFixed(1) + ' m', 8, y + H * 0.04); } } });
  chart.position.set(0, 0.95, -3.18); studio.scene.add(chart); lacquer(r.group);
}
const chunks = []; for (let i = 0; i < roles.length; i += 3) chunks.push(roles.slice(i, i + 3));
for (const group of chunks) {
  const chars = group.map((k) => person(studio.scene, CAST.characters[k]));
  const xs = group.map((_, j) => (j - 1) * 0.72);   // three slots, so every card has the same scale
  const idx = T; onCard.push([idx, chars]);
  const update = (t) => {
    showOnly(t); if (Math.floor(t) !== idx) return;
    const span = 0.72 * 2 + 0.62, dist = (span / 2) / Math.tan(HF(34) / 2);
    aimCam(studio, V3(0, 0.85, -1.2 + dist), V3(0, 0.66, -1.2), 34); studio.follow(0, 0, -1.2);
    chars.forEach((ch, j) => { place(ch, xs[j], -1.2); ch.pose(stand(ch, { x: 0, z: 0, arms: j === 1 ? 'hips' : 'down', face: V3(1, 0, (j - 1) * 0.25), expr: j === 1 ? 'smug' : 'flat' }), studio.camera); });
  };
  card(studio, update, 'CAST ' + (chunks.indexOf(group) + 1) + '/' + chunks.length, { look: 'studio',
    tags: chars.map((ch, j) => [() => V3(xs[j], 0.02, -1.2), [group[j], `${CAST.characters[group[j]].build || ''} · ${CAST.characters[group[j]].outfit || ''}`]]),
    marks: Object.fromEntries(chars.map((ch, j) => [group[j], { get: () => ch.headWorld(), R: ch.R, when: [idx, idx + 1], caption: false }])) });
}
// ---------------------------------------------------------------- the lead's faces (four copies, four presets)
{
  const FACES = ['smug', 'grin', 'shock', 'worried'], cs = FACES.map(() => person(studio.scene, CAST.characters[lead])), idx = T, RISER = 0.6;
  const riser = new THREE.Mesh(new THREE.BoxGeometry(1.4, RISER, 0.6), new THREE.MeshStandardMaterial({ color: 0x8a6a4a, roughness: 0.5 })); riser.position.set(0, RISER / 2, -1.6); studio.scene.add(riser); onCard.push([idx, [{ holder: riser }]]); onCard.push([idx, cs]);
  const update = (t) => {
    showOnly(t); if (Math.floor(t) !== idx) return;
    cs.forEach((ch, j) => place(ch, (j % 2 ? 0.27 : -0.27), j < 2 ? -1.6 : -1.1, FACE_CAM, j < 2 ? RISER : 0));   // a 2 x 2 group photo
    for (let pass = 0; pass < 2; pass++) {   // first pass finds the head heights
      const y = pass ? (cs[0].headWorld().y + cs[2].headWorld().y) / 2 : 1.3;
      aimCam(studio, V3(0, y, -1.35 + 0.62 / Math.tan(HF(30) / 2)), V3(0, y - 0.04, -1.35), 30);
      cs.forEach((ch, j) => ch.pose(stand(ch, { x: 0, z: 0, arms: 'down', face: V3(1, 0, 0), expr: FACES[j] }), studio.camera));
    }
  };
  card(studio, update, lead.toUpperCase() + ' FACES', { look: 'studio', tags: cs.map((ch, j) => [() => ch.headWorld().add(V3(0, -ch.R * 1.6, 0)), FACES[j]]),
    marks: { lead: { get: () => cs[1].headWorld(), R: cs[1].R, when: [idx, idx + 1], caption: false } } });
}
// ---------------------------------------------------------------- hero set: wide, medium (lens blur), prop close-up
const setStage = makeStage({ mood: withLook('day') });
const castSpecs = roles.slice(0, 4).map((k) => CAST.characters[k]);
const hero = heroSet(setStage.scene, { cast: castSpecs });
const A = person(setStage.scene, CAST.characters[lead]), B = person(setStage.scene, CAST.characters[roles.find((k) => k !== lead) || lead]);
const poseSet = () => {
  const c0 = hero.at.chairs[1]; place(A, c0.x, c0.z + 0.05);
  A.pose(sitOn(A, { x: 0, z: 0, seat: hero.items.chairs[1].children[0].position.y + 0.03, arms: 'down', face: V3(1, 0, 0.3), expr: 'smug' }), setStage.camera);
  place(B, hero.at.counter.x - 0.1, hero.at.counter.z - 0.55); B.pose(stand(B, { x: 0, z: 0, arms: 'down', face: V3(1, 0, -0.4), expr: 'flat' }), setStage.camera);
};
const setCard = (title, pos, look, fov, dof) => card(setStage, () => { aimCam(setStage, pos, look, fov); setStage.follow(0, 0, -2); poseSet(); }, title,
  { dof, marks: { lead: { get: () => A.headWorld(), R: A.R, caption: false } } });
setCard('SET · WIDE', V3(-0.3, 1.35, 3.1), V3(-0.3, 1.3, -2.4), 52, null);
setCard('SET · MEDIUM (BLUR 10)', V3(-0.55, 0.95, 0.5), V3(-0.95, 0.72, -1.55), 38, { cInf: 10, focus: 'lead' });
card(setStage, () => { const p = hero.items.pegboard.getWorldPosition(V3()); aimCam(setStage, V3(p.x + 1.9, p.y - 0.15, p.z + 0.95), V3(p.x, p.y - 0.1, p.z - 0.1), 46); poseSet(); },
  'PROP · CLOSE-UP (BLUR 14)', { dof: { cInf: 14, focus: () => 2.0 }, marks: { prop: { get: () => hero.items.pegboard.getWorldPosition(V3()), size: 1.4, caption: false } } });
// ---------------------------------------------------------------- hero car (skip if the story has none)
if (CAST.cars && Object.keys(CAST.cars).length) {
  const carStage = makeStage({ mood: withLook('day', 'outdoor') });
  addHighway(carStage.scene);
  const k = CAST.cars.schemer ? 'schemer' : Object.keys(CAST.cars)[0], car = buildCar(CAST.cars[k]); car.position.set(0, 0, 5.55); car.add(blobShadow(5.6, 2.9)); carStage.scene.add(car);
  card(carStage, () => { aimCam(carStage, V3(6.6, 1.7, 13.6), V3(0.2, 0.75, 5.55), 36); carStage.follow(0, 0, 5.55); }, 'CAR · ' + k.toUpperCase(),
    { marks: { car: { get: () => V3(0, 0.8, 5.55), size: 5, caption: false } } });
}

// ---------------------------------------------------------------- labels (2D, on top of every card)
const tmp = new THREE.Vector3();
run({
  shots,
  captions: [[0, '']],
  overlay: (ctx, t) => {
    const i = Math.min(labels.length - 1, Math.floor(t)), L = labels[i], cam = shots[i].stage.camera;
    ctx.save(); ctx.textAlign = 'center'; ctx.lineJoin = 'round';
    ctx.font = '800 64px Cap, sans-serif'; ctx.lineWidth = 12; ctx.strokeStyle = '#111'; ctx.fillStyle = '#fff';
    ctx.strokeText(L.title, 540, 130); ctx.fillText(L.title, 540, 130);
    ctx.font = '800 34px Cap, sans-serif'; ctx.lineWidth = 8;
    for (const [fn, text] of L.tags) { tmp.copy(fn()).project(cam); const x = (tmp.x + 1) / 2 * 1080, y = (1 - tmp.y) / 2 * 1920 + 50;
      [].concat(text).forEach((line, k) => { ctx.font = `800 ${k ? 26 : 34}px Cap, sans-serif`; ctx.strokeText(line, x, y + k * 36); ctx.fillText(line, x, y + k * 36); }); }
    ctx.restore();
  },
});
