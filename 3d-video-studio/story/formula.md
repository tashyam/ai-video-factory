# The story formula

A fake, comic origin story for an everyday invention. A **schemer** exploits a **loophole**, gets rich, gets greedy,
brushes off the pushback, and is beaten by a **quiet victim** who uses the **invention**. The last line names it.

Measured from one reference (`examples/dashcam.md`, 62 s, 238 words, 17 sentences). This is a hypothesis, not a law.
Re-check it whenever a new reference is analysed, and update the % column if several references agree.

## The 12 beats

Times are for a 62 s video at 3.8 words/s. Scale them by % for other lengths.

| # | Beat | % of runtime | ≈ s | Words | Sentences | Job |
|---|---|---|---|---|---|---|
| 1 | **Hook** | 0–8 | 0–4.7 | 15–18 | 1 | Show the misdeed and its result. Don't explain anything. |
| 2 | **Loophole** | 8–17 | 4.7–10.4 | 18–22 | 1 | The fake-out plus *because* plus the rule he exploits. The viewer learns the secret. |
| 3 | **First payoff** | 17–26 | 10.4–16 | 20–24 | 1 | It works. A concrete list of rewards, ending on the funniest one. |
| 4 | **Repeat** | 26–30 | 16–18.6 | 10–12 | 1 | "So the next week, he does it again…" Now it's a pattern. |
| 5 | **List of three** | 30–39 | 18.6–24 | 18–22 | 2 | "He picks them carefully." Then three targets, each a quick visual gag. |
| 6 | **Escalation 1** | 39–45 | 24–28 | 12–16 | 1 | A helper or tool that scales the scheme up. |
| 7 | **Escalation 2, excess** | 45–52 | 28–32 | 14–18 | 1 | Greed becomes absurd (buys something just to repeat the scheme). Frame-filling visual (cash burst). |
| 8 | **Pushback that fails** | 52–62 | 32–38.5 | 20–24 | 3 | The authority calls. **Two spoken lines**: a dry fact with a number, then a deadpan excuse. Only lip-sync in the video. |
| 9 | **"But" #1, false security** | 62–70 | 38.5–43.5 | 18–22 | 1 | Restate the loophole from his side: why he thinks he can't lose. |
| 10 | **Mood shift + quiet victim** | 70–81 | 43.5–50 | 22–26 | 1 | "Then, one rainy morning…" He picks someone quiet and does the trick again, in full. |
| 11 | **"But" #2 + reveal** | 81–97 | 50–60 | 38–44 | 3 | The victim doesn't react, just points. The invention is shown and does its job; show its own view. |
| 12 | **Tag** | 97–100 | 60–62 | 7–9 | 1 | "And that's how the ___ was invented." |

Split: **setup and rise 0–70%, downfall 70–100%.** The reveal starts at about 85%. The invention's generic name
("a camera") appears at about 89%; its real name ("dash cam") appears only in the last sentence.

## Rules that hold the structure together

- **Hero = villain.** We follow the schemer and want him caught. The ending is justice, never a lesson or a moral.
- **The winner is silent.** The quiet victim never speaks. The invention does the talking.
- **The trick is repeated in full twice:** at the hook and at beat 10. The second time the viewer knows the pattern,
  so the different ending lands.
- **Two "But" turns**, at about 63% and about 81%.
- **Sentence openers drive forward:** He / And sure enough / So / Then / Eventually / But / Then / But / And that's how.
  Avoid openers that pause (However, Interestingly, You see).
- **Specific and deadpan:** numbers ("fifth neck injury this year"), small-object details ("a little box taped to his
  windshield"), understatement ("a really weak neck").
- **Loop:** the last shot echoes the first (same kind of setup), so the Short loops cleanly.
- **The scheme stays cartoonish.** Show what he does and why it works in one sentence. Never give a step-by-step
  how-to of real fraud.

## Picture and edit, tied to the beats

Details and the setup-by-setup table are in `examples/dashcam.md`. The measured numbers and frames are in
`examples/dashcam/` (`profile.json`, `frames/`, `transitions/`). Framing, camera speed and must-have detail per setup
type are in `look/setup-types.md`.

- **A new camera setup on most sentence starts** (12 of 17), plus cuts on the action inside long sentences
  (impact, purchase). About 19 setups for 62 s.
- **Pace slows by act:** about 2.3 s per setup in act 1, one long 9 s move in act 2, 3 to 5 s per setup in act 3.
- **Hard cuts (about 7) only on jolts and punchlines:** the impact, the motive, a list topping itself, the purchase,
  the dialogue reply, a "But", the reveal.
- **In-world transitions (3) mark the big beats:** out of the hook (fly-through), the end of the first payoff
  (cash burst fills the frame), the start of the downfall (wiper wipe).
- **Dissolves (about 8)** on time or place jumps and through the calm final act.
  - Measured frame by frame they are **7 to 10 frames** (median 8), on an eased S-curve (about 9, 23, 43, 64, 81, 94%),
    and both shots keep moving while they mix.
  - Only the slow dissolve out of the reveal runs about 16 frames.
  - An earlier note said "6 to 26": those were the extremes, and building to them made the last video's dissolves
    10 to 17 frames.
- **Every shot moves except the device view.** The default is a push-in that zooms the picture 6 to 10% a second.
  The reference office push-in zooms about 6% a second. A 3% push already reads as a locked camera: the last video
  had 17 s like that, and `film.mjs check` now fails it (rule `slow-camera`).
- **Cuts are clean:** one frame changes the whole picture. Motion blur must never mix the two shots
  (`video_qa.py` fails a blended frame at a cut).
- **Act 3 has one hard cut only, on the reveal.**
- **Three colour acts:** bright midday for beats 1–4, dusk then night (most saturated) for 5–9, grey-blue rain for 10–12.
  - Colour the sky and the lights, not the whole frame: the road stays neutral asphalt at dusk.
  - Rain is streaks, not dots.
  - Measured colourfulness is about 103, 79 and 41 by act (`look/setup-types.md`, "Colour by act").
- **Home base:** a low wide on the schemer's house or driveway carries the payoff and greed beats (5 of 19 setups).
- **The reveal shot is the only locked-off camera**, and it shows the invention's own view (overlay, timestamp,
  readout that proves it).
- **About one prop gag per setup** (a PAID sign, a hospital bed on the lawn, a gift bow on a car bought to be
  crashed, a "days since injury" counter resetting). Plan them in the storyboard.
  - A gag prop stays in its own beat; only the story object (the thing the plot is about) travels between scenes.
  - Characters carry what a real person would bring for that errand (`story/rig-check.md`, "Real-life check").
- **A new character or location for every beat**; only the schemer appears in every act. About 8 characters, 2 with
  lip-sync.
- **Faces:** the schemer changes every 0.3 to 0.6 s (grit, smug, grin, fake pain, innocent, shocked; a sweat drop
  when he fakes and when he's caught). The quiet victim keeps one flat face throughout.
- **Captions:** 1 to 2 words, about 3 per second, always on screen, at about 70% of frame height.
- **Sound:** about -14 LUFS, loudness range about 2 LU, a continuous bed (never silent).

Evidence: 1 reference so far (dash cam). Raise a rule's count as more references agree.
