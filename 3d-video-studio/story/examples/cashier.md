# Example: "Why Cashiers Keep Winning The Lottery"

> The reference's frames (`frames/`, `transitions/`, `beats.jpg`) are not included in the public repo. Run `tools/ref_profile.py` on the reference video to rebuild them; `profile.json` (the numbers) is included.

Reference Short (third-party video: learn the recipe, never copy its characters, designs or script).
57.7 s, 1080x1920, 30 fps. 200 words, 3.46 words/s, 13 sentences. 23 camera setups (mean 2.5 s, median 1.9 s,
range 0.5 to 11.3 s). 0 hard cuts: 9 dissolves (median 10 frames) and 13 in-world / continuous-camera transitions.
-15.2 LUFS, loudness range 2.1 LU, true peak -2.6 dBTP. Measured 2026-11-15 with `tools/analyze_ref.py` and
`tools/ref_profile.py --acts 0,17.3,27.9,43.6,57.7`. The ASR dropped 43.6–51.3 s; it was re-transcribed separately
and merged. **Don't re-watch the video; this file and `cashier/` replace it.**
- `cashier/profile.json`: the numbers every gate compares against.
- `cashier/frames/`: one frame per setup. `cashier/transitions/`: every frame of each transition.

## How it differs from dashcam
- **Shape:** "Why X keeps happening", not "why X was invented". The countermeasure is a *procedure* (decoy winning
  tickets + undercover agents), revealed by a short "You see, in real life…" explainer beat, then the tag. There is no
  "and that's how ___ was invented" line; the last sentence states the countermeasure and the last shot loops to the
  first (same store, same counter).
- **No hard cuts at all.** Everything flows: one-take camera moves that re-frame into the next setup, sun-glare
  white-outs, a slide across a pinned photo, and 5–12 frame dissolves.
- **Slower narration** (3.46 w/s) with dialogue lines read in-character ("Sorry man, not a winner", "story of my
  life", "Wow, congratulations! Just wait right here.").
- **Four colour acts:** warm store day (0–17.3), dream / night / dawn purple-pink (17.3–27.9), bright teal lottery
  office (27.9–43.6), blue explainer then warm store again (43.6–57.7).
- **Victim = undercover agent.** The "quiet guy" is the customer from the hook; he returns in a suit with a badge.

## Transitions, frame by frame
- **Continuous push (f28–52, setup 1→2→3):** one camera move from a wide of the counter, through the cashier's face,
  down his arm to a full-frame ticket close-up. ~24 frames; no cut, the framing just keeps going.
- **Dissolves:** 5–12 frames, median 10, both shots moving (store exterior → trash can; bait shop sign → store).
- **Sun-glare white-out (f682–748):** blue night bedroom → the window flares pink-white → the flare resolves into a dawn
  road with the red car driving at camera. ~25 frames of glare.
- **Photo slide (f1303–1331):** the waiting-room three-shot freezes into a pinned polaroid ("KYLE · LAKE RD") on a
  corkboard; the camera slides across the board as a lamp/arm sweeps past.
- **Top-down push (f1566–1590):** overhead on a green cabinet; the doors swing open to reveal stacks of winning tickets.

## Setup by setup
Act: ☀ store day, 🌙 dream / night / dawn, 🏛 lottery office, 🔵 explainer + return.

| # | Time | In | Camera | Picture | Narration | Act |
|---|---|---|---|---|---|---|
| 1 | 0.0–1.3 | — | Wide push-in on the counter | Cashier (red polo, name badge, swoop of brown hair) at a bait-and-lottery counter; scanner gun, register, lottery wall. | He scanned a customer's | ☀ |
| 2 | 1.3–2.5 | continuous push | Close on cashier, tilting down | Smug face, scanner gun pointed at the ticket. | lottery ticket, | ☀ |
| 3 | 2.5–6.0 | continuous push | Full-frame ticket insert, then face | "REEL BIG CASH – WIN UP TO $1,000,000" ticket; register screen flashes WINNER; cashier's eyes pop, sweat drop. | saw it had won a million dollars, | ☀ |
| 4 | 6.0–10.6 | dissolve 10f | Over-the-shoulder, customer foreground | Cashier deadpan "Sorry, man"; the customer (fishing hat with lures, yellow jacket) shrugs, lip-sync "story of my life", walks out the door. | and said, Sorry man… The guy just shrugs… walks out. | ☀ |
| 5 | 10.6–12.4 | dissolve 8f | Low push from the door to the trash can | Door closes; cashier dives head first into the bin, legs up. | The second the door closes, the cashier is elbow deep in the trash | ☀ |
| 6 | 12.4–16.3 | dissolve 5f ×2 | Inside-the-bin POV (dark ring), then table top | He fishes the ticket out, smug; tucks it into his wallet next to his ID. | fishing the ticket back out and tucking it into his wallet | ☀ |
| 7 | 16.3–17.1 | continuous | Medium on cashier | Eyes closed, blissful smile. | like it's been his all along. | ☀ |
| 8 | 17.1–21.9 | dissolve 10f | Dream: yacht at night under a huge moon, castle on a cliff, fireworks | Cashier at the yacht's helm ("…KEEPERS"). | By midnight, he's already bought a boat, a mansion, and a whole new set of friends. | 🌙 |
| 9 | 21.9–23.8 | continuous pull-back | Top-down, blue night bedroom | Cashier asleep hugging a goldfish bowl; pizza box on the floor. | At least in his head. | 🌙 |
| 10 | 23.8–25.7 | sun-glare white-out | Head-on tracking, dawn road | Red boxy car driving at camera, cashier at the wheel. | So, the next morning, he drives two hours | 🌙 |
| 11 | 25.7–28.0 | dissolve 11f | Close side, through the window | Cashier gripping the wheel, grinning. | to the lottery office, | 🌙 |
| 12 | 28.0–32.6 | continuous | Centred push on the counter, glass window | "STATE LOTTERY PRIZE CLAIMS" sign; clerk lady (orange curly hair, glasses, teal blouse); "PLACE TICKET HERE" slot; he slides the ticket under the glass; she beams, lip-sync "Wow, congratulations! Just wait right here." | slides the ticket under the glass… | 🏛 |
| 13 | 32.6–43.9 | dissolve 11f | Waiting room, slow push (11 s, the long hold) | "OUR WINNERS" wall of photos, fish tank, chairs; he waits; a door opens behind him; the customer walks in in a suit with a badge, two police officers follow. Cashier: sweat, panic. | So, he waits. Five minutes… Except now he's wearing a suit with a badge… two police officers. | 🏛 |
| 14 | 43.9–45.3 | photo slide | Corkboard, slide | The scene becomes a polaroid "KYLE · LAKE RD" pinned on a board. | You see, in real life, | 🔵 |
| 15 | 45.3–51.3 | continuous moves | Top-down on a desk with two piles labelled "CLERKS" and "EVERYONE ELSE" | Pile of clerk photos grows tall; the other pile stays flat (the statistics joke). | lotteries noticed that store clerks were winning way more often than everyone else, which is statistically a little suspicious. | 🔵 |
| 16 | 51.3–52.6 | dissolve 12f | Locked top-down (the only still shot) | Green cabinet under a printer. | So, they started | 🔵 |
| 17 | 52.6–54.5 | top-down push | Same | Printer drops a ticket; cabinet doors open on rows of winning tickets. | printing winning tickets as bait | 🔵 |
| 18 | 54.5–55.8 | continuous | Top-down on the agent's hat, then storefront | The fishing hat (agent in disguise) walks to a "BAIT · GAS" store. | and sending undercover agents into stores | 🔵 |
| 19 | 55.8–57.7 | dissolve 10f | Over-the-shoulder, the opening counter | Hat in the foreground, cashier behind the counter: the first frame again. Loops. | pretending to be regular customers. | ☀ |

## What the details show
- **Cast (5):** cashier (schemer), customer / undercover agent (the victim, two looks: fishing hat + yellow jacket,
  then suit + badge), claims-office clerk, two police officers. The victim appears in the hook and the reveal.
- **Lip-sync on 3 lines:** "Sorry man, not a winner", "Story of my life", "Wow, congratulations! Just wait right here."
- **Props that carry jokes:** "REEL BIG CASH" fishing-themed ticket (store is a bait shop), register screen
  "WINNER!", the lure-covered fishing hat (reappears on the agent), the wallet with ID, goldfish bowl in bed, yacht
  name, "PLACE TICKET HERE" slot, "OUR WINNERS" wall (he'll never be on it), the polaroid, two piles "CLERKS" vs
  "EVERYONE ELSE", the bait-ticket cabinet, "BAIT · GAS" sign (pun on bait).
- **Pace:** act 1 has 7 setups in 17 s; the office waiting room holds 11 s with only a slow push (the tension beat);
  the explainer is fast again (1.3–2 s per setup).
- **Faces:** cashier smug → shocked + sweat → deadpan lie → blissful → grinning → panicked. Agent stays flat.
- **Captions:** 1–2 words, ~60 px text, centre at 70% of frame height, present on 90% of samples.
- **Sound:** -15.2 LUFS, LRA 2.1 LU; continuous bed.
