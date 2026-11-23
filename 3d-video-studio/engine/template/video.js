// Template video: the approved 5 s opener (interior → fly-out through the windshield → rear-end collision).
// This is the only kind of file to write per video: build stages from the engine, describe motion as pure
// functions of time, list the shots. Copy a shot block to start a new one.
import { THREE, V3, clamp, lerp, ease, DEG, table, track, run } from 'engine/core.js';
import { makeStage } from 'engine/stage.js';
import { addHighway } from 'engine/sets/highway.js';
import { M, paint, blobShadow } from 'engine/materials.js';
import { makeCar, addInterior, tintGlass, rollWheels, brakeLights, COUPE, SUV, IC, IS } from 'engine/cars.js';
import { makeChar, exprAt } from 'engine/chars.js';
import { puffs, tyreSmoke, skids, skid, debris, lightMats } from 'engine/fx.js';

// ------------------------------------------------------------------ shot 1: the brake check (0 to 5 s)
const st = makeStage({ mood: 'day' });
const { scene, camera } = st;
addHighway(scene);
const LANE = 5.55;

const coupe = makeCar(COUPE, 0xffbf0a); addInterior(coupe, IC, true); scene.add(coupe);
const suv = makeCar(SUV, 0xbfe9dc); addInterior(suv, IS, false); scene.add(suv);
const lead = makeChar({ R: 0.195, shirt: 0x7a45e0, hair: '#1c1c24', hair2: '#3a3a48', style: 'mess' }); coupe.body.add(lead);
const victim = makeChar({ R: 0.215, shirt: 0xff6a3d, hair: '#d9722b', hair2: '#f09a52', style: 'bowl', glasses: true }); suv.body.add(victim);
// background traffic: [car, lane z, x at t=0, speed m/s]
const traffic = [[makeCar(COUPE, 0x2f6fe0), 1.85, 34, 29.5], [makeCar(SUV, 0x8f97a6), -1.85, -46, 31.5], [makeCar(COUPE, 0xf2f2f2), -5.55, 70, 27]];
for (const [c] of traffic) { tintGlass(c); scene.add(c); }
for (const [car, L, Wd] of [[coupe, 5.6, 2.9], [suv, 6.3, 3.2], [traffic[0][0], 5.6, 2.9], [traffic[1][0], 6.3, 3.2], [traffic[2][0], 5.6, 2.9]]) car.add(blobShadow(L, Wd));

// kinematics: lead brakes at TB, rear driver reacts at TN, impact at TI. xRef = lead without the impact kick
// (the camera follows it, so the camera does not jerk on impact).
const TB = 0.32, TN = 2.6, TI = 3.9, DUR = 5;
const L_ = table(DUR), R_ = table(DUR), S_ = table(DUR);
{
  let x = 0, v = 26, xr = 0, vr = 26, xs = 0, vs = 27, hitL = false, hitS = false;
  for (let i = 0; i < L_.n; i++) {
    const t = i * L_.dt; L_.arr[i] = x; R_.arr[i] = xr; S_.arr[i] = xs;
    let a = 0; if (t >= TI) { if (!hitL) { v = 9.8; hitL = true; } a = v > 0 ? -8.0 : 0; } else if (t >= TB) a = v > 7 ? -9.5 : -0.4;
    v = Math.max(0, v + a * L_.dt); x += v * L_.dt;
    let ar = 0; if (t >= TI) ar = vr > 0 ? -2.56 : 0; else if (t >= TB) ar = vr > 7 ? -9.5 : -0.4;
    vr = Math.max(0, vr + ar * L_.dt); xr += vr * L_.dt;
    let as = 0; if (t >= TI) { if (!hitS) { vs = 9.4; hitS = true; } as = vs > 0 ? -8.4 : 0; } else if (t >= TN) as = -10.5;
    vs = Math.max(0, vs + as * L_.dt); xs += vs * L_.dt;
  }
  const iI = Math.round(TI / L_.dt), shift = L_.arr[iI] - 2.13 - 2.40 + 0.07 - S_.arr[iI];
  for (let i = 0; i < S_.n; i++) S_.arr[i] += shift;
}
const xL = L_.at, xRef = R_.at, xS = S_.at;

const P = puffs(scene, 230), SK = skids(scene, 4);
const DB = debris(scene, [paint(0xffbf0a), lightMats.tail(), M.trim, lightMats.glassShard()], 30, 99);

//      t     px    py    pz     lx     ly    lz   roll  fov     (relative to the lead car)
const CAM = track([
  [0.00, 0.40, 0.50, 0.62, 0.30, 0.72, -0.40, 15, 106],
  [1.05, 0.44, 0.55, 0.60, 0.28, 0.76, -0.40, 12, 106],
  [1.30, 0.60, 1.00, 0.24, -0.25, 1.00, -0.38, 5, 100],
  [1.50, 1.00, 1.14, 0.06, -0.28, 1.00, -0.36, 2, 90],
  [1.72, 2.70, 1.24, 0.22, -0.25, 0.96, -0.30, 0, 70],
  [2.05, 5.60, 1.22, 0.90, -1.00, 0.90, 0.00, 0, 54],
  [2.75, 8.60, 1.45, 2.20, -3.60, 0.95, 0.00, 0, 48],
  [3.50, 7.60, 1.40, 4.10, -1.90, 0.92, 0.00, 0, 46],
  [3.90, 6.60, 1.32, 4.60, -1.20, 0.90, 0.00, 0, 44],
  [5.00, 5.80, 1.22, 4.50, -1.15, 0.90, 0.00, 0, 41],
]);
const LEAD_EXPR = [[0, 'smug'], [0.30, 'grit'], [0.92, 'grin'], [3.90, 'jolt'], [4.35, 'grin']];
const VIC_EXPR = [[0, 'calm'], [2.42, 'shock'], [3.92, 'jolt'], [4.3, 'dazed']];

function update1(t) {
  const xl = xL(t), xs = xS(t), xr = xRef(t), ti = t - TI;
  // cars: brake dive, wheels, lights, crumpled bumpers
  const diveL = -2.7 * ease(TB, TB + 0.2, t) * (1 - 0.8 * ease(2.2, 2.6, t)) + (ti > 0 ? 3.2 * Math.exp(-5 * ti) * Math.cos(13 * ti) : 0);
  const diveS = -3.3 * ease(TN, TN + 0.2, t) * (1 - 0.9 * ease(TI + 0.5, TI + 1.0, t)) + (ti > 0 ? -2.5 * Math.exp(-5 * ti) * Math.cos(11 * ti) : 0);
  coupe.position.set(xl, 0, LANE); coupe.body.rotation.z = diveL * DEG;
  suv.position.set(xs, 0, LANE); suv.body.rotation.z = diveS * DEG;
  const lockL = t > TB && t < 1.3; rollWheels(coupe, lockL ? xL(TB) + (xL(t) - xL(TB)) * 0.15 : xl);
  rollWheels(suv, t > TN ? xS(TN) : xs);
  brakeLights(coupe, t > TB); brakeLights(suv, t > TN);
  if (ti > 0) { const k = 1 - Math.exp(-9 * ti); coupe.bumperR.rotation.x = 0.5 * k; coupe.bumperR.position.y = COUPE.yb + 0.13 - 0.12 * k; coupe.bumperR.rotation.y = 0.09 * k; suv.bumperF.rotation.x = -0.12 * k; suv.bumperF.position.y = SUV.yb + 0.13 - 0.05 * k; }
  else { coupe.bumperR.rotation.set(0, 0, 0); coupe.bumperR.position.y = COUPE.yb + 0.13; suv.bumperF.rotation.set(0, 0, 0); suv.bumperF.position.y = SUV.yb + 0.13; }
  for (const [c, z, x0, v] of traffic) { c.position.set(x0 + v * t, 0, z); for (const w of c.wheels) w.rotation.z = -(v * t) / 0.34; }
  // interior props: pedal, rolling can, swinging charm, phone sliding into the footwell
  const tb = t - TB;
  coupe.brake.rotation.z = 0.30 * ease(0.38, 0.47, t);
  { const cx = 0.14 + 0.78 * ease(0.36, 0.92, t) - 0.07 * ease(0.92, 1.25, t); coupe.can.position.set(cx, 0.283 + 0.033, 0.24 + 0.05 * ease(0.36, 0.92, t)); coupe.can.rotation.z = -(cx - 0.14) / 0.033; }
  coupe.charm.rotation.z = tb > 0 ? (0.75 * (1 - Math.exp(-5 * tb) * Math.cos(9 * tb))) * (1 - 0.8 * ease(2.2, 2.7, t)) : 0.03 * Math.sin(t * 9);
  {
    const u = clamp((t - 0.37) / 0.26), sx = -0.10 + 0.22 * u * u, f = clamp((t - 0.63) / 0.34);
    const px = sx + 0.30 * f, py = 0.492 - (0.492 - 0.272) * f * f + Math.sin(f * Math.PI) * 0.03;
    coupe.phone.position.set(px, py, 0.40 - 0.05 * f); coupe.phone.rotation.set(f * 0.5, 0.35 + u * 0.5 + f * 1.2, -f * (1 - f) * 2.4);
  }
  // camera, relative to the smoothed lead car; locked to the real car while inside it
  const k = CAM(t), shake = ti > 0 ? Math.exp(-7 * ti) * 0.09 : 0;
  camera.position.set(xr + k[0] + shake * Math.sin(ti * 71), k[1] + shake * Math.sin(ti * 93 + 1), LANE + k[2] + shake * Math.sin(ti * 57 + 2));
  if (t < 1.75) camera.position.x += xl - xr;
  camera.fov = k[7]; camera.near = t < 1.8 ? 0.03 : 0.25; camera.updateProjectionMatrix();
  camera.up.set(0, 1, 0); camera.lookAt(xr + (t < 1.75 ? xl - xr : 0) + k[3], k[4], LANE + k[5]); camera.rotateZ(k[6] * DEG);
  camera.updateMatrixWorld(true);
  st.frame(); st.follow(xr - 5, 0, LANE);
  // lead driver
  const lean = (-0.10 + 0.34 * ease(TB, TB + 0.16, t) - 0.20 * ease(0.62, 1.2, t)) + (ti > 0 ? -0.45 * Math.exp(-6 * ti) * Math.cos(10 * ti) : 0);
  const hip = V3(-0.20, 0.53, -0.38), neck = hip.clone().add(V3(Math.sin(lean) * 0.30, Math.cos(lean) * 0.30, 0));
  const wr = coupe.wheelRig, hL = wr.rimPoint(Math.PI - 0.55), hR = wr.rimPoint(0.55);
  const stp = ease(0.26, 0.36, t), push = ease(0.38, 0.47, t);
  const foot = V3(lerp(0.90, 0.885, stp) + 0.075 * push, lerp(0.37, 0.385, stp) + Math.sin(stp * Math.PI) * 0.09 - 0.025 * push, lerp(-0.25, -0.41, stp));
  const look = t < 0.28 ? V3(0.75, 0.45, 0.5) : (ti > 0.45 ? V3(0.8, 0.05, 0.6) : V3(1, 0.0, 0.18));
  lead.pose({ hip, neck, face: look, expr: exprAt(LEAD_EXPR, t),
    arms: [[V3(0.10, 0.62, -0.60), hL], [V3(0.10, 0.62, -0.16), hR]],
    legs: [[V3(0.36, 0.60, -0.50), V3(0.80, 0.30, -0.56)], [V3(0.36, 0.66, -0.33), foot]] }, camera);
  // rear driver
  const vl = (ti > 0 ? 0.5 * Math.exp(-6 * ti) * Math.cos(9 * ti) : 0) + 0.12 * ease(TN, TN + 0.15, t);
  const vh = V3(0.24, 0.80, -0.42), vn = vh.clone().add(V3(Math.sin(vl) * 0.33, Math.cos(vl) * 0.33, 0)), sw = suv.wheelRig;
  const brace = ease(2.45, 2.6, t);
  victim.pose({ hip: vh, neck: vn, face: V3(1, -0.05, 0), expr: exprAt(VIC_EXPR, t),
    arms: [[V3(0.55, lerp(0.95, 1.2, brace), -0.68), sw.rimPoint(Math.PI - 0.6)], [V3(0.55, lerp(0.95, 1.2, brace), -0.18), sw.rimPoint(0.6)]],
    legs: [[V3(0.75, 0.80, -0.52), V3(1.25, 0.52, -0.55)], [V3(0.75, 0.84, -0.34), V3(1.28, 0.56, -0.38)]] }, camera);
  // smoke, skids, debris
  P.begin();
  tyreSmoke(P, xS, t, TN + 0.02, TI + 0.25, 0.02, [1.5, -1.45], 0.84, 0.55, LANE);
  tyreSmoke(P, xL, t, TB + 0.03, 1.3, 0.06, [1.28, -1.25], 0.75, 0.30, LANE);
  for (let te = TI + 0.12, j = 0; te < t; te += 0.07, j++) { const age = t - te; if (age > 1.4) continue; P.add(xS(t) + 2.25 + 0.3 * age, 0.95 + 1.3 * age, LANE + (j % 3 - 1) * 0.35, 0.45 + 1.5 * age, 0.38 * Math.min(1, age / 0.1) * (1 - age / 1.4), 0xffffff); }
  if (ti > 0 && ti < 0.9) for (let j = 0; j < 10; j++) { const an = j * 0.7; P.add(xL(t) - 2.13 + Math.cos(an) * (0.3 + 2.0 * ti), 0.55 + (0.5 + (j % 3) * 0.5) * ti, LANE + Math.sin(an) * (0.5 + 2.2 * ti), 0.8 + 3.2 * ti, 0.6 * (1 - ti / 0.9), 0xfff4d6); }
  P.end();
  skid(SK[0], xS, t, TN, TI + 0.9, -1.45, LANE - 0.84, 1.1); skid(SK[1], xS, t, TN, TI + 0.9, -1.45, LANE + 0.84, 1.1);
  skid(SK[2], xL, t, TB, 1.3, -1.25, LANE - 0.75, 0.9); skid(SK[3], xL, t, TB, 1.3, -1.25, LANE + 0.75, 0.9);
  DB.update(ti, xL(TI) - 2.13, LANE);
}

// ------------------------------------------------------------------ the edit
run({
  shots: [
    { start: 0, end: 5, stage: st, update: update1, grade: st.grade,
      marks: {
        'lead.head': { get: () => lead.headWorld(), R: lead.R, when: [0, 1.2], y: [0.25, 0.55] },
        'brake pedal': { get: () => coupe.brakePad.getWorldPosition(V3()), when: [0.3, 1.0], caption: false },
        'lead car': { get: () => coupe.getWorldPosition(V3()).setY(0.8), when: [2.2, 5], caption: false },
        'rear car': { get: () => suv.getWorldPosition(V3()).setY(1.0), when: [2.4, 5], caption: false },
        'rear.head': { get: () => victim.headWorld(), R: victim.R, when: [2.6, 5] },
      } },
  ],
  captions: [[0.00, 'One'], [0.18, 'driver'], [0.50, 'stomps'], [0.95, 'the brakes'], [1.35, 'on an'], [1.60, 'open'], [1.85, 'highway,'], [2.35, 'and'], [2.55, 'the car'], [2.90, 'behind'], [3.25, 'has'], [3.45, 'nowhere'], [3.90, 'to go.']],
  samples: (t) => (t < 1.2 ? 1 : t <= 2.15 ? 5 : 3),   // motion blur sub-frames: 1 inside the car, 5 in the fly-out, 3 outside
});
