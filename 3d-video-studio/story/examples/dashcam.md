# Example: "Why Drivers Started Filming The Road"

> The reference's frames (`frames/`, `transitions/`, `beats.jpg`) are not included in the public repo. Run `tools/ref_profile.py` on the reference video to rebuild them; `profile.json` (the numbers) is included.

Reference Short (third-party video: learn the recipe, never copy its characters, designs or script).
62.2 s, 1080x1920, 30 fps. 238 words, 3.82 words/s, 17 sentences. 19 camera setups (mean 3.3 s, median 2.6 s,
range 1.1 to 9.0 s). 7 hard cuts, 11 gradual transitions. -14.2 LUFS, loudness range 2.2 LU.
Measured with `tools/analyze_ref.py` and a frame-count check of every transition; pictures labelled from
57 frames (start, middle, end of each setup). **Don't re-watch the video; this file and the measured profile
in `dashcam/` replace it.**
- `dashcam/profile.json`: the numbers every gate compares against.
- `dashcam/frames/`: one frame per setup, the reference side of pair sheets.
- `dashcam/transitions/`: every frame of each transition.

## Transitions, frame by frame (measured 2026-11-14)
- **Hard cuts:** one frame changes the whole picture; nothing is mixed.
- **Dissolves:** 7 to 10 frames (median 8) on an eased curve, for example 0.09, 0.23, 0.43, 0.64, 0.81, 0.94. Both
  shots keep moving through the mix. The slow dissolve from the schemer's caught face into the dashcam footage is
  16 frames.
- **Captions** change on the spoken word, independent of the transition; a caption often switches in the middle of a
  dissolve.
- **Fly-out (frames 33–45, about 9 frames):**
  - the camera passes the windshield with a single glare frame;
  - it skims the bonnet while red fills the frame for 2 to 3 frames;
  - it pulls back fast to a wide in which the car is about a quarter of the frame width.
  - The frames stay fairly crisp: no long smear.
- **Cash burst (frames 463–488):**
  - 3D bills stream out of the scene toward the lens;
  - at most about 65% of the frame is covered, and the schemer stays visible inside the burst;
  - the next shot dissolves in under the bills over about 4 frames (480–484) while bills are still flying.
- **Wiper wipe into the rain act (frames 1300–1316):**
  - a black wiper blade enters from the bottom left and sweeps across the frame;
  - the rain shot is revealed directly behind the blade, with no grey fade first;
  - the blade leaves on the left edge about 6 frames later.
- **Into dusk (frames 548–560):** a 6-frame dissolve from the day shot into the dusk head-on shot, with both cameras
  moving.

## Detail measured at full resolution
- **Gauge cluster in the POV shot:** readable numerals, needles, PRND, a warning line ("CHECK AIRBAG SYSTEM"),
  outside temperature and an odometer. The steering wheel, a screen and the bonnet are in frame.
- **Office wall:** framed photos of the schemer with gold plaques are readable at 1:1; there is also a skyline in the
  window and a nameplate.
- **Cars:** panel gaps, door handles, chrome trim, window reflections and blooming headlights.
- **Sharpness:** Laplacian variance on matched frames is 480 to 850 (ours was 94 to 290). Edge density per act is
  0.27, 0.21 and 0.14.
- **Faces in the key shots, as a share of frame width:** talker about 45%; the caught schemer filling the dashcam view
  about 70%; the night driveway trio large, at eye level, in a pool of light.

## Setup by setup

`In` = how the setup starts: **CUT** (one frame), **dissolve** or **in-world** (a fly-through, cash burst or wiper;
frame count in brackets). Act: ☀ day, 🌆 dusk/night, 🌧 rain.

| # | Time | In | Camera | Picture: who, what, props | Narration | Act |
|---|---|---|---|---|---|---|
| 1 | 0.0–1.1 | — | **Tilted ultra-wide interior** | Schemer (yellow shirt, messy brown hair) at the wheel, foot on the brake pedal, phone glowing on the seat. Face goes from **grit to smug grin** in about 0.6 s. | He slammed the brakes | ☀ |
| 2 | 1.1–3.4 | in-world (7f): fly-out through the windshield | **Tracking**, low front three-quarter, then low side | His red coupe brakes; a white SUV closes in behind, its driver visible through the glass. Debris starts on "smashes". | on the highway and the car behind him smashes | ☀ |
| 3 | 3.4–4.7 | **CUT** on the impact | High, close, over the SUV's bonnet | SUV nose buried in the coupe's bumper; SUV driver's face goes to **round-eyed shock**; red flecks of debris. | right into his bumper. | ☀ |
| 4 | 4.7–7.0 | dissolve (11f) | **POV over the SUV's dashboard** (gauges, screen) | Ahead, the schemer climbs out, grabs his neck and limps. Overhead highway signs. | He climbs out, holding his neck and limping, | ☀ |
| 5 | 7.0–10.3 | **CUT** on "because" | Low roadside two-shot | The rear driver (green shirt) stands bewildered; the schemer leans on his car with a **sweat drop**, then collapses on the tarmac clutching his neck. | because he figures whoever hits you from behind always gets the blame. | ☀ |
| 6 | 10.3–12.8 | dissolve (15f): time jump | **Low wide on the house and lawn** (garden hose on the grass) | Schemer in a neck brace by his repaired car; an insurance adjuster in a dark suit arrives with a briefcase and a **"PAID" sign** and plants it on the car. | And sure enough, their insurance pays for his car, | ☀ |
| 7 | 12.8–16.1 | **CUT** on the list | Same lawn, closer | **A hospital bed on the front lawn**, a doctor beside it; the schemer lounges in it and takes a cheque. Ends on a **cash burst** filling the frame. | his doctor, and a nice fat check for all that pain he's in. | ☀ |
| 8 | 16.1–18.6 | in-world (9f): the cash burst clears | **Tracking**, high three-quarter, then side | Red coupe back on the highway, pulling up beside a teal minivan ("different car"). | So the next week, he does it again with a different car. | ☀ |
| 9 | 18.6–27.6 | dissolve (6f) into dusk | **One 9 s move**: head-on, orbiting about 120° to a high three-quarter | **Purple dusk sky.** Head-on of the coupe with possible targets in the lanes behind; the orbit lands as a black pickup (the buddy) boxes a teal car in beside him. | He picks them carefully. A guy on his phone, a kid who just got his license, anyone driving a little too close. Then he brings a buddy who drives right beside you so you can't swerve. | 🌆 |
| 10 | 27.6–29.6 | dissolve (22f) | **Low wide on the house** (garage door) | The schemer in front of the garage; a **mountain of cash bundles** grows until he stands on top with his arms up. | The money comes in so fast, he | 🌆 |
| 11 | 29.6–32.2 | **CUT** on "buys" | Low wide, night driveway | A new **green sports car with a red gift bow**; a white van ploughs into it; bills fly, cash pile in the foreground. | buys a nicer car, just to crash that one too. | 🌆 |
| 12 | 32.2–36.6 | dissolve (17f) from the smoking wreck | **Centred slow push-in on a talker** | Office: an insurance agent (black hair, navy suit) at a desk, a skyline in the window, **framed photos of the schemer on the wall**. The desk counter **"2 DAYS SINCE … NECK INJURY" flips to "0"** on "this". **Lip-sync.** | Eventually, the insurance company starts calling. Sir, this is your fifth neck injury this year. | 🌆 |
| 13 | 36.6–38.6 | **CUT** on the reply | Centred push-in on a talker | Night backyard pool under string lights: the schemer floating, **sunglasses on his head, phone to his ear, a rubber duck**. Smug. **Lip-sync.** | Yeah, I've got a really weak neck. | 🌆 |
| 14 | 38.6–43.5 | **CUT** on "But" | Low wide, night driveway | The schemer, a **highway patrol officer (campaign hat)** and a rear driver with glasses. The officer glares at the rear driver, who looks worried; the schemer looks innocent. | But it's his word against the guy who hit him, and he's counting on everyone blaming the guy in the back. | 🌆 |
| 15 | 43.5–46.8 | **in-world (12f): a wiper blade wipes** | Side close, then push-in on the face | **Rain.** An old **wood-panelled station wagon**; the quiet driver (dark hair, maroon hoodie) with a coffee cup on the dash. **Flat, unbothered face.** | Then, one rainy morning, he picks a quiet guy in an old car, | 🌧 |
| 16 | 46.8–49.9 | slow dissolve (26f) | **POV over the old analogue dashboard** | Rain on the glass; the red coupe ahead brakes hard; the schemer climbs out, clutching his neck. | slams on his brakes, and out he comes, clutching his neck. | 🌧 |
| 17 | 49.9–55.0 | dissolve (11f) | **Tilted ultra-wide interior** of the wagon (echoes setup 1) | The quiet guy in the foreground, the schemer at the side window. A **small box on the windshield**; the quiet guy **points up at it** (the camera pans with the arm); the schemer presses his face to the glass, still sly. | But the quiet guy doesn't yell, and he doesn't even get out. He just points at a little box taped to his windshield. | 🌧 |
| 18 | 55.0–60.0 | **CUT** on the reveal | **The camera's own view**, then **locked-off dashcam footage** (the only static shot) | The schemer's face fills the frame: **shock with a sweat drop**. Then the footage: **REC dot, date stamp, speed 54 → 46 → 0 MPH**, an empty rainy road, the red car braking for nothing. | It's a camera, and it filmed an empty road and a man braking for absolutely nothing. | 🌧 |
| 19 | 60.0–62.2 | dissolve (6f) | Wide interior, slow push-in | The quiet guy, deadpan, the camera box glowing red on the windshield. Ends inside a car like the opening, so it loops. | And that's how the dash cam was invented. | 🌧 |

## What the details show

**Cast (8 characters, 2 lines of lip-sync):** schemer, first rear driver, adjuster, doctor, buddy (a car more
than a person), insurance agent, patrol officer, quiet guy. Every new beat brings in a new character or location.
Only the schemer appears in every act.

**Camera setups used:** tilted interior ×3 (1, 17, 19), POV over a dashboard ×2 (4, 16), vehicle tracking ×3
(2, 8, 9), high close ×1 (3), low wide on a house or driveway ×5 (6, 7, 10, 11, 14), centred push-in on a talker
×3 (12, 13, 15), device view ×1 (18). The house and driveway is home base for the payoff and excess beats.

**When it cuts and when it dissolves:**
- **Hard cuts (7)** land on a jolt or punchline: the impact (3), the motive (5), the list topping itself (7), the
  purchase (11), the dialogue reply (13), the "But" (14), the reveal (18).
- **In-world transitions (3)** mark big beats: the fly-out (hook), the cash burst (end of first payoff), the wiper
  (start of the rain act).
- **Dissolves (8)** cover time or place jumps (6, 9, 10, 12) and the calm rain sequence (16, 17, 19).
- **Act 3 has a single hard cut, on the reveal.** Everything else there is slow and soft, so the reveal hits harder.

**Pace by act:** act 1 runs 7 setups in 16 s (2.3 s each); act 2 slows down with the 9 s orbit and the dialogue;
act 3 holds 3 to 5 s per setup. The pace slows as the story heads to the ending.

**Faces:** the schemer cycles grit → smug → grin → pained (fake) → innocent → shocked; the sweat drop appears
twice (when he collapses in setup 5 and when he's caught in 18). The quiet guy keeps the same flat face for the
whole act. The stillness is the joke.

**Props that carry jokes:** the phone on the seat, the PAID sign, a hospital bed on the lawn, the neck brace, the
cash mountain, a gift bow on a car bought to be crashed, framed photos of the schemer in the insurer's office, the
"days since neck injury" counter resetting, sunglasses and a rubber duck during the "weak neck" call, the
wood-panelled wagon and coffee cup (humble = trustworthy), the dashcam overlay with the speed dropping to 0.
**There is roughly one prop gag per setup.**

**Captions:** 1 to 2 words, white with a black outline, centred at about 70% of frame height, on every frame.

**Sound:** -14.2 LUFS with only 2.2 LU of loudness range (heavily levelled). The half-second level never drops below
about -43 dB after the first 0.5 s, so there is a continuous bed under the narration. Music and SFX weren't
identified by ear.
