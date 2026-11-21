# Steam expanded pilot: crawl, quality and overlap

Generated at 2026-11-21T09:08:16.081481Z. Dataset: `steam_100games_v1`. Crawl status: **completed**.

**STEAM SOURCE DECISION REQUIRES SHARED SPLIT CHECK.** The snapshot has 100 games, 169 users with at least two positive games and 37 with at least three. Expanding the item catalog removes the old 20-item Recall@20 limitation, but does not establish chronological warm-start coverage. Members 2/3 must report eligible users and targets under the shared historical split before training or choosing a source. No universal minimum-user threshold or model-quality result is asserted here.

This is a recommendation for the project lead, not an automatic dataset switch. No Amazon data was fetched or merged.

## Collection and provenance

- Source: https://api.steampowered.com/IUserReviewsService/GetAppReviews/v1/
- API documentation: https://partner.steamgames.com/doc/webapi/IUserReviewsService?l=english
- Start / finish UTC: 2026-11-21T09:04:14.962398Z / 2026-11-21T09:07:35.498259Z
- Configured games: 100; target per game: 100; page size: 100.
- Parameters: recent (filter=1), English, all recommendation labels (review_type=0), all purchase types (purchase_type=1), off-topic filtering enabled. Parameters are passed as input_json.
- Selection: Bounded convenience sample of 100 manually selected PC games across genres, including the 20 earlier pilot games. 100 recent English reviews per game, independently recrawled; not representative of Steam or players. No selection based on model/test performance.
- Crawl attempts: 101; successful: 101; failed: 0; HTTP 429: 0.
- Access probe attempts are recorded separately in the same request log and excluded from these crawl counts.
- See steam_access_check.json for this machine's access test; a teammate on a different network must test there separately.
- Cursor and per-game progress are saved after each page. Data is saved atomically before the manifest; a replay after a crash deduplicates existing review IDs.
- Local synthetic tests cover crash/replay and HTTP 429. Live bounded pause/resume is recorded in the manifest run_history; these are distinct from simulated failures.

## Data quality

| Check | Value |
| --- | ---: |
| Saved reviews | 10000 |
| Unique review IDs | 10000 |
| Duplicate IDs in saved file | 0 |
| Repeated user-game records | 0 |
| Blank review bodies | 47 |
| Bodies with at most 3 whitespace tokens (descriptive only) | 3147 |
| Schema-invalid saved records | 0 |
| Duplicate observations skipped during requests/replay | 0 |
| Invalid observations excluded before saving | 0 |
| Distinct reviewers | 9718 |
| Distinct games | 100 |
| Positive recommendations | 8659 |
| Negative recommendations | 1341 |

Review creation-time range UTC: 2026-07-01T20:28:53+00:00 to 2026-11-21T09:02:16+00:00.
Update timestamps preserved: 10000 / 10000; last update later than creation: 422. Older snapshots may not have this optional field.
All saved reviewer IDs pass the 64-character lowercase SHA-256 format check. The saved schema excludes raw author objects and SteamIDs. Source language labels were checked; no independent language classifier was run.

## Per-game coverage

| App ID | Configured game label | Reviews | Positive | Negative | Pages | Status |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| 570 | Dota 2 | 100 | 77 | 23 | 1 | target_reached |
| 730 | Counter-Strike 2 | 100 | 86 | 14 | 1 | target_reached |
| 440 | Team Fortress 2 | 100 | 96 | 4 | 1 | target_reached |
| 620 | Portal 2 | 100 | 100 | 0 | 1 | target_reached |
| 550 | Left 4 Dead 2 | 100 | 98 | 2 | 1 | target_reached |
| 400 | Portal | 100 | 98 | 2 | 1 | target_reached |
| 220 | Half-Life 2 | 100 | 99 | 1 | 1 | target_reached |
| 4000 | Garry's Mod | 100 | 97 | 3 | 1 | target_reached |
| 105600 | Terraria | 100 | 99 | 1 | 1 | target_reached |
| 413150 | Stardew Valley | 100 | 96 | 4 | 1 | target_reached |
| 1091500 | Cyberpunk 2077 | 100 | 94 | 6 | 1 | target_reached |
| 1245620 | ELDEN RING | 100 | 94 | 6 | 1 | target_reached |
| 1086940 | Baldur's Gate 3 | 100 | 96 | 4 | 1 | target_reached |
| 292030 | The Witcher 3: Wild Hunt | 100 | 92 | 8 | 1 | target_reached |
| 1174180 | Red Dead Redemption 2 | 100 | 85 | 15 | 1 | target_reached |
| 367520 | Hollow Knight | 100 | 99 | 1 | 1 | target_reached |
| 1145360 | Hades | 100 | 98 | 2 | 1 | target_reached |
| 646570 | Slay the Spire | 100 | 94 | 6 | 1 | target_reached |
| 294100 | RimWorld | 100 | 99 | 1 | 1 | target_reached |
| 548430 | Deep Rock Galactic | 100 | 93 | 7 | 1 | target_reached |
| 271590 | Grand Theft Auto V Legacy | 100 | 93 | 7 | 1 | target_reached |
| 1172470 | Apex Legends | 100 | 65 | 35 | 1 | target_reached |
| 578080 | PUBG: BATTLEGROUNDS | 100 | 69 | 31 | 1 | target_reached |
| 252490 | Rust | 100 | 77 | 23 | 1 | target_reached |
| 346110 | ARK: Survival Evolved | 100 | 78 | 22 | 1 | target_reached |
| 945360 | Among Us | 100 | 91 | 9 | 1 | target_reached |
| 1794680 | Vampire Survivors | 100 | 94 | 6 | 1 | target_reached |
| 1966720 | Lethal Company | 100 | 92 | 8 | 1 | target_reached |
| 1623730 | Palworld | 100 | 97 | 3 | 1 | target_reached |
| 892970 | Valheim | 100 | 84 | 16 | 1 | target_reached |
| 108600 | Project Zomboid | 100 | 94 | 6 | 1 | target_reached |
| 1144200 | Ready or Not | 100 | 90 | 10 | 1 | target_reached |
| 1938090 | Call of Duty | 100 | 57 | 43 | 1 | target_reached |
| 359550 | Tom Clancy's Rainbow Six Siege | 100 | 72 | 28 | 1 | target_reached |
| 381210 | Dead by Daylight | 100 | 75 | 25 | 1 | target_reached |
| 322330 | Don't Starve Together | 100 | 83 | 17 | 1 | target_reached |
| 219740 | Don't Starve | 100 | 89 | 11 | 2 | target_reached |
| 275850 | No Man's Sky | 100 | 88 | 12 | 1 | target_reached |
| 264710 | Subnautica | 100 | 98 | 2 | 1 | target_reached |
| 848450 | Subnautica: Below Zero | 100 | 89 | 11 | 1 | target_reached |
| 242760 | The Forest | 100 | 88 | 12 | 1 | target_reached |
| 1326470 | Sons Of The Forest | 100 | 91 | 9 | 1 | target_reached |
| 1084600 | My Time at Sandrock | 100 | 86 | 14 | 1 | target_reached |
| 666140 | My Time at Portia | 100 | 79 | 21 | 1 | target_reached |
| 632360 | Risk of Rain 2 | 100 | 91 | 9 | 1 | target_reached |
| 250900 | The Binding of Isaac: Rebirth | 100 | 84 | 16 | 1 | target_reached |
| 753640 | Outer Wilds | 100 | 93 | 7 | 1 | target_reached |
| 588650 | Dead Cells | 100 | 93 | 7 | 1 | target_reached |
| 504230 | Celeste | 100 | 92 | 8 | 1 | target_reached |
| 268910 | Cuphead | 100 | 95 | 5 | 1 | target_reached |
| 391540 | Undertale | 100 | 97 | 3 | 1 | target_reached |
| 427520 | Factorio | 100 | 99 | 1 | 1 | target_reached |
| 526870 | Satisfactory | 100 | 96 | 4 | 1 | target_reached |
| 457140 | Oxygen Not Included | 100 | 94 | 6 | 1 | target_reached |
| 255710 | Cities: Skylines | 100 | 84 | 16 | 1 | target_reached |
| 949230 | Cities: Skylines II | 100 | 69 | 31 | 1 | target_reached |
| 227300 | Euro Truck Simulator 2 | 100 | 100 | 0 | 1 | target_reached |
| 270880 | American Truck Simulator | 100 | 95 | 5 | 1 | target_reached |
| 289070 | Sid Meier's Civilization VI | 100 | 92 | 8 | 1 | target_reached |
| 8930 | Sid Meier's Civilization V | 100 | 92 | 8 | 1 | target_reached |
| 236850 | Europa Universalis IV | 100 | 69 | 31 | 1 | target_reached |
| 281990 | Stellaris | 100 | 67 | 33 | 1 | target_reached |
| 394360 | Hearts of Iron IV | 100 | 76 | 24 | 1 | target_reached |
| 1158310 | Crusader Kings III | 100 | 55 | 45 | 1 | target_reached |
| 251570 | 7 Days to Die | 100 | 75 | 25 | 1 | target_reached |
| 238960 | Path of Exile | 100 | 67 | 33 | 1 | target_reached |
| 2694490 | Path of Exile 2 | 100 | 84 | 16 | 1 | target_reached |
| 899770 | Last Epoch | 100 | 60 | 40 | 1 | target_reached |
| 2344520 | Diablo IV | 100 | 68 | 32 | 1 | target_reached |
| 582010 | Monster Hunter: World | 100 | 93 | 7 | 1 | target_reached |
| 1446780 | MONSTER HUNTER RISE | 100 | 95 | 5 | 1 | target_reached |
| 814380 | Sekiro: Shadows Die Twice | 100 | 92 | 8 | 1 | target_reached |
| 374320 | DARK SOULS III | 100 | 96 | 4 | 1 | target_reached |
| 570940 | DARK SOULS: REMASTERED | 100 | 92 | 8 | 1 | target_reached |
| 960090 | Bloons TD 6 | 100 | 96 | 4 | 1 | target_reached |
| 1244460 | Jurassic World Evolution 2 | 100 | 90 | 10 | 1 | target_reached |
| 703080 | Planet Zoo | 100 | 88 | 12 | 1 | target_reached |
| 493340 | Planet Coaster | 100 | 94 | 6 | 1 | target_reached |
| 582660 | Black Desert | 100 | 48 | 52 | 1 | target_reached |
| 306130 | The Elder Scrolls Online | 100 | 74 | 26 | 1 | target_reached |
| 39210 | FINAL FANTASY XIV Online | 100 | 79 | 21 | 1 | target_reached |
| 1284210 | Guild Wars 2 | 100 | 86 | 14 | 1 | target_reached |
| 230410 | Warframe | 100 | 89 | 11 | 1 | target_reached |
| 1085660 | Destiny 2 | 100 | 81 | 19 | 1 | target_reached |
| 1238810 | Battlefield V | 100 | 61 | 39 | 1 | target_reached |
| 1517290 | Battlefield 2042 | 100 | 64 | 36 | 1 | target_reached |
| 1238840 | Battlefield 1 | 100 | 85 | 15 | 1 | target_reached |
| 218620 | PAYDAY 2 | 100 | 89 | 11 | 1 | target_reached |
| 1272080 | PAYDAY 3 | 100 | 84 | 16 | 1 | target_reached |
| 447040 | Watch Dogs 2 | 100 | 82 | 18 | 1 | target_reached |
| 460930 | Tom Clancy's Ghost Recon Wildlands | 100 | 83 | 17 | 1 | target_reached |
| 812140 | Assassin's Creed Odyssey | 100 | 92 | 8 | 1 | target_reached |
| 2208920 | Assassin's Creed Valhalla | 100 | 66 | 34 | 1 | target_reached |
| 2050650 | Resident Evil 4 | 100 | 98 | 2 | 1 | target_reached |
| 883710 | Resident Evil 2 | 100 | 96 | 4 | 1 | target_reached |
| 1196590 | Resident Evil Village | 100 | 92 | 8 | 1 | target_reached |
| 1150690 | OMORI | 100 | 95 | 5 | 1 | target_reached |
| 413410 | Danganronpa: Trigger Happy Havoc | 100 | 95 | 5 | 1 | target_reached |
| 620980 | Beat Saber | 100 | 92 | 8 | 1 | target_reached |
| 284160 | BeamNG.drive | 100 | 96 | 4 | 1 | target_reached |

## Metadata audit

- Public Steam store appdetails check: **incomplete**.
- Verified game app types: **98 / 100**.
- Official app IDs, titles, types, request times and source URLs are saved in steam_metadata_audit.json.
- The review file keeps the configured human-readable game labels; the audit retains official titles separately (including trademark punctuation).
- This verifies the selected IDs are games; it is not a full genre/category audit or historical metadata snapshot.

## Reviewer overlap and positive graph

Positive graph: undirected bipartite graph with one edge per distinct user-game pair whose positive_interaction is true. Negative reviews are retained in the data but create no positive edges. Only nodes incident to positive edges are counted.

- Reviewers of at least two games (either feedback label): **200 / 9718**.
- Positive users / items / unique edges: **8423 / 100 / 8659**.
- Users with at least two distinct positive games: **169 / 8423**.
- Users with at least three distinct positive games: **37 / 8423**.
- Users with at least five / ten distinct positive games: **5 / 1**.
- Positive connected components: **13**.
- Largest component (by total nodes): **7501 users, 88 games, 7737 edges**.
- Largest component shares: **89.04% of positive nodes**, **89.35% of positive edges**.

| Distinct positive games per user | Users |
| --- | ---: |
| 1 | 8254 |
| 2 | 132 |
| 3 | 21 |
| 4 | 11 |
| 5 | 2 |
| 6 | 1 |
| 8 | 1 |
| 10 | 1 |

## Comparison with baseline snapshot

These are separate time-dependent convenience snapshots, not a random-sample comparison. The original files were not modified.

| Check | Baseline snapshot | Current snapshot |
| --- | ---: | ---: |
| Reviews | 2000 | 10000 |
| Games | 20 | 100 |
| Reviewers | 1972 | 9718 |
| Multi-game reviewers | 25 | 200 |
| Users with >=2 positive games | 24 | 169 |
| Users with >=3 positive games | 2 | 37 |

## Evaluation implications and handoff

- History counts are upper bounds only. Member 2 owns global chronological cutoffs, warm-user/item eligibility and the final evaluator; this report does not invent a competing split.
- Two positive games can potentially support a user's historical interaction plus one held-out target. Three can potentially support history plus separate validation and test targets for that same user; the global protocol does not require every evaluated user to occur in both windows.
- Having a large connected component does not imply that users have long histories: a few cross-game reviewers can connect many item-centered stars.
- The full catalog has 100 games; Recall@20 is no longer automatically trivial. Still report actual candidate counts after historical item and seen-item filtering; some users can have small candidate sets.
- Keep both feedback labels for opinion mining. A negative recommendation is not an aspect sentiment label. Unobserved items are not verified negative labels.
- Review creation timestamps do not certify historical text contents. For new snapshots, use timestamp_updated to conservatively exclude collected text whose last update is at/after a prediction cutoff; treat missing update timestamps explicitly. Overall feedback can also change on edit, so interaction labels need the same audit. This cannot reconstruct earlier text or labels.
- Share the versioned JSONL and manifest with Member 2, and these graph diagnostics with Member 3. Member 4 can use this pilot to develop annotation guidelines; ranking features must later respect the agreed historical split.
- The limited metadata check above establishes only the fields it records; do not claim a full metadata audit.
- Ask the lead to confirm the Steam/Amazon decision. Do not collect beyond this bound or silently mix sources.

## Limitations

- Bounded convenience sample, not representative of Steam or all game players.
- Recent English reviews only; manually selected games; off-topic filtering enabled.
- No complete purchase/exposure histories; unobserved games are not verified dislikes.
- Steam voted_up is overall binary recommendation feedback, not aspect sentiment.
- SHA-256 reviewer identifiers are pseudonymous, not anonymous.
- Review text can be edited after creation: timestamp is creation time, not proof that the collected text existed then. Strict historical text evaluation needs an edit-time policy or historical snapshots.
- API responses may be cached; collection settings do not reproduce an immutable server snapshot.
- App names are manually configured labels, not a complete metadata audit.
