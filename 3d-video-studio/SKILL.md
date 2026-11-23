---
name: 3d-video-studio
description: Makes a ~60 s vertical comedy Short that invents a fake origin story for an everyday invention ("Why drivers started filming the road" → "and that's how the dash cam was invented"). A schemer games a loophole, escalates, and is beaten by a quiet victim using the invention. Flat-face cartoon characters in a glossy 3D world, three colour acts, 1–2 word captions, rendered in code; the voice is made by the user in Cartesia from a tagged script. Use when the user runs /3d-video-studio, asks for a 3D cartoon Short like the reference they share, asks for a "why X was invented" or "that's how X was invented" short, or wants to analyse a reference Short in this niche.
---

# /3d-video-studio

```
┌──────────────────────┐
│  "Why Drivers Started│  title asks about a behaviour, never names the invention
│   Filming The Road"  │
│   ◕‿◕  ▶ 💥           │  hook: the schemer's misdeed, payoff by 4 s
│   loophole → greed   │  escalation, deadpan pushback, two "But" turns
│   quiet guy points ▣ │  reveal through the invention's own view
│ "that's how the ___  │  tag answers the title, last shot loops to the first
│   was invented."     │
└──────────────────────┘
```

Work through the steps in order. **⏸ marks a gate: stop, show the result, and wait for the user's answer.**
At every gate, say which step comes next. Read only the files the current step lists.

```
SKILL_DIR="<base directory of this skill>"; ENGINE="$SKILL_DIR/engine"
KIT="$SKILL_DIR/kit"; [ -d "$KIT/node_modules/playwright" ] || KIT="$HOME/.claude/kit"
PY="$KIT/.venv/Scripts/python.exe"; [ -x "$PY" ] || PY="$KIT/.venv/bin/python"
[ -d "$ENGINE/node_modules/three" ] && [ -x "$PY" ] || bash "$SKILL_DIR/setup.sh"
```
Needs Node 18+, ffmpeg and Python 3.9+. `bash "$SKILL_DIR/setup.sh"` installs the rest once (three.js, Playwright +
Chromium, a Python venv with the Parakeet word-timing model). Run every Python tool below with `"$PY"`.

**The reference profile is the yardstick for every gate.**
- `PROFILE="$SKILL_DIR/story/examples/dashcam"` holds the measured numbers (`profile.json`), one frame per setup
  (`frames/`) and every frame of each transition (`transitions/`).
- If the user brings a new reference, build its profile first ("Learning from a new reference" below) and point
  `PROFILE` at it.
- **Frames are not shipped in the public repo.** `story/examples/dashcam/` and `story/examples/cashier/` hold the
  measured numbers (`profile.json`) and the written beat sheets, but not the reference's frames (they belong to the
  original channel). If `$PROFILE/frames` is missing, ask the user for the reference video (any Short in this format
  works) and run step 2 of "Learning from a new reference" with `$PROFILE` as the output folder, before step 4. If the
  user has no reference video, judge against `profile.json` and the written examples only, and say so at each gate.
- Never judge our frames alone: every review sheet puts the reference beside ours.

## Step 1 · Topic ⏸
Read `story/topic-bank.md`. Use the user's topic or offer three. Run the four-question test and name the weakest check.
**Gate:** the user picks a topic.

## Step 2 · Title and script ⏸
Read `story/title-formula.md`, `story/formula.md`, `story/hook-rules.md`, `story/script-template.md`, `story/script-check.md`.
Also read `story/rig-check.md` (what our flat characters can and can't do) and run `"$PY" "$SKILL_DIR/tools/rig_check.py" <project>/script.json`
before scoring; show any flag with its "Stage it as" note. A line the rig can't show must be fixed **before** the voice is recorded.
Write the title first, then the script beat by beat. Score it (rewrite below 9/10).
Show the title, the script (one sentence per line, beat labels on the side), the word count, the estimated
length at 3.8 words a second and the score.
**Gate:** the user approves or edits. Save the approved sentences as `<project>/script.json`
(create the project with `cp -r "$ENGINE/template" <project>` first; `<project>` must not exist).

## Step 3 · Visual bible ⏸
Read `look/style-guide.md` (the house look: glossy lacquered surfaces, ink on everything in focus, natural light,
slightly blurred backgrounds, dense dressing) and `look/visual-bible.md` (rules and template).
Generate the looks first: `node "$ENGINE/cast.mjs" new <project> --chars <roles> --cars <roles>`. Then write
`<project>/visual_bible.md` covering:
- every character (build, head and hair, outfit layers in hex, accessories, the faces the story needs);
- every environment (layout, surfaces, visible light sources, 4 to 8 dressing items per wall, exact text gags, depth);
- the interiors (cars, booths, screens), the props (the hero invention in full) and the 2D graphics;
- an asset plan marking each item `library + params`, `library + new text` or `new`.
Show the bible with the cast output. **Gate:** the user approves, edits or asks for a reroll.

## Step 4 · Look sheet ⏸
Show the visual design built in 3D before any storyboard, at final detail. Read `look/setup-types.md`.
- `lookdev.html`, `lookdev.js` and `sets.js` came with the template. Write the story's busiest set into `sets.js`
  (`heroSet()` is the worked example of the house look: replace it, keep its layers), following the bible exactly. The
  video imports the same `sets.js` later, so this work is not thrown away.
- `lookdev.js` already makes the cards:
  - every `cast.json` character, in lineups of three with labels;
  - the lead's faces;
  - the hero set: wide, medium with lens blur 10, and a prop close-up with blur 14;
  - the hero car.
  Add a card for the hero prop, and for any other set the bible marks `new`.
- **One card per setup type the story uses** (`interior`, `pov`, `tracking`, `house`, `twoshot`, `talker`,
  `device`), each built in its real set at its real framing, with every "Must have" from `look/setup-types.md`.
  The dashboard POV, the talker's wall and the device view are the ones that get skipped; build them now.
- **Pair them with the reference:** `"$PY" "$SKILL_DIR/tools/sbs_sheet.py" <project>/review/look_pairs.jpg --ours <cards> --ref <the
  same types from $PROFILE/frames>`.
- Add one strip of 400 px crops at 1:1 (gauges, wall gags, car body, road), so missing detail and blur show.
- `node "$ENGINE/film.mjs" check <project> 0 <cards> 0.5 --page lookdev.html`, fix every FAIL (including `clipped-art`:
  a character's hair, hat or head art cut flat at its edge), then
  `node "$ENGINE/film.mjs" sheet <project> <project>/review/look.jpg 0.5 1.5 2.5 ... --page lookdev.html --w 360 --cols 4`.
- Score it in code: `node "$ENGINE/film.mjs" lookcheck <project> <project>/review/lookcheck 0.5 1.5 ... --page lookdev.html`
  (gloss, outlines, light, depth, density, colour, faces; 0 to 10 against `look/targets.json`). Fix every `LOW`, then
  look at the sheet once by eye, for what numbers can't judge (story props, appeal). Show the scores with the sheet.
  Run `lookcheck` on each act's frames in step 8 too.
Hand over `review/look.jpg` and `review/look_pairs.jpg`. **Gate:** the user approves the look of the characters, the
world and every setup type, or lists fixes. Every set in the video is built to this level of detail.

## Step 5 · Storyboard + voice script ⏸
Two documents in one go:
1. **Storyboard** `<project>/storyboard.md`: one row per camera setup (18 to 21):
   `# | sentence(s) | beat | setup type | camera move | action and faces | prop gag | transition in (frames) | act/mood`.
   Rules from `story/formula.md` ("Picture and edit"); `story/examples/dashcam.md` shows a full one.
   - **Setup type** is one of the names in `look/setup-types.md`; it becomes the shot's `type` in code.
   - **Action and faces** names an engine pose (`stand`, `walk`, `sitOn`, `point`, `lean`, `armTo`…) or a prop for every action;
     anything else fails `story/rig-check.md` and is rewritten before building.
   - **Camera move:** every row names its move and speed (for example "push-in 6%/s", "pull-back to wide",
     "orbit 120°"); only the device view may say "locked".
   - **Transition in:** dissolves are 7 to 10 frames (up to 16 for the reveal), or name the in-world transition.
   Sets, characters and props come from the approved visual bible: name them as the bible does. Below the table,
   copy the bible's asset plan with anything the storyboard added.
   - **Continuity table** (below the storyboard): every prop or character that changes place or state gets one line,
     `thing: state → state → state`, with the setup number of each change (for example `key: pocket (1) → floor (3)
     → dog's mouth (5)`).
     - Every change happens **on screen** in a named setup, or is shown by an on-screen action the viewer can read (it
       is thrown, it lands, it is handed over).
     - No setup may start from a state the viewer never saw happen. A later action that depends on an unseen change
       (searching for something nobody saw dropped) is a storyboard failure: add the action to a setup, or add a setup.
       Across a narrated time jump, ordinary off-screen steps are allowed (taking a ticket out of its hiding place).
     - Label each prop **story object** (travels with the plot) or **gag prop** (a hiding place, container or joke
       object that stays in its own beat). A gag prop in a new location fails unless the narration names it there.
     - Under the table, one **carry line** per location: who is there, what each carries and why.
   - **Real-life check** (`story/rig-check.md`, last section): every action and carried item has a reason a real
     person would have in that moment. If the only reason is continuity, rewrite the row.
2. **Voice script** `<project>/voice/cartesia.md`: read `story/voice-cartesia.md` and write the tagged blocks
   (emotion per block, speed advice, pauses only before the "But" turns and the tag).

Show both. **Gate:** the user approves the storyboard. Then **ask for the voice**: "Generate the blocks in
`voice/cartesia.md` in Cartesia and put the files in `<project>/audio/` (vo_01.wav, vo_02.wav... or one vo.wav).
I'll build the 5-second preview meanwhile." Don't wait for the audio to continue to step 6.

## Step 6 · 5-second preview ⏸
Build only the hook (the first 5 s, usually setups 1 to 3) so the user can judge the look before the long build.
Read `engine/API.md`; copy blocks from `engine/template/video.js` (never open `engine/src`). Build every character
and car from `cast.json` (`makeChar(CAST.characters.x)`, `buildCar(CAST.cars.x)`), and use `stand` / `sit` poses.
- Timing: `sentenceStarts` / `captionsFromWords` with the estimate (`estimateWords`), or the real word file if the
  audio has already arrived (step 7).
- Import the sets from `./sets.js` and use `makeStage({ mood: withLook(mood, 'indoor' | 'outdoor') })`.
- The look to judge against is the approved look sheet: clean 3D with glossy surfaces, ink on everything in focus,
  natural light, a slightly blurred background, and every frame filled edge to edge. If a face is blank or shows the
  back of the head, the camera was placed after the pose (see `engine/API.md`, chars.js).
- Give every face a `mark` and every shot its `type`. Run `node "$ENGINE/film.mjs" check <project> 0 5 0.25`; it
  exits 1 on any FAIL, so fix them all.
- One sheet: `node "$ENGINE/film.mjs" sheet <project> <project>/review/preview.jpg 0.2 0.8 1.6 2.6 3.6 4.6 --w 180 --cols 6`.
  Look at it once; fix what is clearly wrong.
- Render: `node "$ENGINE/film.mjs" render <project> <project>/review/preview.mp4 0 5` (about 1 minute).
  If the voice is in, add the first 5 s of it: `ffmpeg -i review/preview.mp4 -i audio/vo.wav -map 0:v -map 1:a -c:v copy -t 5 review/preview_vo.mp4`.
- Compare the hook with the reference's hook:
  - `"$PY" "$SKILL_DIR/tools/compare_video.py" <project>/review/preview.mp4 "$PROFILE" <project>/review/cmp_preview --range 0 5`;
  - put our fly-out strip next to `$PROFILE/transitions/` (the fly-out passes the glass in about 4 frames and lands on
    a wide shot).
  Fix FAILs in motion, sharpness and detail before showing the preview.
Hand over the mp4 path and the pair sheet. **Gate:** the user approves the look (characters, colours, camera,
captions) or asks for changes. Changes to characters or style are cheap here and expensive later.

## Step 7 · Voice in
When the user says the audio is in `<project>/audio/`: follow "When the audio arrives" in `story/voice-cartesia.md`
(join blocks, `words.py`, check the length and pace).
- **The pace is a hard gate:** outside 3.5 to 4.1 words a second (`film.mjs check` fails it), ask for a new take at
  another speed and don't build on the slow one. The last video went ahead at 3.4 and ran 71 s against the
  reference's 62.
- Otherwise continue: the edit is built on sentence numbers, so it retimes itself.
If the voice has not arrived by the end of step 8, ask again; don't render the final without it.

## Step 8 · Build the rest, act by act
For each act (1 day, 2 dusk/night, 3 rain), in order:
1. New sets and props first, in `sets.js`, built to the detail of the approved look sheet and the bible (see "Not built
   yet" in `engine/API.md`).
2. Shot blocks for every setup in the act, each with its `type`, transitions as the storyboard says (`dissolve` of 7
   to 10 frames, `burst` with `cashBurst()` / `paperBurst()`, a wipe, or a hard cut).
3. `film.mjs check` for the act's time range must exit 0 (no FAIL). The FAILs that matter most:
   - a camera slower than the `slow-camera` limit (a push-in should zoom 6 to 10% a second);
   - a hero face outside its type's size range;
   - a dissolve outside 5 to 12 frames;
   - a label hanging off the object it is stuck to (`decal-overhang`): register stickers and labels with `on: <surface>`;
   - key text cut by the frame edge, covered by a head or hidden (`text-cut`). Register every number, price, screen and
     label the joke depends on with `readable(mesh, label, { key: true })` when the set or shot is built.
4. **Pair sheet** of the act: our setup middles on the bottom row, the reference's setups of the same beats on top
   (`tools/sbs_sheet.py`, frames from `$PROFILE/frames`). Add one strip of 400 px crops at 1:1 from the act.
5. **Transition review:** render each transition in the act as a short clip (`film.mjs render` over about 1 s around
   it). Make a frame-by-frame strip and put it next to the reference transition of the same kind in
   `$PROFILE/transitions/`. Check that:
   - cuts change in one clean frame;
   - dissolves follow an eased curve while both shots keep moving;
   - a burst never covers more than about two thirds of the frame, and the next shot fades in under it;
   - a wipe reveals the new shot directly behind the blade.
Show the pair sheet, the crops and the transition strips, with one line per setup saying what is in it.
Before showing, walk the act's continuity table against the render: every change of a prop's place or state is visible in
the frames, in order.
**⏸ Gate per act:** the user approves or lists fixes.

## Step 8b · Sound (after the voice is in and step 8 is approved)
Add `sound` and `music` to `run()` and a `bed` on interior shots (engine/API.md "Sound"): an event on every action the
voice names (brakes, crash, ka-ching, phone, tap...), a `record_scratch` 0.4 s before each "But", music `stops` on the
"But" sentences and `tag` on the last one. Then `node "$ENGINE/film.mjs" cues <project>` and
`"$PY" "$ENGINE/audio/mix.py" <project>`. Read `audio/sound.md` (levels, loudness) instead of listening: integrated
-14 LUFS, true peak <= -1.5 dBTP. Tell the user `audio/mix.wav` is ready to listen to.

## Step 9 · Render and deliver ⏸
- **Storyboard sheet first, never a render first.** Before any full render (first or after fixes):
  - run `check` over the whole video; it must exit 0;
  - make one sheet with a frame from every setup (plus each frame the user flagged), paired with the reference.
  Look for: covered glass, empty frames, signs or text cut off by the frame edge or hidden behind a head, blown-out
  areas. Show it to the user and **wait for approval**; render only then.
- **One output only.** Always write `<project>/<name>.mp4` and `out/part_*.mp4`, overwriting the previous render. Never
  write `_v2`, `_v3` or `out_v2` copies; the old file is replaced.
- Render one file per stretch between hard cuts (dissolves and bursts live inside a file), each under about
  10 minutes: `node "$ENGINE/film.mjs" render <project> out/part_01.mp4 <t0> <t1>`. About 11 s of render time per
  second of video on the user's laptop GPU.
- Join: `ffmpeg -f concat -safe 0 -i out/list.txt -c copy out/silent.mp4`.
- Mux: `ffmpeg -i out/silent.mp4 -i audio/mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest <project>/<name>.mp4`
  (mix.wav is already levelled; without step 8b, use `audio/vo.wav` with `-af "apad,loudnorm=I=-14:TP=-1.5"`).
- QA every frame: `"$PY" "$SKILL_DIR/tools/video_qa.py" <project>/<name>.mp4 <project>/review/qa <project>/audio/cues.json`;
  fix black, white, frozen, popping or blended-at-a-cut frames and silences before handing over.
- **Compare with the reference:** `"$PY" "$SKILL_DIR/tools/compare_video.py" <project>/<name>.mp4 "$PROFILE" <project>/review/compare --words <project>/audio/vo.words.json`.
  It prints PASS / WARN / FAIL per metric and exits 1 on any FAIL:
  - cut cleanliness and dissolve length;
  - camera motion and still time;
  - detail and sharpness per act;
  - colour per act;
  - setups and pace;
  - loudness and captions.
  A FAIL goes back to step 8 for its act, unless the user explicitly accepts it. Hand over `review/compare/compare.md`
  and its pair sheets with the video.
- Log the looks so the next videos avoid them: `node "$ENGINE/cast.mjs" register <project> "<title>"`.
- Promote anything new (a set, a prop) into the engine with its options exposed, and add a line for it to
  `engine/API.md`, so the next video gets it as `library + params`.
Hand over the mp4 path. **Gate:** the user's notes, if any, go back to step 8 for that act only.

## Learning from a new reference (any time)
1. `"$PY" "$SKILL_DIR/tools/analyze_ref.py" <video.mp4> <out_dir>` prints a summary and writes:
   - `beats_draft.md`: setups with duration, cut or gradual and first word; sentences with time and %; loudness;
   - `setups.jpg`: start, middle and end of every setup;
   - word timings and strips.
2. `"$PY" "$SKILL_DIR/tools/ref_profile.py" <video.mp4> "$SKILL_DIR/story/examples/<name>" --words <out_dir>/vo.words.json --acts <act starts>`
   measures everything the gates compare against:
   - setups, and the frame count and curve of every dissolve;
   - camera motion and still time;
   - detail, sharpness and colour per act;
   - captions, loudness and pace.

   It also saves one frame per setup and every frame of each transition.
3. Read `beats_draft.md`, open `setups.jpg` and the transition sheets once, and write `story/examples/<name>.md` like
   `examples/dashcam.md`, including the "Transitions, frame by frame" section.
4. Update `story/formula.md` where references agree, and note how many support each rule. Quote typical values
   (median) next to ranges; a range copied from the extremes ("6 to 26 frames") hides the normal case.

### Matching a look ("make it look like X")
1. Measure first, in numbers: line widths, colours (sky top / horizon, shadow hue), blur on backgrounds, camera speed,
   blink rate. Write them to `story/examples/<name>.md` next to the beat sheet.
2. Compare our frames to theirs side by side: `"$PY" "$SKILL_DIR/tools/sbs_sheet.py" out.jpg --ours a.jpg b.jpg --ref r1.jpg r2.jpg`.
3. Score each area out of 10 (colour, lighting, ink, textures, characters, depth, composition, motion) with a numbered
   fix list per frame, fix the biggest gap first, and re-score. Put the final numbers into the engine defaults.

## Files and when to read them
| File | Step |
|---|---|
| `story/topic-bank.md` | 1 |
| `story/rig-check.md`, `tools/rig_check.py` | 2 and 5 (can the characters physically do it?) |
| `story/title-formula.md`, `formula.md`, `hook-rules.md`, `script-template.md`, `script-check.md` | 2 |
| `look/style-guide.md`, `look/visual-bible.md` | 3 and 4 (the style guide again when building sets in 8) |
| `look/setup-types.md` | 4, 5 and 8 (framing, camera speed and must-have detail per setup type) |
| `$PROFILE/` (`profile.json`, `frames/`, `transitions/`) | 4, 6, 8 and 9 (the reference side of every pair sheet) |
| `engine/template/sets.js`, `lookdev.js` | 4 |
| `story/voice-cartesia.md` | 5 and 7 |
| `story/examples/dashcam.md` | 5, only if a setup type or beat is unclear |
| `engine/API.md` | 4, 6 and 8 |
| `engine/template/video.js` | 6 and 8, to copy a car, character, camera or effects block |
| `engine/src/*` | never, unless the engine itself has a bug |
| `tools/analyze_ref.py`, `tools/ref_profile.py` | new reference videos |
| `tools/compare_video.py` | 6 (hook) and 9 (final), against `$PROFILE` |
| `engine/audio/` (`mix.py`, `sfx_lib.py`, `score.py`) | 8b, only to add a new sound |
| `tools/video_qa.py`, `tools/sbs_sheet.py` | 9 (QA), look matching |

## Token rules
- Approval gates come before code: script (2), visual bible (3), look sheet (4), storyboard (5), preview (6), each act (8).
- `film.mjs check` (text) before any image. One small sheet per review; full-size stills only for a specific problem.
- Don't re-watch a reference; its `examples/<name>.md` and its measured profile folder replace it. Prose alone is not
  enough: the numbers and frames in the profile are what the gates compare against.
- Pair sheets cost the same as single sheets; never review our frames without the reference beside them.
- Render long files in the background and only read their last line.
