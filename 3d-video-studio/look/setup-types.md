# Setup types: framing, camera and must-have detail

Every camera setup in a video is one of these types. Set it on the shot in code (`type: 'talker'` and so on;
`engine/API.md`), so `film.mjs check` can hold the hero face to its size and the camera to its speed.

The look sheet (step 4) builds **one card per type the story uses**, at final detail, before any storyboard. Each
card is shown beside the reference frame of the same type, from `story/examples/dashcam/frames/` (setup numbers in
`examples/dashcam.md`).

**Why this exists:** in "Why Cars Started Watching The Road" only the busiest set went on the look sheet. The other
setups were built later with no reference beside them, and the comparison found:
- an empty navy band where the dashboard should have been;
- a blank office wall;
- faces about half the reference size;
- 17 s of camera that barely moved.

Each "Must have" line below is a thing that video was missing.

## Camera speed, for every type
- The camera always moves. A slow push-in that zooms the picture 6 to 10% a second is the default (the reference
  office push-in zooms about 6% a second).
- `check` measures how far the picture moves on screen (`engine/API.md`, "slow camera"). A 6% zoom scores about 3.3.
  Under 3 is a WARN, and under 2.5 for more than 1 s is a FAIL.
- Our last office shot zoomed about 3% a second (score 1.7) and read as a locked camera.
- The only locked shot is the device's own view (`locked: true`), and it is short.
- Big reframes are cuts, never fast pans. A move peaks at about 22 px a frame.

## The types

| Type | Hero head width (share of frame width) | Camera | Must have |
|---|---|---|---|
| `interior` (tilted ultra-wide in a car) | 0.2–0.4 | ultra-wide, 10–20° roll, slow push or drift | the whole driver reads in one look: head top left, foot on the pedal bottom right; a lit gauge cluster; stitched seats; a visor with a tag; a story prop on the seat (a phone with a lit screen); sunlight or rain on the glass; no dark empty dash |
| `pov` (over a dashboard) | none | eye height behind the wheel, gentle forward drift | a gauge cluster readable at 1:1 (numerals, needles, a gear indicator, one warning light or line of text, odometer); the steering wheel with spokes; a screen or radio; the bonnet; the headliner edge at the top of frame; the road ahead with lane lines, signs and the action car; **no depth blur on the dash** |
| `tracking` (cars on the road) | none (faces readable in the windows) | low, a fast pull-back into a wide, then side or three-quarter; cars fill 40–60% of the width | glossy cars with panel gaps, handles, chrome, glass reflections and blooming headlights; asphalt grain, skid marks, tyre smoke; guardrail, trees, signs and traffic in the distance |
| `house` (low wide on a house or driveway) | 0.08–0.15 | low (knee height), slow push | textured grass with blades, a path or pavement, house siding and trim; the act's prop gag big and readable (hospital bed, PAID sign, cash mountain, gift bow); 2 or 3 characters doing something |
| `twoshot` (two or three people talking on location) | 0.15–0.35 | eye level, slow push or drift; never side-on in a flat line | a pool of light at night; characters overlapping in depth, not lined up; the lower third is road, pavement or lawn with detail, not a flat colour |
| `talker` (centred push-in on one speaker) | 0.35–0.65 | centred, push-in at about 6% a second | the wall behind is dressed with 4 to 8 readable story gags (framed photos of the schemer, a counter, a skyline in the window); the desk or foreground has props; lip-sync |
| `device` (the invention's own view, or a face filling it) | 0.5–0.8 | locked, at most about 2 s per locked stretch | a lens look (fisheye bend, vignette, the bonnet edge); small, realistic overlay text (REC dot, date, speed) |
| `wide` (any other establishing wide) | 0.06–0.12 | slow push or crane | the place readable at a glance, with depth layers |

## Colour by act (applies to every type)
- Colour the **light and the sky** for each act, never the whole frame:
  - at dusk the sky goes purple-orange, but road and pavement stay neutral dark asphalt and the headlights bloom;
  - a full-frame tint turns the road purple and kills contrast. The comparison measured act-2 saturation of 0.67
    against the reference's 0.54.
- Rain is **thin streaks plus drops sliding on the glass**, with wet reflections on paint and road. Round white dots
  read as snow.
- Act 3 keeps some colour (colourfulness about 40% of act 1, not 25%): a red car, a maroon hoodie, warm interior trim.

## Detail at 1:1
- Review sheets at 180 px hide blur and missing detail. Every act gets one strip of 400 px crops at full resolution
  (step 8).
- Detail targets come from the reference profile (`story/examples/dashcam/profile.json`):
  - edge density at least 0.7 times the reference per act;
  - sharpness at least 0.7 times the reference.

  The last video measured about half the detail and 2 to 8 times less sharpness. Haze, heavy lens blur and
  motion-blur smear were the main causes, together with untextured surfaces.
