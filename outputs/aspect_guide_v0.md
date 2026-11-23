# Aspect Annotation Guide v0

**Status:** draft, written by reading all 200 reviews in [steam_pilot.jsonl](steam_pilot.jsonl). Revise it after the first 50-review pass and the overlap adjudication, and record every change in the change log at the bottom. Machine-readable labels and example cue words are in [configs/aspect_lexicon_v0.json](../configs/aspect_lexicon_v0.json).

The pilot covers five Valve multiplayer and co-op games (Dota 2, CS2, TF2, Portal 2, Left 4 Dead 2). That is why `cheating_moderation` and `matchmaking_ranking` are separate categories. Before final annotation, check the categories on the 100-game catalogue. Single-player RPGs, survival and simulation games may need different splits.

## What to annotate

For each review, record zero or more **(aspect, sentiment, evidence)** triples:

- **Aspect:** what the reviewer talks about. Use one category from the table below.
- **Sentiment:** the reviewer's opinion about that aspect: `positive`, `negative`, `neutral` or `mixed`.
- **Evidence:** the shortest exact span copied from the review that shows both the aspect and the opinion. Copy it character for character, without paraphrasing or fixing typos. The evaluator rejects any span that is not an exact substring.

**Do not look at, or infer, `voted_up`.** The worksheet hides it on purpose. A reviewer who recommends a game can still criticize its servers, and a reviewer who does not recommend it can still praise its gameplay.

## Categories

| Aspect | Covers | Typical cues in the pilot | Does not cover |
| --- | --- | --- | --- |
| `gameplay` | Mechanics, controls, combat/gunplay, puzzles, heroes/classes/weapons, strategy, depth, difficulty, pacing, hero/weapon balance, replayability | "clever puzzles", "the gunplay", "lacks balance", "steep learning curve", "never gets old" | Team-balance problems in matches (`matchmaking_ranking`) |
| `modes_content` | Maps, levels, campaign, co-op/versus/casual modes as content, game length, workshop/mods/community maps | "co-op mode is awesome", "longer than the first", "workshop support", "missing content and maps" | Whether matches can be found in a mode (`matchmaking_ranking`) |
| `story_characters` | Story, plot, lore, characters, dialogue, writing, humor, voice acting, ending | "well written", "funny story and characters", "fenomenal voice acting" | Jokes the reviewer makes themselves |
| `audiovisual` | Graphics, visuals, art style, animation, music, sound, gore effects | "Graphics hold up", "nice music", "funny ragdolls" | FPS or stutter (`performance_stability`) |
| `performance_stability` | FPS, stutter, optimization, crashes, bugs, server/connection reliability, system requirements | "poorly optimized", "constant FPS fluctuations", "could run on a toaster", "Game isn't buggy" | Bot accounts or cheaters (`cheating_moderation`) |
| `matchmaking_ranking` | Matchmaking, queue times, ranked/MMR/Elo, team balance in matches, smurfs/boosters as a fairness issue | "matchmaking is complete and utter dogshit", "Rank system is broken", "smurf accounts in lower rank" | Penalties and reports (`cheating_moderation`) |
| `players_community` | Other players and the social experience: teammates, toxicity, community, playing with friends/randoms | "toxic teammates", "fun with friends", "lovely community" | Systems that punish players (`cheating_moderation`) |
| `cheating_moderation` | Cheaters/hackers, bot accounts, anti-cheat/VAC, bans, reports, behavior/communication scores, penalties, vote kicks | "anti-cheat is banning innocent players", "bots flood the servers", "worst commend and report system" | Developers' general neglect (`developer_support`) |
| `developer_support` | Developer/publisher care: updates, patches, fixes, neglect/abandonment, customer support | "abandoned by the developers", "no MAJOR updates", "Valve, fix your game" | A specific system being broken (label that system's aspect) |
| `value_monetization` | Price, value for money, free-to-play, skins/cosmetics, cases, gambling, paid subscriptions | "worth the 10 euro", "dirt cheap", "required to buy dota plus" | "Worth my time" with no money sense (`overall`) |

Special labels:

- `overall`: a judgment of the whole game with no specific aspect, such as "Great game", "10/10" or "masterpiece". Annotate it, but it is scored separately and kept out of O(u,i).
- `none`: write **one** row with `aspect=none` and empty sentiment and evidence when a review has no aspect and no overall judgment. Examples are pure jokes, off-topic text and non-English text. Without this row the review looks unannotated.

## Sentiment rules

1. `positive` / `negative`: the reviewer clearly praises or criticizes the aspect.
2. `neutral`: the aspect is mentioned with no opinion ("I mostly play co-op", "the game is free").
3. `mixed`: the same aspect gets both praise and criticism and you cannot separate them into two spans ("sea server still as bad a decade ago and I love it"). If they can be separated, use two rows with the same aspect. The evaluator merges positive and negative into `mixed` automatically.
4. **Sarcasm:** label what the reviewer means, not the literal words, and add `sarcasm` to notes. For example, "Very good game with no cheaters, all legit players, great VAC AI" is `cheating_moderation`, `negative`. Only call it sarcasm if the text gives clear evidence. If you aren't sure, add `uncertain` to notes.
5. **Past vs. present:** "The game used to be fun" describes the past. Label the opinion about the current state when the review gives one; otherwise label the past opinion and add `past_state` to notes.
6. **Comparisons:** "CS:GO was better by far" with no aspect named is `overall`, `negative` for the reviewed game. If an aspect is named ("clunky gameplay"), label that aspect.
7. **Requests or demands:** "Valve please fix the bot problem" implies the aspect is currently bad, so label it `negative` (`cheating_moderation`).

## Aspect rules for ambiguous cases

| Case from the pilot | Decision | Reason |
| --- | --- | --- |
| "bots flood the servers, you cannot join a casual game" (TF2) | `cheating_moderation` negative; add `matchmaking_ranking` negative only if matchmaking itself is criticized | The cause named is bot accounts, not the server hardware |
| "Game is bugged ... Can't join games in EU West" | `performance_stability` negative | A technical failure to connect |
| "4 players can report you for communication abuse" | `cheating_moderation` negative | Criticizes the report/penalty system, not the people |
| "the people are terrible" | `players_community` negative | Criticizes other players |
| "smurfs and noob account buyers are 70% of the players" | `matchmaking_ranking` negative | Smurfing hurts match fairness. Use `cheating_moderation` only if hacks or cheats are mentioned |
| "fun to play with friends" | `players_community` positive | The social experience. Use `modes_content` only if a mode is named ("co-op mode is great") |
| "it runs great if u set graphics to low" | `performance_stability` positive | About performance, even though "graphics" appears |
| "Great game and the co-op mode is also awesome" | `overall` positive + `modes_content` positive | Two separate judgments |
| "The game is free, but the therapy after that isn't. 10/10" | `value_monetization` neutral + `overall` positive, `sarcasm`/`joke` in notes | Joke review; keep the literal price mention as neutral |
| "Peak gaming experience" after a list of abuse | `players_community` negative, `sarcasm` in notes | The context gives the meaning |
| "i mostly only collect the skins" | `value_monetization` neutral | Mention with no opinion |
| "Valve's TRUE Timeless Master Piece" | `overall` positive | No specific aspect; "Valve" alone is not `developer_support` |

Rule of thumb: when two categories seem to fit, choose the one that names **what the reviewer wants changed or praises**, not the side effect. If you are still unsure, add `ambiguous:<other_aspect>` to notes so the adjudication can revisit it.

## Evidence span rules

- Shortest span that contains both the aspect cue and the opinion, usually one clause.
- Copy it exactly, including typos ("fenomenal voice acting") and casing.
- Do not join text from different sentences. If the opinion and the aspect are in different sentences, take the sentence with the opinion and explain in notes.
- No surrounding quotes or trailing spaces.

## Notes vocabulary

Use comma-separated tags: `sarcasm`, `joke`, `uncertain`, `past_state`, `not_english`, `ambiguous:<aspect>`, `implicit` (aspect implied rather than named), and free text after the tags.

## Procedure

1. Open [annotation_batch_v0.csv](annotation_batch_v0.csv): 50 reviews, 10 per game, 16 not recommended (the worksheet does not say which). Reviews marked `overlap=yes` (15) are also labelled independently by a second teammate.
2. Add your rows to [aspect_annotations_v0.csv](aspect_annotations_v0.csv) with columns `review_id, annotator_id, aspect, sentiment, evidence, notes`. Use a stable `annotator_id` (for example `m4`, `m2`). Open the CSV as UTF-8 and keep the quotes around evidence that contains commas.
3. Don't discuss overlap reviews until both annotators have finished them.
4. Run `python scripts/opinion_evaluate.py`. It validates labels and spans, then writes agreement and a disagreement list to `outputs/annotation_disagreements_v0.csv`.
5. Adjudicate together. For each overlap review, write the agreed labels under `annotator_id=adjudicated`. Update this guide when a disagreement shows a rule is unclear.
6. Don't use LLM output as human labels. An extractor can only be scored against labels written by people. [aspect_annotations_v0_claude_draft.csv](aspect_annotations_v0_claude_draft.csv) is an LLM pre-annotation. The primary annotator may use it as a starting point, but must check every row against the text and this guide, fix or delete wrong rows, add missed ones, and then write the result under their own `annotator_id`. Report that the gold labels were LLM-assisted and then human-corrected. The **second** overlap annotator must not see the draft or the first annotator's labels.

## Change log

- v0 (2026-11-23): initial 10 aspects + `overall` / `none`, drafted from the 200-review pilot. Not yet tested on a second annotator.
