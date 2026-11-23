# Voice-over script for Cartesia (Sonic)

The user makes the voice in Cartesia and sends the audio back. Write `<project>/voice/cartesia.md` from the
approved script in this format, show it, and **ask the user for the audio**. Don't wait idle: build the preview
(step 6) while they record.

Source: docs.cartesia.ai, "Volume, speed and emotion" and "SSML tags" (checked 2026-11-13).

## What Cartesia supports

| Control | Syntax | Range | Notes |
|---|---|---|---|
| Emotion | `<emotion value="calm"/>` | named emotions | English only. **Most reliable: neutral, calm, angry, content, sad, scared.** Also usable: excited, confident, curious, sarcastic, mysterious, surprised, proud, anxious, hesitant. Must match the words. |
| Speed | `<speed ratio="1.2"/>` or `generation_config.speed` | 0.6 to 1.5 | Guidance, not exact. Small changes are hard to hear; the docs prefer `generation_config`. Not supported on Professional Voice Clones. |
| Volume | `<volume ratio="1.3"/>` or `generation_config.volume` | 0.5 to 2.0 | Rarely needed; we level to -14 LUFS afterwards anyway. |
| Pause | `<break time="300ms"/>` | s or ms | Splits the generation, so use at most 2 or 3 per video. Punctuation usually pauses better. |
| Laugh | `[laughter]` | | Only if a line needs it. |

**Emotion changes in the middle of one generation are unreliable** (the docs say so). So the script is split into
**blocks**: one block = one emotion = one generation. The user generates each block separately and sends numbered
files, or generates it all at once if the voice sounds even.

## Rules for our format

- Pace target: about 3.8 words a second (62 s for about 237 words). Most voices are slower at 1.0, so suggest
  **speed 1.15 to 1.25** in `generation_config` for the whole video, then adjust after a test block.
- Recommend a voice the docs mark as "Emotive" (the docs name Leo, Jace, Kyle, Gavin, Maya, Tessa, Dana, Marian).
  A calm, slightly deadpan storyteller fits the format.
- Use plain text exactly as approved. Write numbers the way they should be said ("fifth", "twenty grand").
- Spell out anything easy to misread. Avoid `<spell>` unless a code or plate is read letter by letter.
- The two spoken lines (beat 8) can use other voices: one for the authority, one for the schemer. If the user
  wants a single narrator voice, keep them in the narrator voice with a different emotion.
- Pauses: one `<break time="250ms"/>` before each "But" turn and one before the tag line. Nowhere else.

## Default emotion per beat

| Beats | Emotion | Why |
|---|---|---|
| 1–4 hook, loophole, payoff, repeat | `content` | relaxed storyteller who knows the punchline |
| 5–7 list, escalations, excess | `excited` (or `content` if it sounds forced) | the scheme speeding up |
| 8 line A (authority) | `neutral` | dry, bureaucratic |
| 8 line B (schemer) | `content` | smug, unbothered |
| 9 "But" #1 | `confident` | his false security |
| 10 quiet victim, rainy morning | `calm` | the mood shift |
| 11 reveal | `mysterious`, then `calm` from "It's a ..." | the turn, then the plain fact |
| 12 tag | `content` | the button |

## File to write: `<project>/voice/cartesia.md`

````
# Voice: <title>
Voice: <suggested voice, e.g. an Emotive narrator>   speed (generation_config): 1.2   model: Sonic
Send back: one file per block named vo_01.wav, vo_02.wav, ... (or one vo.wav), WAV or MP3, into <project>/audio/

## Block 01 · beats 1–4 · narrator
```
<emotion value="content"/>He ... (sentences 1–4 exactly as approved)
```

## Block 02 · beats 5–7 · narrator
```
<emotion value="excited"/>...
```

## Block 03 · beat 8 line A · authority voice
```
<emotion value="neutral"/>Sir, this is your ...
```
...
## Block NN · beat 12 · narrator
```
<break time="250ms"/><emotion value="content"/>And that's how the ... was invented.
```
````

Each code block is exactly what gets pasted into Cartesia. Nothing else goes inside the code blocks.

## When the audio arrives

1. Numbered blocks: join them with a short natural gap, then level:
   ```bash
   cd <project>/audio && for f in vo_*.wav; do echo "file '$f'"; echo "file 'gap.wav'"; done > list.txt
   ffmpeg -f lavfi -i anullsrc=r=44100:cl=mono -t 0.12 gap.wav
   ffmpeg -f concat -safe 0 -i list.txt -ar 44100 -ac 1 vo.wav
   ```
2. Word times: `"$KIT/.venv/Scripts/python.exe" "$KIT/words.py" audio/vo.wav script.json` (on macOS or Linux:
   `.venv/bin/python`) writes `audio/vo.words.json`.
3. Check the length and pace: aim for 55 to 65 s and 3.5 to 4.1 words a second. If the pace is far off, ask the user
   to regenerate at a different speed rather than stretching the audio.
4. `video.js` reads the word file, so captions and sentence-based shot times update by themselves
   (see `engine/API.md`, "Timing from the voice").
