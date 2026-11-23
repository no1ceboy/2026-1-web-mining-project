# Graph coverage

Dataset version **steam_history_v3**. Split manifest SHA-256 `5b29cc87a838ded2f336a4f538e1ad0d4c1bd9caae196534a9bf30cd83393b77`.
Planning gate passed **False**.

| History | Reviews | Observed users | Observed games | Positive users | Positive games | Positive edges | Users with ≥2 positive games | Components | Largest component users | Largest component games | Largest component edges | Eligible target users |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Original Steam pilot (reference) | 200 | 199 | 5 | 120 | 5 | 121 | 1 | 4 | 40 | 1 | 40 | — |
| Validation | 354 | 54 | 85 | 54 | 84 | 334 | 54 | 1 | 54 | 84 | 334 | 22 |
| Test | 494 | 54 | 91 | 54 | 90 | 458 | 54 | 1 | 54 | 90 | 458 | 23 |

An edge is a distinct positive user–game pair. Components contain incident nodes only.
Validation uses train history. Test refits on history available before the test cutoff.
The original 200-review snapshot is included as a separate coverage reference.
