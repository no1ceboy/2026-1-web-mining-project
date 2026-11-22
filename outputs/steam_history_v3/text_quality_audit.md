# Steam history v3: cleaning and text-quality audit

This audit reports structural and text signals without modifying or removing any source row. Text-pattern counts are screening flags, not proof of spam or inauthentic reviews.

| Check | Value |
| --- | ---: |
| Cohort review rows | 554 |
| Unique review IDs | 554 |
| Unique users / games | 54 / 95 |
| Positive / negative feedback | 509 / 45 |
| Blank text | 0 |
| Text under 20 tokens | 382 |
| Median / 90th-percentile token count | 9.0 / 80 |
| Training-time opinion candidates | 85 |
| Repeated user-game pairs | 0 |
| Conflicting feedback pairs | 0 |
| Source/normalized feedback disagreements | 0 |
| Repeated normalized-text groups / excess rows | 10 / 43 |
| Largest repeated-text group | 14 rows |
| Rows with 'Originally posted by author' marker | 10 |
| Rows with Introduction/Conclusion heading | 11 |
| Rows matching promotional-language signals | 4 |

Detected-language counts: `{"english": 169, "fr": 1, "unknown": 384}`.

## Interpretation

- Repeated review IDs or feedback mismatches are structural errors; this snapshot has none if the corresponding counts are zero.
- Repeated user-game pairs should be inspected before graph construction. Repeated text alone is not a duplicate rule: different users can independently post the same short phrase.
- Short and blank reviews remain valid interaction evidence. They should be omitted from opinion extraction where the registered text-quality rule requires it, not deleted from the graph history.
- Templated-language signals identify records for human source/content review; do not automatically delete or call them fake.
- The separate 20-row public-source/date/content spot-check remains necessary before historical text availability or opinion validity is claimed.
