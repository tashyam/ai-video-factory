# Visual bible (step 3)

The visual bible is written after the script is approved and before anything is built. It decides what everything
looks like, so the look sheet (step 4) and the storyboard (step 5) only have to show it. Write it to
`<project>/visual_bible.md` using the template below.

**Before writing:**
- Read `look/style-guide.md` (the house look).
- Read the approved `script.json`.
- Generate the looks with `node "$ENGINE/cast.mjs" new <project> --chars <roles> --cars <roles>`, so the bible
  describes real `cast.json` entries. The user can reroll any entry.

**Rules:**
- **Concrete, not mood words.** Write "mustard yellow wall (#f0c43a) with a teal band at 1 m and a wood wainscot", not
  "a warm lobby". Every colour is a hex. Every sign, screen and printed item has its exact text.
- **One entry for every place the script visits**, including places seen only through a window or on a screen.
- **Mark every asset:** `library + params`, `library + new text` or `new`. Only the hero prop (the invention) should
  normally be `new`.
- **Every prop gag is written out:** what it is, where it sits, what it says, and in which sentence it pays off.
- **Keep it short enough to approve:** about one screen per character group and per set.

## Template

```markdown
# Visual bible: <title>

## 0. Look
- House look: look/style-guide.md (gloss, ink on everything in focus, natural light, soft backgrounds, dense dressing).
- Acts and moods: act 1 <day / mood, palette>, act 2 <dusk/night>, act 3 <rain>.
- Palette of the video (from cast.json): <hexes> · accent for the joke props: <hex>.

## 1. Characters
| Role | cast.json | Build, height | Head / hair | Outfit layers (hex) | Accessories | Signature prop |
|---|---|---|---|---|---|---|
| schemer | schemer | average, 3.5 HH | curly black crown | yellow jacket #ffc93a over a white tee, grey pants | — | neck brace (act 2) |
For each character, two or three lines: the default face and the 3 expressions the story needs (with sentence numbers),
posture and movement (slouch, brisk walk, deadpan stillness), the one thing that reads at 8 % of frame width
(silhouette hook: the cap, the bright jacket), and costume changes by act.

## 2. Environments (one block per set)
### <Set name> · act <n> · <mood> · beats <sentence numbers>
- **Layout:** what the camera sees from the main setup. Back wall, side walls, floor, ceiling. Foreground, mid-ground
  and background layers, and where the characters stand.
- **Surfaces:** wall colour, band and wainscot (hex); floor pattern; ceiling; materials (lacquered wood, tile, metal).
- **Light:** the visible sources (pendants, window, neon, TV) with colour temperature, where the pools fall, and the
  shadow direction.
- **Dressing:** background items (4 to 8 per wall, each named), mid props, and foreground framers for medium shots.
- **Text gags:** exact wording of every sign, poster, screen and label, and the sentence where each pays off.
- **Depth:** the focus subject per setup, and the blur level (style guide section 4).
- **Asset marks:** `addRoom kind + params`, `heroSet()` in sets.js, `library + new text`, `new`.

## 3. Interiors (cars, booths, screens)
For each car the story uses: the type and colour from cast.json, the interior ('modern' or 'old'), dash props (charm,
bobblehead, phone), what the camera sees through the windshield, and the damage states. For a room seen through a
window: what shows and how lit it is.

## 4. Props
- **Hero prop (the invention):** shape, size relative to a head, colours, screen or lens details, its on and off states,
  and how it appears in the reveal. Always `new` (built in sets.js or props).
- **Gag props:** one line each: the prop, its library source, its text, the sentence it pays off in.

## 5. 2D graphics
Captions are the style default. List any overlay: HUD (REC, timestamp, speed), screen contents, rain on glass, the
cash or paper burst, and title cards. Give the exact text, colours and when each appears.

## 6. Asset plan
| Asset | Mark | Built in | Cost |
|---|---|---|---|
| Lobby | new (heroSet) | sets.js | high |
| Schemer's coupe | library + params | buildCar(CAST.cars.schemer) | low |
```
