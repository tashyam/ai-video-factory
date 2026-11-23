"""Flag script sentences that ask the rig for something it can't show (story/rig-check.md).

Usage: python tools/rig_check.py <project>/script.json
Prints one line per hit: sentence number, the trigger word, and the substitution to consider. Exit 1 if anything was
flagged, so it can gate a pipeline. A hit is a prompt to look, not proof of a problem ("pocket" on a shirt is fine).
"""
import json, re, sys

RULES = [  # (regex, what's wrong, stage it as)
    (r"\b(sock|socks|shoe|shoes|boot|boots|glove|gloves|sleeve|sleeves|watch|wristwatch|ring|bracelet|anklet)\b",
     "worn on an arm or leg: limbs are single ink strokes", "a prop container (stash sock on a nail, tin, till) or something on the torso"),
    (r"\b(trouser|pants|jeans|back) pockets?\b|\bwaistband\b",
     "below the torso: legs can't hold things", "a breast pocket on the torso garment, or a prop container"),
    (r"\b(finger|fingers|thumb|thumbs|knuckle|nail|nails|fist ?bump|snap(s|ped)? (his|her) fingers)\b",
     "fingers: hands are round ink blobs", "show the object reacting, or a close-up of the object"),
    (r"\b(count(s|ed|ing)?|writ(es|ing|ten)|wrote|sign(s|ed|ing)?|typ(es|ed|ing)|scribbl\w*)\b",
     "fine hand action", "a close-up of the paper or screen, or a cash stack or burst"),
    (r"\b(kneel\w*|crawl\w*|crouch\w*|squat\w*|lies|lying|lay down|rolls? over|bends? over|bent over|face[- ]?down|upside[- ]?down|cartwheel\w*|somersault\w*)\b",
     "torso can only lean; head can't be shown inverted", "dissolve to the result (sitOn a bed or bench), or lean at most 0.6 rad"),
    (r"\b(hug\w*|embrac\w*|shak(es|ing) hands|handshake|grab(s|bed)? (him|her|them)|carr(y|ies|ied) (him|her|them)|punch\w*|wrestl\w*)\b",
     "contact between characters", "step close with arms up and a heart or sparkle, or an impact effect without contact"),
    (r"\b(changes? (clothes|outfit)|puts? on (a|his|her) (disguise|costume|wig|dress|suit))\b",
     "costume change on screen", "dissolve to a second character spec in the new outfit"),
    (r"\b(hair ?flip|haircut|tears? (stream|roll)\w*|make-?up|lipstick)\b",
     "hair, tear or make-up action", "an expression change plus a prop"),
]

def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(2)
    script = json.load(open(sys.argv[1], encoding="utf8"))
    hits = 0
    for i, s in enumerate(script, 1):
        for rx, why, alt in RULES:
            for m in re.finditer(rx, s, re.I):
                hits += 1
                print(f'S{i}: "{m.group(0)}" -> {why}. Stage it as: {alt}.')
    print(f"rig check: {len(script)} sentences, {hits} flag(s)" + ("" if hits else ", all clear"))
    sys.exit(1 if hits else 0)

if __name__ == "__main__":
    main()
