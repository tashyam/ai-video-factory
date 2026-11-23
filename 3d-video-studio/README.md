# 3D Video Studio

A free Claude Code skill that makes **3D animated cartoon Shorts (9:16, about 60 s)**, entirely in code. No animation
software, no After Effects, no stock footage. Every character, room, car and camera move is written in three.js,
rendered frame by frame in a browser, and finished with captions, sound effects and music, all timed to your voiceover.

It was built on the "fake origin story" format ("Why cashiers stopped winning the lottery", "Why cars started watching
the road"): a schemer games a loophole, escalates, and is beaten by a quiet person using an everyday invention.

You can use it two ways:
1. **Replicate a concept.** Give Claude a reference Short. It studies it, measures it (cut speed, camera motion,
   colour, sharpness, captions, pace) and builds a new story in the same format.
2. **Your own script.** Give Claude a topic, or ask it for three ideas, and it writes a brand-new script from scratch.

---

## What you need

| | |
|---|---|
| **Claude Pro** subscription | That's all you pay for on the Claude side |
| **Claude Code** | Terminal or desktop app. Use **Opus 5.5** with **high effort** (`/model`) |
| **Node.js 18+**, **Python 3.9+**, **FFmpeg**, **Git** | Free. Claude can install them for you during setup |
| **Cartesia** account | For the voiceover. Claude writes the voice script with emotion and speed tags already in it |

Windows: run everything in **Git Bash** (comes with Git for Windows).

---

## Install

### The easy way: ask Claude
Open Claude Code and type:

> Install the 3D Video Studio skill from this repo and run its setup: https://github.com/codewithsiddique-04/3d-video-studio

Claude clones it into your skills folder, installs the engine and sets up the render kit. The first setup downloads
a few things (Chromium and a ~500 MB word-timing model), so give it a few minutes.

### Or by hand
```bash
git clone https://github.com/codewithsiddique-04/3d-video-studio.git ~/.claude/skills/3d-video-studio
bash ~/.claude/skills/3d-video-studio/setup.sh
```

### Then restart
**Fully close Claude Code and open it again.** Typing `/exit` isn't enough; it needs a fresh start to pick up the
new skill. To check, start a new session and ask *"what skills do you have for 3D videos?"*. You should see
`3d-video-studio`.

---

## Make your first video

Create a new, empty folder for the video, open Claude Code inside it, and start with `/3d-video-studio`:

**Replicate a concept**
```
/3d-video-studio Here's my reference video: C:\videos\reference.mp4
Study it and make a new Short in the same format, about a different invention.
```

**A fresh idea**
```
/3d-video-studio Make a Short about why restaurants started using pagers.
```

**Not sure?**
```
/3d-video-studio Give me three topic ideas.
```

From there Claude takes you through nine stages, and **stops after each one for your approval**.

---

## The 9 stages

| # | Stage | What you review |
|---|---|---|
| 1 | **Topic** | Does the idea work as a story? Claude names the weakest part before you commit |
| 2 | **Title + script** | ~60 s, beat by beat, scored out of 10 (rewritten below 9). Your most important review |
| 3 | **Visual bible** | Your character sheet: every character, outfit colour, face, set, prop and sign gag |
| 4 | **Look sheet** | Characters and the busiest set built in real 3D, next to the reference, scored in code |
| 5 | **Storyboard + voice** | 18–21 camera setups, plus `voice/cartesia.md`. Now generate the voice in Cartesia |
| 6 | **5 s preview** | The hook, rendered. Changing the style here is cheap; later it's expensive |
| 7 | **Voice in** | Every word is timed and the pace checked (3.5–4.1 words/s); too slow means a new take |
| 8 | **Build act by act** | Per act: frames next to the reference, close-up crops, every transition frame by frame. Then sound |
| 9 | **Render + QA** | Every frame checked (black, frozen, cut-off text), loudness to -14 LUFS, compared with the reference |

## Tips for a better result

1. **Review every stage.** Claude is very good, but it can still make mistakes: a face turned the wrong way, a sign
   cut off, a joke that doesn't land. Review every act, not just the final video. Fixing one act is quick; fixing the
   whole video at the end is not.
2. **Be specific.** Not *"it looks off"* but *"in shot 4 the cashier's face is too small"* or *"the rain is too dark"*.
3. **Start a new Claude session for every new video.** A fresh session keeps the context small and your token usage down.
4. **Know what to expect.** One video takes about **1.5 hours** including every review. On Claude Pro it used about
   **35–40 % of the usage limit** including change requests per scene, and under 30 % when only small changes were needed.

---

## How it works

- `SKILL.md`: the 9-step workflow with approval gates. `story/`: topic bank, title formula, hook rules, script
  template and check, rig check, the Cartesia voice guide and two worked examples. `look/`: the house style and targets.
- `engine/`: three.js characters, cars, sets, props, captions and transitions (`API.md`), `film.mjs` (check, sheet,
  render), `cast.mjs` (character looks) and `audio/` (synthesized sound effects, score and mix).
- `tools/`: reference analysis (`analyze_ref.py`, `ref_profile.py`), look scoring, side-by-side sheets, frame QA and
  the final comparison against the reference.
- `kit/`: Playwright, the Python venv and the word-timing model (`setup.sh` fills it).

Captions and shot times are tied to the words in your voiceover, so if the audio changes, the edit retimes itself.

**Reference profiles.** `story/examples/dashcam` and `story/examples/cashier` contain the measured numbers
(`profile.json`) and beat sheets of the two reference Shorts. Their frames aren't included (they belong to the
original channel); give Claude the reference video and it rebuilds them with `tools/ref_profile.py`.

## Third-party code

`engine/audio/dsp.py`, `instruments.py`, `sfx_core.py` and parts of `tools/video_qa.py` are used under the MIT
license in `engine/audio/LICENSE-third-party.txt`.

Made by TryAIToday. I keep improving this skill, so watch the repo for updates.
