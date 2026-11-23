# House look: what every frame must have

The targets for steps 3 and 4 (visual bible, look sheet) and every frame after them. Match this **treatment**, not a
reference's sets, characters or wording. The pixel numbers are in `look/targets.json`; `film.mjs lookcheck` scores
frames against them (see "Checking the look in code" at the end).

## 1. Glassy (lacquered) surfaces, everywhere
- Everything solid looks lacquered, like a glossy toy.
  - **Floors** are the strongest: the lobby's terrazzo shows soft streaks of the room's light and the colours of things
    standing on it.
  - **Plastic and metal** come next: the teal and red waiting chairs each carry one long, soft highlight along the curve
    of the seat and back, and the display case's metal frame has bright edge lines.
  - **Painted walls, posters, tickets and boxes** have only a faint sheen.
- The highlights are soft and wide, never mirror-sharp, and about 15 to 30 % brighter than the surface. Colours under
  them stay saturated.
- Skin, hair and cloth stay matte. The characters are flat 2D, so the gloss lives in the world.
- **Engine:**
  - Call `lacquer(setGroup)` on every interior and on man-made outdoor props (coat 0.8, floors 1).
  - Never lacquer grass, ground or trees; `userData.matte` excludes any one mesh.
  - Car paint is already clear-coated.

## 2. Ink outlines on everything in focus
- Every object in the zone in focus is outlined in a dark warm ink (#15120f to #1b1712, not pure black). This covers
  outer silhouettes **and** hard edges: shelf fronts, picture frames, door jambs, counter tops, the rims of lamp shades,
  the dividers of the display case.
- **Line weight, measured at 1080 px wide:**

  | Thing | Line weight |
  |---|---|
  | Characters | 6 to 9 px |
  | Props within about 2 m | 4 to 6 px |
  | Mid-ground | 2.5 to 3.5 px |
  | Background | thin, then softened by the blur (section 4) |

- Printed things (posters, tickets, packs, signs) carry their own drawn outlines and inner design lines inside the
  texture. An inked frame around a flat print is what makes it read as an object.
- **No lines inside foliage.** Trees and bushes get silhouettes only, never crease lines between leaves.
- **Engine:** `withLook(mood, 'indoor')` sets ink 1.0, `inkWidth [3.6, 1.6]` and `inkCrease [48, 62]`.
  `withLook(mood, 'outdoor')` turns crease lines off. Draw the outlines of printed art in the canvas texture
  (`panel({draw})`).

## 3. Natural light and shadow
- Every interior is lit from sources you can see in the frame:
  - pendant lamps with glowing bulbs that bloom, each throwing a warm pool on the floor below;
  - a ceiling of tiles with lights;
  - a window.
- Light falls off toward the frame edges and corners, about a 15 to 20 % darker vignette.
- **Shadows:**
  - soft contact shadows wherever things meet: under shelves and in the cells of the display case, under chairs, where
    the counter meets the floor, and under characters' feet;
  - one soft cast shadow from the key light;
  - shadows tinted toward the wall colour, never grey-black.
- Interiors are warm (3000 to 3500 K). Day exteriors use the sunny, saturated mood they already have.
- **Engine:** `pendant()` (props.js), `lamp()`, `ao 0.7`, `bloom 0.9`, `vignette [0.18, 0.42]` (in `LOOK.indoor`).

## 4. Depth: the subject sharp, the background slightly soft
- The focus plane is on the subject: the speaker, or the prop that carries the joke.
- The back wall is **slightly** blurred, about 3 to 6 px at 1080, still readable as posters and signs.
- Foreground things closer than the subject are blurred more. The fisherman's hat that frames the bait-shop shot is
  heavily blurred, about 10 to 15 px.
- The joke's text must stay readable. If it sits on the back wall, lower the blur.
- **Engine:** shot `dof: { cInf, focus: '<mark>' }`.

  | Shot | cInf |
  |---|---|
  | Talking medium | 8 to 12 |
  | Close-up | 12 to 16 |
  | Wide | 0 |
  | Sign is the gag | about 6 |

  The blur in front of the focus plane is already 1.2 times stronger.

## 5. Set dressing density
- **No empty wall.**
  - Every visible wall carries 4 to 8 readable items: a title sign across the top, framed photos or posters in a row, a
    pegboard or cork board with hanging items, a clock, a fire alarm, a door with its frame.
  - The wall itself is layered: one saturated main colour (mustard yellow, sage green), a contrasting band or stripe,
    and a wood wainscot or skirting.
- **Floor:** patterned (terrazzo speckle, tiles, wood planks) with one feature such as a centre emblem.
- **Ceiling:** visible in wide and low shots (tiles, lamps).
- **Props are specific to the story and repeated in sets:** a wall of identical scratch tickets, rows of lure packs,
  framed winners. Repetition sells the place and makes the joke.
- **Printed design:** every printed item is a real little design, with a logo or title, a picture, a price burst or
  badge, a few text lines and a barcode. Keep it legible at 1080.
- **Foreground framers:** an out-of-focus object at the frame edge (a hat, a shoulder, a chair back) gives depth in
  medium shots. It must be recognisable, or else gone (see the camera rules).

## 6. Colour
- Big, flat, saturated planes for walls, with furniture and clothes in complementary colours: a yellow wall against
  navy uniforms and teal or red chairs; a sage wall against a red apron and a wood counter.
- The cream-white heads are the brightest thing in the frame after the lamps, so faces pop.
- Shadows lean warm brown or violet, and highlights lean warm.
- **Acts change the light, not the whole frame.**
  - Dusk colours the sky and the lamps while the road stays neutral.
  - Rain is streaks with wet reflections.
  - Never put a full-frame tint on a shot.
  - Per-act targets and the per-setup-type framing, camera speed and must-have detail are in `look/setup-types.md`.

## 7. Characters in these frames (already matched by chars.js)
- Round cream heads with a heavy chin line, crown hair, thick brows and dot or lidded eyes.
- Outfits carry the role: officer caps and badges, a clerk's apron with a name tag reading TRAINEE, a tie, a
  mustache. Sweat drops show nerves.
- Accessories are story props: the fisherman's hat hung with lures.

## Checking the look in code
`node "$ENGINE/film.mjs" lookcheck <project> <project>/review/lookcheck <t1> <t2> ... [--page lookdev.html]` scores
each frame 0 to 10 per area and prints `LOW` for anything under 8. It needs no reference pictures.
- **From the scene:**
  - the kind of shot: indoor (a ceiling above the camera), outdoor, or studio (cast cards);
  - gloss: the share of solid objects in view that carry the clear coat;
  - ink settings that fit the kind of shot;
  - light sources visible in frame;
  - lens blur that fits the subject's distance.
- **From the pixels** (`tools/look_score.py`, against `look/targets.json`):
  - colour: saturation;
  - outlines: the share of dark line pixels;
  - density: the share of flat, empty 60 px tiles;
  - depth: how sharp the background is compared with the subject, using tiles sorted by raycast depth;
  - faces: whether the heads are among the brightest pixels.
- **New reference frames:** run `python tools/look_score.py --measure <frames>` and put the ranges into
  `targets.json`.

## The look-sheet checklist (what the scores stand for; also read the sheet by eye)
1. Gloss: does the floor show soft light streaks, do chairs and metal have highlights, and do walls have only a faint sheen?
2. Outlines: is every in-focus object inked, with the printed art outlined? Are there no lines inside foliage?
3. Light: are the light sources visible, with warm pools, contact shadows and a vignette?
4. Depth: is the subject sharp, the back wall slightly soft, and the foreground framer blurred?
5. Density: does every wall have 4 to 8 readable items, plus a patterned floor and the ceiling in the wide?
6. Colour: are the walls saturated, the props complementary, and the heads the brightest thing?
7. Story props: is every gag prop specific, with readable text and printed design?
