# Rig check: what our world can show

Our characters are flat 2D figures in a 3D world, so some things a sentence can say can't be pictured:
- the head is a face billboard that always turns to the camera;
- the torso is a capsule that can only lean;
- arms and legs are single ink strokes ending in round ink hands and feet.

**Every action in the script must be on the "Can" list, or have a "Stage it as" substitution written next to it, before
the voice is recorded.** Run `python tools/rig_check.py <project>/script.json` at step 2 and again at step 5. It flags
trigger words; the judgement is yours.

## Can (works with the rig)
| Area | What works | Engine |
|---|---|---|
| Body | stand, walk, sit (chair, sofa, bed, car seat), lean forward or back up to about 0.6 rad, bob or jump (hip offset) | `stand`, `walk`, `sitOn`, `sit` |
| Arms | point, wave, arms up, hands on hips, phone to ear, hand on neck, cross arms, shrug; one hand to any exact point (`armTo` in the cashier video) | `stand({arms})`, pose override |
| Hands | hold a prop at the hand point, as long as the prop is **bigger than the hand** (about 0.1 m or more: ticket, phone, scanner, cup, cane, badge, sign) | prop follows the hand point every frame |
| Clothes | anything on the **torso**: polo, shirt, apron, jacket, cardigan, vest, badge, name tag, a breast pocket drawn on the garment | `outfit`, torso decals |
| Head | caps, glasses, headset, beard, mustache, blush; 14 expressions, lip-sync, blinks, sweat drop, expression pop | `acc`, `exprAt`, `talkAt` |
| Staging | a character half hidden behind an object **only if the head stays outside it** (hips and legs out of a bin) | sink the neck below the rim |

## Can't (rewrite or stage differently)
| Don't write | Why |
|---|---|
| socks, shoes, gloves, watches, rings, sleeves, trouser pockets, anything **on an arm or leg** | limbs are single ink strokes; there is no surface to put it on |
| putting something **into** a sock, shoe, sleeve, trouser pocket or waistband | same |
| fingers: counting bills, writing, typing close-up, snapping, thumbs up, picking a pocket, a fine grip | hands are round ink blobs |
| a head seen from directly above or below, upside down, face-down, or inside an object | the face billboard always turns to the camera and pokes through walls |
| bending at the waist, crouching, kneeling, crawling, lying on the floor, rolling | the torso is a straight capsule that only leans |
| hugs, handshakes, grabbing or carrying another character, fights with contact | limbs can't wrap or grip a body |
| changing clothes on screen, a costume growing or appearing | outfits are per character spec |
| hair actions (flip, wind, haircut), tears streaming, make-up | the hair is a fixed cap; there are no tear or make-up layers |

## Stage it as (substitutions that keep the joke)
| The script says | Show instead |
|---|---|
| "into his sock / pocket / shoe" | a **prop container** the character uses: a stash sock hanging on a nail, a tin, the till, a jar; or a pocket on the **torso** garment |
| "counts the money" | a fanned stack in one hand, a cash pile growing, a cash burst |
| "writes / signs / types" | a close-up of the paper or screen itself; the hand is just near it |
| "headfirst into X" | torso sunk inside, only the hips and kicking legs out; the head never shows |
| "falls / lies down / faints" | dissolve to the result: on a bed or bench with `sitOn`, or a stretcher prop |
| "hugs / shakes hands" | two characters step close, arms up, a heart or sparkle effect between them |
| "puts on a disguise / changes clothes" | dissolve to a second character spec in the new outfit |
| "looks down into / up out of X" | a low or high angle of about 35° at most, never straight up or down; frame the ring or rim with an overlay |

## In the storyboard (step 5)
The "action and faces" column names an engine pose (`stand`, `walk`, `sitOn`, `point`, `lean`, `armTo`…) or a prop for
every action. If a row needs anything else, it's a rig-check failure: rewrite the row before building.

## Real-life check: would a real person do this?
The rig check asks whether our characters *can* do something. This one asks whether a real person *would*. Run it on
every storyboard row before the gate. Without it, the build follows the continuity chain literally, and the result
reads as wrong to any viewer even when every frame is technically right.

**Story objects and gag props.** In the continuity table, label every prop as one of two kinds:
- **story object:** the thing the plot is about (the ticket, the money, the key, the evidence). It travels from scene
  to scene, and the viewer follows it.
- **gag prop:** a hiding place, a container, a tool or a joke object (a stash sock, a tin, a disguise, the bin). It
  lives only in the beat of its joke.

A gag prop that appears in a new location is a failure unless the narration mentions it there. Show the story object
on its own, in a hand, a pocket on the torso garment or a bag the character would really carry.

**Hiding places are temporary.** People hide something to keep it safe for now. When they act on it (claim it, spend
it, hand it over), they take the thing out and carry only the thing. A container comes along only when the
narration says so, or when the container itself is the joke of that beat.

**Time jumps reset the small stuff.** After a narrated time jump ("by lunch", "the next morning", "at sunrise", "a
week later"), characters may have done ordinary things off screen (got dressed, took the ticket out of its hiding
place, drove to work). In the new scene they carry only what a real person would bring for that errand. The rule
"no setup may start from a state the viewer never saw" covers continuous time and changes the plot depends on; it
doesn't ask to show ordinary off-screen steps across a jump.

**Every action has a reason in the moment.** For each action and each carried item, name why a real person would do
it right then. "Because the continuity chain had it in the last scene" is not a reason. If the only reason is
continuity, drop the item or rewrite the row.

**Carry line per location.** Under the continuity table, write one line per location: who is there, what each
person carries and why, for example `HQ claims window: cashier carries the ticket (to claim it)`. The user reads
these at the storyboard gate; it is the fastest place to catch a prop that shouldn't be there.
