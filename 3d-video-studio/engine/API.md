# Engine API

Read this instead of the engine source. A video is a folder with `index.html` (copy from `template/`) and
`video.js`. Imports use `engine/...`. Units are metres; car-local axes +x forward, +y up, +z right.
`template/video.js` is a complete worked shot (the approved 5 s opener): copy blocks from it.

## core.js
| Export | Use |
|---|---|
| `THREE, V3, clamp, lerp, smooth, ease(t0, t1, t), DEG, rng(seed), canvas(w, h), ctex(canvas, repeat?)` | helpers |
| `W, H, FPS` | 1080, 1920, 30 |
| `table(dur, dt?)` → `{arr, n, dt, at(t)}` | precomputed 1-D motion; fill `arr[i]` for time `i*dt`, read with `at(t)` |
| `track(keys)` → `(t) => [px,py,pz,lx,ly,lz,rollDeg,fov]` | camera keys `[t, px, py, pz, lookX, lookY, lookZ, roll, fov]`, cubic Hermite |
| `aim(camera, k, base)` | place a camera from one `track` sample, relative to world point `base` |
| `run({shots, captions, samples?, overlay?})` | starts the page; see below |

**Shots:** `{start, end, stage, update(t, lt), type?, grade?, in?: {type: 'dissolve', frames, slow?}, marks?, dof?, bed?, locked?}`
- `update` must be a pure function of time (a render may start anywhere; dissolves call the outgoing shot past its end).
- `in: {type: 'dissolve', frames: 5..12}` blends from the previous shot, centred on `start` (reference: 5-9 frames on
  time jumps). `slow: true` allows up to 18 frames, only for the reveal or the final calm act. A hard cut needs no `in`.
- Motion blur never crosses a cut: every sub-frame is clamped into the time range of the shot it draws (that range is
  widened by half a dissolve on a side that dissolves), so the frames next to a hard cut are never a mix of both shots.
- `type`: the setup, one of `interior pov tracking house twoshot talker device wide`. It sets the head-width range
  (head width / frame width) the check wants for the shot's **hero** head: talker 0.35-0.65, device (a face filling a
  camera view) 0.5-0.8, twoshot 0.15-0.35, interior 0.2-0.4, house 0.08-0.15, wide 0.06-0.12; tracking and pov have
  none. Give every shot a type.
- `grade`: CSS filter for the shot (use `stage.grade`).
- `marks`: `{name: {get: () => Vector3 world, R?, size?, when?: [t0, t1], y?: [a, b], w?: [a, b], caption?: false, hero?: true}}` for
  `film.mjs check`: off frame / behind camera / near-plane clipping fail; caption band (66–76%), side edge, `y`
  range and head width `w` (with `R`) warn per probe. Give every face a mark. The hero mark is the one with
  `hero: true`, else the first head mark (with `R`) that is not `caption: false`; an explicit `w` on it beats the type's range. `size` (things without `R`, default 2.5 m) is the
  marked thing's own extent, so a car's body does not count as hiding the car.
- `dof: { cInf, focus, max? }`: lens blur (see "The look"). `bed`: the shot's ambience (see "Sound").
  `locked: true`: a deliberate locked-off camera (the dash cam's own view), so the camera-motion rule skips the shot.

**What `film.mjs check` tests** (geometry only, no pixels; run it over the whole video before every sheet). It ends
with a `FAIL rules:` line (each failing rule and its count) and exits with code 1 when anything FAILs (0 otherwise), so a
pipeline step can stop on it. `--verbose` also prints one info line per shot (camera %/s, hero head width).
- every mark: in frame, not behind the camera or clipped, and **not hidden**: a ray from the lens to the face that hits
  an opaque object first is a FAIL within 2.5 m of the lens, a WARN further away (it names the object and its position);
- **covered frame**: one surface within 2 m of the lens covering 40 % (WARN) or 55 % (FAIL) of a 6x10 ray grid: a
  panel, a wall, or the inside of a car body;
- **signs**: every readable `sign()` (wider than 10 % of the frame, facing the camera) must be fully inside the frame,
  not more than 12 % behind a character's head, and not behind an object (WARN);
- **label overhang** (`decal-overhang`, FAIL): a sticker, label or decal registered with `readable(mesh, label, { on:
  surface })` must sit on that surface at all four corners. A flat card on a round or tapered object hangs in the air
  past its edge; curve it to the surface (an open cylinder segment for round things), shrink it or move it;
- **clipped art** (`clipped-art`, FAIL): a character whose head canvas has opaque pixels on its edge (hair, a hat, a bun
  or an accessory drawn taller than the room above the head, `HEAD_FRAC` in chars.js) looks sliced flat. Run the check on
  the look sheet so it is caught when the cast is created;
- **key text** (`text-cut`, FAIL): text the joke depends on (a number, a price, WINNER, a name, a label the narration
  names) must be fully inside the frame, not behind a head and not behind an object, for every frame it is in the shot
  (6 % of the frame width or wider). Register it with `readable(mesh, 'label', { key: true })` (props.js) or
  `sign(text, { key: true })`. `key` can be `(t) => bool`, so a screen counts only while it shows the gag. Register
  every screen, ticket, poster and price tag that carries a joke; anything left unregistered is never checked;
- **camera snap** (WARN): the subject moving more than 45 px per frame (glide over 18+ frames, peak about 22 px/frame, or cut);
- **slow camera** (`slow-camera`, per shot, sampled every 0.1 s): how far the picture moves on screen because of the
  camera, in % of the frame width per second, over each 1 s window: a 5x5 grid of static points spread over the frame
  at the depth of the hero mark (else any active mark, else what the centre ray hits) is re-projected and their mean
  shift taken. A pan of 5 % of the width a second reads 5 %/s; a push-in that zooms the picture Z %/s reads about
  0.53 Z (an 8 %/s zoom, 0.27 % a frame, reads 4.2). Under 2.5 %/s for more than 1 s (two 1 s windows in a row) is a
  FAIL, under 3 %/s a WARN (the dash-cam reference office push-in, zoom about 6 %/s, reads about 3.3). Subject motion does not count. Only `locked: true` shots are exempt. Debug one shot with
  `node film.mjs eval <project> "window.__camMotion(shotIndex, t, 1)"` (`pctPerS`, plus the fitted zoom / roll / shift);
- **face size** (`face-size`, per shot): the hero head's width outside its range (`w`, else the shot `type`'s) for more
  than half of the time its mark is active is a FAIL;
- **dissolve length** (`dissolve-length`): a dissolve outside 5-12 frames (5-18 with `in.slow: true`) is a FAIL;
  bursts and wipes are not checked;
- **voice pace** (`voice-pace`, once, from `audio/vo.words.json`): words / speech span (first word start to last word
  end) outside 3.5-4.1 words/s is a FAIL (reference 3.8).
`node film.mjs eval <project> "<js>"` runs an expression in the page (`window.__shots`, `import('/_engine/src/...')`)
to debug a check result.
- `samples(t)`: motion-blur sub-frames for renders (1 still, 3 moving, 5 fast moves). `overlay(ctx, t)` draws 2D on
  top before captions (HUDs, REC dot, screen text).
- `captions`: `[[t, 'text'], ...]`. Build with `captionsFromWords(words)` from `captions.js`.

## The look: clean 3D world, ink lines, crisp characters (core.js `renderStage`, used by `run`)
**House look (look/style-guide.md):** build every stage as `makeStage({ mood: withLook('day', 'indoor' | 'outdoor') })`,
with `withLook` and `LOOK` from the project's `sets.js` (template). Indoors this means heavier ink (1.0, `inkWidth [3.6, 1.6]`),
hard-edge crease lines `[48, 62]`, AO 0.7, bloom 0.9 and vignette `[0.18, 0.42]`. Outdoors there are no crease lines,
so leaves are never inked. Call `lacquer(group)` on every set for the glassy coat.
Car glass (`GLASS_LAYER` = 2) is drawn last, after the inked world and the characters, so its tint and reflections sit over
the cabin and the drivers like real glass (drawn before, the ink lines of the interior made windshields look missing).
Every frame is two passes. The world (layer 0) is rendered as clean 3D (the oil-paint brush filter is OFF by default;
`paint: { radius: 3 }` turns it back on), hazed with distance, then inked and graded (below). Then the characters (`CHAR_LAYER` = 1,
set by `makeChar`) are drawn crisp on top, still hidden correctly behind cars and walls.  Per mood, tune with
`paint: { radius 3, detail 0.22, sat, bright, contrast, haze: [nearM, farM, amount], hazeColor, grain, ao 0.55, aoRadius 0.45,
bloom 0.8, bloomThreshold 1.05 }` and
`charTint: [r, g, b]`. Clouds are painted soft heaps and long thin wisps with grey-blue bases (no outlines):
`clouds` (heaps) and `wisps` per mood, colours `cloud: [deep shade, body, base, sunlit top]`. Set `stage.paint = false` (or the mood's `paint: false`) for a plain render.
The world pass also gets ambient occlusion from the depth buffer (contact shadows where things meet) and bloom on HDR
lights: anything emissive above about 1.05 glows (headlights 2.4, brake lights 3, lit windows, the glowing gauge
cluster; a `MeshBasicMaterial` with `color.setScalar(1.6)` and `toneMapped: false` glows too).
Anything parented to a character is on its layer; props held in a hand (burger, ticket) stay in the world and get painted.

**Ink outlines** (on by default, light): thin dark lines only on the outer silhouettes of nearby objects (~2.6 px near
to 1.4 px, gone by 60 m), so cars read as real glossy cars and trees have no lines between their leaves. Crease lines
inside objects are off (`inkCrease: [35, 50]` turns them on for a heavier cartoon look). The world pass renders with 4x
anti-aliasing.
Normals are rebuilt from the depth buffer, so cut-out leaves and grass get clean outlines with no second scene render.
Characters are never inked by the world pass (they carry their own outline). Per mood:
`paint: { ink: 0.85 (0 = off), inkColor, inkWidth: [near px, far px], inkCrease: null | [deg, deg], inkFade: [m, m], inkJump: [rel, rel] }`.
`inkId: 0.6` (on in `LOOK.indoor`) also inks every border between two different objects, using an object-ID pass, so
frames on a wall, a desk on the carpet and posters are outlined like the reference interiors. Mark a mesh
`userData.noInk` to leave it out, and give one `userData.inkGroup` to parts that should read as one object.

**Lens blur** per shot: `dof: { cInf: px, focus: 'mark name' | metres | (t) => metres, max: 24 }`. The blur radius is
`cInf * |1 - focus / depth|` (1.2x in front of the focus plane), gathered with 48 taps; sharp subjects keep clean edges
and the ink blurs with the background. Values from the reference: close-ups 12-16, medium 10-12, wide 0 (off); blur
about a third of the screen time. Focus on the speaker's mark. Keep the joke prop readable (lower `cInf` when a sign
is the gag, about 6).

**Grade** per mood (in `paint`): `vignette: [strength, start radius]`, split tone `tintShadow` / `tintHigh` ([r, g, b]
offsets: day a hint of violet in the shadows, dusk violet-blue shadows and warm highlights, night blue). `grain`
defaults to 0: the reference shorts have none, and grain doubles the file size and turns to mush on YouTube.

## Look sheet (step 4): template `lookdev.html` + `lookdev.js` + `sets.js`
`sets.js` holds the video's sets (one function per set, each returning `{ group, at, items }`). The look sheet and
`video.js` both import it. `heroSet(scene, { cast, title, wall, w, d, h })` is the worked example of the house look:
- a lobby with a layered wall (main colour, a teal band, a wood wainscot) and a title sign;
- four framed portraits of the cast, a door, a pegboard of printed packs, a poster, a clock and an alarm box;
- chairs in complementary colours, a counter, a plant;
- a terrazzo floor with an emblem, a tiled ceiling, two pendants, and lacquer over everything.
Anchors: `chairs[] counter door` plus addRoom's. Items: `title frames pegboard poster clock chairs counter bell`.
`lookdev.js` shows one still card per second from `cast.json` and `sets.js`:
- lineups of three with role, build and outfit labels;
- the lead's four faces;
- the set wide, medium (`dof` 10) and as a prop close-up (`dof` 14);
- the hero car.
Film it with `--page lookdev.html` (`check`, `sheet`, `stills`, `lookcheck`). Card `i` is the still at `t = i + 0.5`.
`film.mjs lookcheck <project> <out_dir> t...` scores frames against the house look in code, without reference pictures.
- From the scene (`src/lookcheck.js`):
  - the kind of shot (indoor, outdoor, or studio via shot `look: 'studio'`);
  - the share of solids carrying the clear coat;
  - ink settings that fit the kind of shot;
  - light sources in frame on wide interiors;
  - lens blur that fits the subject's distance.
- From the pixels (`tools/look_score.py` against `look/targets.json`): saturation, dark-line share, empty tiles,
  background versus subject sharpness (tiles sorted by raycast depth), and head brightness.
It prints `LOW` for any area under 8.

## Timing from the voice (captions.js)
Build the edit on sentence numbers, not seconds, so it follows the voice:
```js
import SCRIPT from './script.json' with { type: 'json' };            // array of sentences
import { captionsFromWords, sentenceStarts, wordTime, estimateWords } from 'engine/captions.js';
let WORDS; try { WORDS = (await import('./audio/vo.words.json', { with: { type: 'json' } })).default; }
catch { WORDS = estimateWords(SCRIPT); }                             // no voice yet: 3.8 words/s estimate
const S = sentenceStarts(WORDS);                                     // S[0] = sentence 1 starts
// shot: { start: S[4], end: S[5], ... }   cut on a word: wordTime(WORDS, 'buys', S[7])
// run({ captions: captionsFromWords(WORDS), ... })
```
`estimateWords` lets the preview be built before the audio exists; when `audio/vo.words.json` appears, the same code
uses the real times.

## transitions.js (in-world transitions)
`{ start, ..., in: { type: 'burst', frames: 18, fx: cashBurst() } }`: objects fly from a source point at the camera,
fully cover the frame at `start` (the shot switches there, hidden), then scatter outward to reveal the next shot.
Make the fx once at the top of `video.js`. Options: `cashBurst({ origin: [sx, sy], n, cover, seed, spin, size })`,
`origin` is the screen point it bursts from (-1..1, default `[0, -0.75]`, low centre). `paperBurst()` uses paper
sheets stamped PAID; `makeBurst({ tex })` takes any canvas texture (leaves, confetti, receipts).
Inside a shot (cash raining on a lawn), call `fx.render(u)` from `update` after nothing else: it draws over the frame.
Tested at 18 frames.

## stage.js
- `makeStage({mood, fov?, near?, far?})` → `{scene, camera, sky, hemi, sun, grade, follow(x, y, z), frame()}`.
  Call `stage.frame()` after moving the camera (the sky follows it) and `stage.follow(...)` to keep the sun's shadow
  box (±24 m) on the action.
- Moods: `day` (the approved look), `dusk`, `night` (stars, saturated blue: add lamps), `rain` (grey-blue, low
  saturation). Pass an object to customise (`{...MOODS.day, sun: [0xffffff, 2]}`).
- `lamp(scene, x, y, z, {color, intensity, range, glow})`: a pool of light with a glow sprite (street lamps,
  porch lights, string lights).

## sets/highway.js
`addHighway(scene, {wet?, trees?, wall?, houses?, rails?, tufts?, lines?, lights?, x0?, x1?})`. Lanes at
`LANES = [-5.55, -1.85, 1.85, 5.55]`. The roadside is filled by default: a guardrail on the far (-z) side (`rails: 'both'`
adds one on the near side, which blocks low cameras on the shoulder), grass tufts, a power line at z -12.6, rows of houses at
z -27 / +29 / -52, bushes and painted trees, all for x -320..920 (`x0`/`x1` to move the dressed range). `lights: true`
lights the house windows for night. `wall: true` brings back the old noise wall. Keep the action on the +z shoulder.

## Variety: cast.json (use this instead of hand-picking looks)
`node "$ENGINE/cast.mjs" new <project> --chars schemer,quiet,officer,agent,victim,buddy --cars schemer,upgrade,quiet,buddy,traffic,traffic`
writes `cast.json`: a palette for the video and one look per role, avoiding the looks and silhouettes of the last
5 registered videos and repeats within the video. `reroll <project> <key>` replaces one entry; `show` lists them;
`register <project> "<title>"` logs the final video (step 7).
Character roles: `schemer quiet victim buddy officer agent doctor extra`. Car roles: `schemer upgrade quiet buddy victim traffic`.
```js
import CAST from './cast.json' with { type: 'json' };
const schemer = makeChar(CAST.characters.schemer);          // R, shirt, hair, style, acc, girth, legs
const car = buildCar(CAST.cars.schemer);                    // type, colour, skin, interior, plate, shape jitter
```
You can still override any field (`makeChar({ ...CAST.characters.agent, acc: ['headset', 'blush'] })`).

## cars.js
The body is built like a real car (`makeCar`): the side profile is split at the belt line. Below it, a lower body with
rounded edges and cut-out wheel arches, in three pieces (a full-width hood block and rear/boot block, and thin door walls
around an open cabin, so interior cameras see the cabin). Above it, a separate greenhouse leaning in toward the roof:
side panels with the real window openings, body-coloured A and C pillars, a gloss-black B pillar, a crowned roof panel
with rails and a headliner, chrome belt trim. Windshield, rear and side glass are separate panes inset in their frames
(drawn last, `GLASS_LAYER`). Panel gaps for the hood, boot and doors, door handles, body-coloured wraparound bumpers
with a black lip (`car.bumperF`/`bumperR` groups: rotate or drop them for crash damage), recessed grille and lights,
mirrors on stalks, side skirts, exhaust; pickups get bed walls. `car.cabin` = [rear x, front x] of the open cabin.
Realism kit (used by every car): tyres with a bulging sidewall, rounded shoulders, tread and sidewall lettering (bump
map), a recessed, slightly dished 5-twin-spoke alloy with a polished lip, wheel nuts and dark windows, brake discs and red calipers, headlight units (chrome housing, projectors, an LED strip that blooms) and
taillight units, a honeycomb grille in a chrome frame, black window trim, shaped mirrors. Interiors: leather seats with
bolsters, pleated and stitched inserts (`I.accent`, oxblood by default) and headrests on posts; a curved soft-touch dash
with a trim strip and A-pillars; the glowing cluster (`glowGaugeTex`) under a hood; slatted vents in chrome frames,
climate knobs, a gear shifter, door handles and speakers, a fabric headliner, a visor sticker, a carpet with a rubber mat,
and a driver's seatbelt (`car.seatbelt`, hide it with `.visible = false` when the driver gets out). The steering wheel is
leather with three spokes and an airbag hub; `wheelRig.rimPoint()` is unchanged.
- **Generator (use for new cars):** `buildCar({ type, color, skin?, shape?, plate?, interior?: 'modern' | 'old' | false, detail?, traffic?, I? })`
  → a car with `.spec`, and `.I` + `.wheelRig` when it has an interior.
  Types (`CAR_TYPES`): `coupe sedan hatch wagon sports suv van pickup`, each a different silhouette.
  `shape` overrides any `CAR_TYPES` number (`L H hw wR hood ws belt yb bh roof rearRun cab`) or `jitter / jitter2` (-1..1).
  `skin`: `{ wood, stripe: hex, rack, rust, bow: hex }`. Interior `'old'`: tan seats, wood strip, analogue gauges, radio.
  `carSpec(type, overrides)` gives the spec alone (with `spec.I`).
- `makeCar(COUPE | SUV, colour)` → `.body` (tilt `.rotation.z` for brake dive), `.wheels`, `.bumperF/.bumperR`,
  `.tail`, `.glow`, `.head`, `.spec`.
- `addInterior(car, IC | IS, detail)` → `car.wheelRig.rimPoint(angle)` (hands on the wheel); with `detail`:
  `car.brake` (pedal group), `car.brakePad`, `car.can`, `car.charm`, `car.phone`, gauges, screen, cabin lights.
- `rollWheels(car, distance)`, `brakeLights(car, on)`, `tintGlass(car)` (traffic with dark windows).
- New car shapes: copy `COUPE` and change the side-profile `top`, `windows`, `wheelX`.

## chars.js
The look (matched to the reference frames): a big round white head with soft shading and a dark-brown ink outline
(heavier on the shadow side), an ear on the far side, hair drawn like the reference shorts (a solid flat-colour cap on the CROWN: it
covers the top 25-35 % of the head, mostly as volume above the skull, with a high hairline and a big bare forehead and
almost no sideburns; its own thick ink outline including the fringe edge, one clean fringe shape per style and 2-3
thin strand lines from the part; it follows the face when the head turns and covers the whole top from behind), eyes as the reference measures them (solid dark vertical-oval dots 0.09 x 0.13 head widths, no catch-light;
`lid` > 0.28 gives the deadpan straight lid line over a dark half-disc; `eo >= 0.9` gives big round white eyes 0.22 W
with small dot pupils for shock; eye spacing 0.26 W), thick short brows high above the eyes, filled mouths (dark interior, tongue,
teeth). The torso is toon-shaded cloth with an ink outline and clothes; limbs are thin ink strokes with small hands and
shoes. Every head has its own hand-drawn shape (`headShapeFor`: height/width 0.85-1.0, egg taper to the chin, a
slightly pointed crown, one fuller cheek toward the facing side, a small tilt, a fixed 1 % wobble; override with
`makeChar({ head: { hw, egg, nTop, nBot, asym, rot } })`) and a brush outline that is about 3x heavier along the bottom
curve (chin and jaw) than over the top; the torso ink hull and the limbs carry the same weight (so the chin line never reads
as a beard). The head is cream white, drawn as an opaque cut-out that stamps the
stencil buffer: no body part can draw over a face, so the collar and shoulders always tuck in behind the chin.
Shut eyes (`sq`) are heavy curved lids with a crease, not `> <`. Gritted teeth (`mt` + `mg`) are a rounded box with two rows.
- `makeChar({R, shirt, hair, hair2, style, glasses, acc?, outfit?, role?, build?, girth?, torso?, legs?, extra?})`.
  `build` (`BUILD_NAMES`): `average slim tall short stout big kid`, measured on the reference (adults about 3.5 head-
  heights tall, torso 0.9-1.23 HH, legs 1.2-1.54 HH, torso width 0.58-0.97 of the head; kids 2.7-3.0 HH). The torso is
  a long even capsule on a flatter base (a short, squarish bottom with rounded corners, not a bulb; the top end a touch
  narrower under the chin; heavy builds a slight belly); clothes, belt and the arm
  and leg roots follow its real surface. `girth`/`torso`/`legs` multiply the build. The cast picker gives every role a
  fitting build and avoids two alike in one cast; give each character a different one when you hand-pick.
  `outfit` (`OUTFIT_NAMES`): 3D-detail kinds `plain tee polo shirt suit uniform hoodie`, and garments worn as real layers (a shell
  a little outside the body with its own ink hull, inked hem and opening edges; the shirt or trousers show where it
  opens or ends) `jacket suit vest stripes plaid overalls apron sweater cardigan hivis tracksuit labcoat dress`. `shirt` is the main garment, `shirt2` the shirt under an open garment, `pants` the
  trousers under a top, `bow: hex` adds a bow tie. Without `outfit` the role picks from a fitting list (schemer jacket /
  stripes / tracksuit / polo, agent suit / vest / cardigan, officer uniform, quiet cardigan / sweater / plaid, doctor
  labcoat, victim plaid / overalls / hivis / tee / jacket, buddy tracksuit / stripes / hoodie, extra apron / dress /
  sweater / vest / stripes / plaid). Give every character in a cast a different outfit.
  Limbs are thick ink strokes (0.16 R wide) ending in round ink hands and shoes. Limb strokes start ON the body like the reference's
  2D drawing: on the surface facing the camera, in front of any garment layer and inside the outline (arms just inside the
  side outline a little below the head-body line; legs just inside the bottom edge), so the start of every arm and
  leg is always visible whatever the character wears; arms cut out through the side outline near the top and hang down. The body's ink hull is a brush like the face outline: about 3x heavier along the bottom than at the top. Arms reach mid-thigh: a little longer than the torso, and the
  legs a little longer than the arms (reference). Beards and mustaches carry a thin ink outline.
  Styles (`HAIR_STYLES`): `mess` (centre-part curtains + a curled cowlick), `bowl` (straight low fringe), `side` (side
  swoop), `spiky`, `curly`, `afro`, `bun`, `ponytail`, `long` (curtains to the jaw), `flattop`, `buzz` (high, stubble), `bald`.
  A new style is a `mass: { kind: 'swoop'|'part'|'bowl'|'locks'|'spiky'|'curly'|'buzz'|'flat', vol, side, fore, part, amp, cowlick, strandN }` entry in `HAIR`.
  `acc` (`ACC_NAMES`): `sunglasses shadesUp cap ranger beanie headset mustache beard bandage blush neckbrace`, colour
  with `'cap:#2f7de0'`. `girth` 0.9–1.3 (wider bodies), `torso` and `legs` around 1. `extra(c, S, R, cx, cy, front, o)`
  draws anything else on the head canvas.
- **Expression changes pop**: on every key change in `exprAt(keys, t)` the head bounces (up with a stretch, then a little
  squash, settling over 0.35 s) so the change reads as an effect; `exprAt(keys, t, { pop: false })` turns it off.
- **Blinks are automatic** in `exprAt(keys, t)`: every 0.5-2.3 s (seeded per character from its keys), 4 frames
  half / shut / shut / half, plus a blink across every expression change (measured on reference shorts). Turn them off
  with `exprAt(keys, t, { blink: false })` (a stare, a dead-eyed punchline). Squeezed-shut faces (`sq`) never blink.
- **Place the camera before posing.** `.pose(p, camera)` draws the face toward where the camera is now. Posing first and
  moving the camera after gives a blank or back-of-head face (the previous shot's camera). If an update must place
  things, then the camera, then pose, run it twice: `update: (t) => { f(t); f(t); }`.
- **Ready poses** (use these instead of writing joint points): `stand(ch, { x, z, arms, target, lean, walk, face, expr })`
  with `arms` = `down hips wave up point neck phone cross shrug` or `[left, right]`; `walk` = phase in radians;
  `sit(ch, car.I, car.wheelRig, { side: -1 driver | 1 passenger, lean, grip, arms, face, expr })`,
  `sitOn(ch, { x, z, seat, arms, lean, face, expr })` for chairs, sofas and beds (`seat` = `item.seat` or 0.35).
  Characters face +x of their parent; `ch.rotation.y = -Math.PI / 2` turns them to face the camera at +z.
  Both return the object for `ch.pose(p, camera)`; adjust any point before passing it.
- `.pose({hip, neck, face, expr, arms: [[ctrl, hand] x2], legs: [[ctrl, foot] x2]}, camera)` each frame; points in
  the parent's space. Standing at the origin: hip `(0, 0.5, 0)`, neck `(0.02, 0.8, 0)`, feet `(0, 0.03, ±0.1)` for R 0.2.
- `.headWorld()`, `.R`.
- `exprAt([[t, 'name'], ...], t)` blends presets over 0.13 s. Presets: `smug grit grin jolt calm shock dazed flat pain
  innocent stern worried talk`. Brow angle `ba` > 0 = angry (inner end down).
  `expr` in a pose can be a preset name (`'flat'`) or an object (from `exprAt`/`talkAt`). Hair follows the face when the
  head turns (the hairline never comes below the brows), so a turned face always shows its eyes.
- `talkAt(expr, words, t, { rate })`: anime lip-sync for the spoken lines. While a word is spoken the mouth snaps (no
  easing) between shapes about 4 times a second (`rate`, one per syllable; 7 read as chattering), picked from the word's vowels (A wide open, E teeth, O round), shut briefly
  between flaps. Eyes and brows stay from `expr`. Pass only that line's words.

## materials.js
`M` (glass, dark, trim, tyre, rim, chrome, seat, liner, mat, black), `paint(c)`, `flat(c)`,
`box(w, h, d, mat, x, y, z, radius?)`, `plateTex(text, bg, fg)` (signs, desk plates), `noiseTex(...)`, `puffTex`,
`blobShadow(L, W)` (add to the object).
`lacquer(root, { coat 0.8, coatRough 0.12, rough 0.5, env 1.1, floors 1 })`: the glassy house look. It upgrades every
MeshStandardMaterial under `root` to a clear-coated physical material in place. Floors get the strongest coat, so they
show soft light streaks. It skips glass, glows, cut-outs (leaves, grass), unlit materials, car paint and
`userData.matte` meshes. Use it on interiors and man-made props, never on ground or trees.
`grassTex({hue, light, seed})`, `asphaltTex({wet, seed})`: ground canvases with soft blotches and fine strokes (wrap with
`ctex(c, [repeatX, repeatY])`; about one tile per 4 m). Use these, not `noiseTex`, for ground the camera gets close to.

## scenery.js: fill every frame (all instanced or merged, cheap)
`forest(scene, {area: [x0, x1, z0, z1], count, seed, kinds: ['round', 'tall', 'pine'], scale, avoid(x, z), tint, shadows})`,
`houseRow(scene, {x0, x1, z, face: 1 | -1, spacing, seed, lights, depth, avoid(x)})` (simple houses, fronts at `z`),
`guardrail(scene, {z, x0, x1})`, `grassTufts(scene, {area, count, seed, size, avoid(x, z)})`, `powerLine(scene, {z, x0, x1, span})`,
`bushRow(scene, {area, count, seed})`, `paintedTree({kind, h, seed})`, `paintedBush({r, color, seed})`. The highway and house
sets already use them; new sets should too, so no frame shows empty ground or sky behind the action.

## fx.js
`puffs(scene, n)` → `begin() / add(x, y, z, size, opacity, colour) / end()` each frame;
`tyreSmoke(P, at, t, t0, t1, dt, offs, halfTrack, opacity, laneZ)`; `skids(scene, n)` + `skid(m, at, t, t0, t1, off, z, width)`;
`debris(scene, mats, n, seed).update(timeSinceImpact, x0, laneZ)`; `lightMats.tail() / glassShard()`.

## sets/house.js: low wide on a house or driveway
`addHouse(scene, { x, z, w, depth, storeys: 1|2, roof: 'front'|'side'|'hip'|'flat', siding, roofColor, trim, doorColor,
garage: 'left'|'right'|false, porch, chimney, vent, shutters, lights, dress, fence, seed })` → `{ group, at, opts }`.
Anything left out is picked from `seed`, so a new seed gives a new house. The front faces +z at z = 0; lawn z 0–6,
sidewalk 6–7.2, street 7.2–14 along x. Stand the camera on the street looking at -z (lower third = plain street).
`lights: true` for night (glowing windows, porch and garage lights). Anchors in `at` (world, y = 0):
`door porch garage driveway drivewayStreet lawn lawnLeft lawnRight sidewalk street mailbox windows[]`.
Put the schemer's car on `at.driveway` (`rotation.y = PI/2` noses it to the garage), a cash pile on `at.lawn`.
The street is dressed by default (`surround: false` to skip): a neighbour on each side, a back row of houses at z -21, a
treeline behind, street trees at x ±13.5, a low hedge and a few grass tufts along the front.

## sets/room.js: interiors
`addRoom(scene, { kind: 'office'|'kitchen'|'living'|'shop'|'empty', x, z, w, d, h, wall, floor: 'wood'|'tile'|'carpet',
view: 'skyline'|'skylineNight'|'trees'|'street', night, window, ceiling, frames: [{ shirt, hair, bg }], plate, sign, tvText, seed })`
→ `{ group, at, items }`. Open toward +z (camera side), back wall at z = -d, own light at mid height.
Anchors: `center front behindDesk deskTop window counterTop sofaSeat wallSlots[]`. `items` holds the dressing
(`desk chair phone laptop plate cabinet plant frames counter fridge table sofa rug tv sign shelfL shelfR`), so a shot
can relabel (`items.laptop.draw(...)`) or move them. `frames` are framed portraits of characters (pass the schemer's
shirt for "photos of him on the insurer's wall").

## props.js: the prop library (each returns a Group on y = 0, front +z; furniture is at character scale, K = 0.7)
- **Text and screens:** `readable(mesh, label, { key, w, h })` registers any panel, screen or ticket with the check
  (above). `sign(text|lines, {w, h, bg, fg, post, key})` `.setText()` (text is measured and shrunk to fit 84% of
  the board width; `fit` changes that). Check that a sign sits fully inside the frame for the whole shot, and not
  behind a head. `deskPlate(text)`,
  `counter(label, n)` `.set(n)` ("days since" gags), `screen({w, h, lines | draw})` `.draw(fn)`, `paper(['PAID'])`,
  `panel(w, h, {glow, draw})`, `labelTex(lines, opts)`, `drawLabel(g, W, H, lines, opts)`.
- **Furniture:** `desk table chair({office}) shelf cabinet plant sofa fridge counterUnit tv rug laptop deskPhone frame({photoOf})`.
  Surfaces expose `.top` / `.seat` heights.
- **Outdoor:** `mailbox bin bush tree fence streetLamp({on, h}) cone parcel({label})` (`bush` and `tree` are the painted scenery ones).
- **Light:** `pendant({ color, r 0.26, cord 0.6, on, intensity 9, range 6, shadow })`: a hanging dome lamp. The bulb
  blooms and throws a warm pool of light below; put the group at ceiling height. Every interior should show its light
  sources.
- **Story:** `cashPile({r, h, n})` `.grow(0..1)`, `hospitalBed()`, `duck()`, `camBox({on})` (dash cam, doorbell cam, CCTV).
New gag props should usually be one of these plus new text. A genuinely new prop goes in the project first, then
into `props.js` and this list after the video.

## Sound (engine/audio: synthesized, no samples; run after the voice is in and the picture times are locked)
`run({ ..., sound, music })` declares the cues; the engine adds the rest:
- `sound: [[t, 'name', { gain?: dB, pan?: -1..1, args?: {generator options}, why? }], ...]` one-shot events on story
  times (use `WT('word', S[i])` so they move with the voice). Names (`engine/audio/sfx_lib.py` SOUNDS):
  cars `brake_squeal tyre_screech crunch({size, glass}) glass_tinkle horn horn_short engine_pass engine_rev car_door seatbelt`;
  money and office `cash_register coins paper_flutter cash_burst paper_burst phone_ring stamp keyboard`;
  bodies `oof groan neck_crack chomp sip tap knock`; dash cam `camera_beep rewind wiper`;
  accents `whoosh whoosh_soft record_scratch pop boing ding thud`.
- Ambience beds per shot from the stage mood (day `day`, dusk `road`, night `night`, rain `rain`), or the shot's
  `bed: 'day' | 'road' | 'night' | 'rain' | 'rain_car' | 'car' | 'room' | 'tv' | 'none'` (interiors need one).
- Dissolves get a soft whoosh (`in: { sound: false }` turns it off), bursts their sound (`in: { sound: 'cash_burst' }`).
- `music: { stops: [S[i] of each "But" turn], tag: S[last], acts?, bpm?: 112, gain?, on?: false }`: an original
  comedy score (one sly D-minor theme: pizzicato + glockenspiel by day, vibes and brushes at night, pad and music box in
  the rain), a beat of silence before each "But", a major-key sting on the tag.
Then: `node film.mjs cues <project>` (writes `audio/cues.json`) and `python engine/audio/mix.py <project>` (about
25 s): `audio/mix.wav` at -14 LUFS / -1.5 dBTP, stems, and `audio/sound.md` (every cue, levels, loudness). Rules: voice
gain only; events 6 dB under their natural level; music about 9.5 LU under the voice and ducked 5 dB more under words;
the voice should sit a median 8-12 LU above everything else. Mux `audio/mix.wav` without `loudnorm` (it is levelled).

## Camera and readability rules (measured on 20 reference shorts; the check enforces the first two)
- Big reframes are cuts. Everything else glides: ease in and out over 18-40 frames, peak about 22 px/frame at 1080.
- Every hold creeps: a push-in of 0.2-0.35 % a frame (zoom 6-10 %/s; slower pushes WARN, under about 0.16 % a frame
  FAILS), 0.6 % on punch words. Rolls of 4-5 degrees on emphasis.
- Impacts: a 7-frame kick that flips sign every frame and decays (about 4 px, roll +-0.3 degrees), not a long wobble.
- Faces change 0-3 frames before their word; lead faces every 0.3-0.6 s.
- A foreground prop closer than ~2 m to the lens and cut by the frame edge reads as a blob: recognisable or gone.
- Painted signs lit from the side go grey: give a sign face an unlit material when it carries the joke.

## Final QA (after the render, before delivery)
`python tools/video_qa.py <project>/<name>.mp4 <project>/review/qa <project>/audio/cues.json`: specs, loudness, silences,
black / unplanned white / frozen (12+ frames) / popping frames (dissolves, cuts and impacts from the cue file are
planned), per-shot colour statistics and 2 s contact sheets. Fix what it reports before handing over.

## Not built yet (write them in the video folder first; move them into the engine once they work)
Backyard pool. Rain streaks on glass, the wiper wipe and the dashcam HUD (REC, timestamp, speed, rewind) exist as 2D
overlays in `cars_watching_the_road/video.js` (`drawStreaks`, `drawDrops`, `drawWipe`, `drawHUD`): copy them from there.
