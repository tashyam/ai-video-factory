# Script check

Score every draft before showing it to the user. One point each (11 checks). **Below 10, rewrite**, then show the user the
script and the score (list any missed checks).

| # | Check | How to test |
|---|---|---|
| 1 | Hook pays off within 5 s | Hook sentence is 15–18 words with a visible result at the end |
| 2 | Loophole stated by 10 s | Sentence 2 contains "because" and the rule |
| 3 | First sentence doesn't answer the title | The invention and its purpose are absent from sentence 1 |
| 4 | List of three | Beat 5 has exactly three targets, each picturable |
| 5 | Two escalations | Beat 6 (a helper or tool) and beat 7 (absurd excess) both present |
| 6 | Pushback dialogue | Exactly two spoken lines; line A has a number; line B is a deadpan excuse |
| 7 | Two "But" turns | At about 63% and about 81% of the word count |
| 8 | Silent winner | The victim never speaks |
| 9 | Visual reveal, name last | The invention is shown before it is named; its real name appears only in the tag |
| 10 | Length and pace | 225–245 words, 16–19 sentences, no sentence over 26 words |
| 11 | Rig check | Every action can be shown by our characters (`story/rig-check.md`): `python tools/rig_check.py <project>/script.json`. Each flag is either a false alarm you can name ("counts the tiles" = eyes, not hands) or gets a "Stage it as" note, or the sentence is rewritten. Any unhandled flag = 0 for this check |

Also reject the draft if any of these is true (no score, just fix it):

- A real person, company, brand or product name appears.
- The scheme reads as a usable how-to for real fraud. Keep it at "what he does, why it works" in one sentence.
- A sentence can't be shown in one or two camera setups.
- A sentence asks the rig for something on the "Can't" list of `story/rig-check.md` with no "Stage it as" note.
- An em dash, rhetorical question or moral appears in the narration.

## Word-position helper

With N words total: hook ends at about 0.07N, "But" #1 at about 0.63N, "But" #2 at about 0.81N, the reveal object at
about 0.88N.
