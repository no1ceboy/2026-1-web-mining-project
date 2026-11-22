"""Audit cohort interaction and review-text quality without altering source rows."""

from __future__ import annotations

from collections import Counter, defaultdict
import json
from math import ceil
from pathlib import Path
import re
import statistics

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "outputs/steam_history_v3"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def build_audit(data_dir: Path = DATA_DIR) -> dict:
    cohort = read_jsonl(data_dir / "cohort_reviews.jsonl")
    quality = read_jsonl(data_dir / "review_quality.jsonl")
    opinion_candidates = read_jsonl(data_dir / "opinion_train_candidates.jsonl")
    review_ids = [row["review_id"] for row in cohort]
    quality_ids = [row["review_id"] for row in quality]
    if len(set(review_ids)) != len(review_ids):
        raise ValueError("Duplicate review_id in cohort_reviews.jsonl")
    if len(set(quality_ids)) != len(quality_ids):
        raise ValueError("Duplicate review_id in review_quality.jsonl")

    quality_by_id = {row["review_id"]: row for row in quality}
    if set(review_ids) != set(quality_by_id):
        raise ValueError("review_quality.jsonl does not cover exactly the cohort review IDs")
    cohort_id_set = set(review_ids)
    opinion_ids = [row["review_id"] for row in opinion_candidates]
    if len(set(opinion_ids)) != len(opinion_ids) or not set(opinion_ids) <= cohort_id_set:
        raise ValueError("Opinion candidates contain duplicate or out-of-cohort review IDs")

    by_user_item_review_ids = defaultdict(list)
    by_user_item_labels = defaultdict(set)
    feedback_disagreements = 0
    for row in cohort:
        pair = (row["user_id"], row["item_id"])
        by_user_item_review_ids[pair].append(row["review_id"])
        by_user_item_labels[pair].add(row["positive_interaction"])
        if row.get("source_feedback") is not row["positive_interaction"]:
            feedback_disagreements += 1
    repeated_user_item_pairs = sum(len(review_ids) > 1 for review_ids in by_user_item_review_ids.values())
    conflicting_user_item_pairs = sum(len(labels) > 1 for labels in by_user_item_labels.values())

    texts = [str(row.get("text") or "") for row in cohort]
    token_counts = [len(text.split()) for text in texts]
    normalized_counts = Counter(normalize_text(text) for text in texts)
    repeated_text_counts = [count for count in normalized_counts.values() if count > 1]
    quality_fields = Counter(row.get("detected_language", "missing") for row in quality)
    opinion_set = set(opinion_ids)

    checks = {
        "rows": len(cohort),
        "unique_review_ids": len(set(review_ids)),
        "unique_users": len({row["user_id"] for row in cohort}),
        "unique_items": len({row["item_id"] for row in cohort}),
        "positive_reviews": sum(row["positive_interaction"] is True for row in cohort),
        "negative_reviews": sum(row["positive_interaction"] is False for row in cohort),
        "blank_texts": sum(not text.strip() for text in texts),
        "short_texts_under_20_tokens": sum(count < 20 for count in token_counts),
        "median_tokens": statistics.median(token_counts) if token_counts else 0,
        "p90_tokens_nearest_rank": sorted(token_counts)[max(0, ceil(0.9 * len(token_counts)) - 1)] if token_counts else 0,
        "opinion_train_candidates": len(opinion_candidates),
        "quality_language_counts": dict(sorted(quality_fields.items())),
        "repeated_user_item_pairs": repeated_user_item_pairs,
        "conflicting_feedback_user_item_pairs": conflicting_user_item_pairs,
        "source_feedback_mapping_disagreements": feedback_disagreements,
        "normalized_text_groups_repeated": len(repeated_text_counts),
        "excess_rows_in_repeated_text_groups": sum(count - 1 for count in repeated_text_counts),
        "largest_normalized_text_repeat_count": max(repeated_text_counts, default=1),
        "author_quote_marker_rows": sum(bool(re.search(r"Originally posted by\s*author", text, re.I)) for text in texts),
        "intro_or_conclusion_heading_rows": sum(bool(re.search(r"(?im)^\s*(Introduction|Conclusion)\s*$", text)) for text in texts),
        "promotional_phrase_signal_rows": sum(bool(re.search(
            r"(?i)critically acclaimed|captivating narrative|immersive experience|game of the year", text
        )) for text in texts),
        "opinion_candidate_ids_in_cohort": len(opinion_set & cohort_id_set),
        "opinion_candidate_quality_flags_consistent": all(
            quality_by_id[review_id].get("opinion_text_eligible") is True
            and quality_by_id[review_id].get("available_before_validation_cutoff") is True
            for review_id in opinion_set
        ),
        "quality_rows_match_cohort_ids": set(review_ids) == set(quality_by_id),
        "feedback_mapping_clean": feedback_disagreements == 0,
    }
    return {
        "dataset_version": "steam_history_v3",
        "scope": "Descriptive quality flags only; no automatic spam or authenticity labels are assigned.",
        "checks": checks,
    }


def render_markdown(audit: dict) -> str:
    c = audit["checks"]
    return "\n".join([
        "# Steam history v3: cleaning and text-quality audit",
        "",
        "This audit reports structural and text signals without modifying or removing any source row. Text-pattern counts are screening flags, not proof of spam or inauthentic reviews.",
        "",
        "| Check | Value |",
        "| --- | ---: |",
        f"| Cohort review rows | {c['rows']} |",
        f"| Unique review IDs | {c['unique_review_ids']} |",
        f"| Unique users / games | {c['unique_users']} / {c['unique_items']} |",
        f"| Positive / negative feedback | {c['positive_reviews']} / {c['negative_reviews']} |",
        f"| Blank text | {c['blank_texts']} |",
        f"| Text under 20 tokens | {c['short_texts_under_20_tokens']} |",
        f"| Median / 90th-percentile token count | {c['median_tokens']} / {c['p90_tokens_nearest_rank']} |",
        f"| Training-time opinion candidates | {c['opinion_train_candidates']} |",
        f"| Repeated user-game pairs | {c['repeated_user_item_pairs']} |",
        f"| Conflicting feedback pairs | {c['conflicting_feedback_user_item_pairs']} |",
        f"| Source/normalized feedback disagreements | {c['source_feedback_mapping_disagreements']} |",
        f"| Repeated normalized-text groups / excess rows | {c['normalized_text_groups_repeated']} / {c['excess_rows_in_repeated_text_groups']} |",
        f"| Largest repeated-text group | {c['largest_normalized_text_repeat_count']} rows |",
        f"| Rows with 'Originally posted by author' marker | {c['author_quote_marker_rows']} |",
        f"| Rows with Introduction/Conclusion heading | {c['intro_or_conclusion_heading_rows']} |",
        f"| Rows matching promotional-language signals | {c['promotional_phrase_signal_rows']} |",
        "",
        f"Detected-language counts: `{json.dumps(c['quality_language_counts'], ensure_ascii=False, sort_keys=True)}`.",
        "",
        "## Interpretation",
        "",
        "- Repeated review IDs or feedback mismatches are structural errors; this snapshot has none if the corresponding counts are zero.",
        "- Repeated user-game pairs should be inspected before graph construction. Repeated text alone is not a duplicate rule: different users can independently post the same short phrase.",
        "- Short and blank reviews remain valid interaction evidence. They should be omitted from opinion extraction where the registered text-quality rule requires it, not deleted from the graph history.",
        "- Templated-language signals identify records for human source/content review; do not automatically delete or call them fake.",
        "- The separate 20-row public-source/date/content spot-check remains necessary before historical text availability or opinion validity is claimed.",
        "",
    ])


def main() -> None:
    audit = build_audit()
    (DATA_DIR / "text_quality_audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (DATA_DIR / "text_quality_audit.md").write_text(render_markdown(audit), encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
