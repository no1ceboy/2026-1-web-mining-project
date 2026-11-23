"""Validate human ABSA labels, measure annotator agreement, and score an extractor.

Unit of evaluation: a (review_id, aspect) pair, as in SemEval-2014 aspect
category detection. Several rows for the same aspect in one review are merged:
positive+negative (or an explicit `mixed`) becomes `mixed`; a polar label plus
`neutral` keeps the polar label. `overall` is scored separately and excluded
from aspect P/R/F1; `none` only marks a review as annotated.

Gold labels per review: the `adjudicated` annotator if present, otherwise the
only annotator; reviews with several annotators and no adjudication are
reported as pending and excluded from extractor scoring.

voted_up is joined from the source JSONL only for the descriptive
criticized-aspect counts; it is never used as an aspect label.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from itertools import combinations

from opinion_common import (ADJUDICATED_ID, ROOT, aspect_names, load_lexicon, read_annotations,
                            read_jsonl, tokens, validate_annotations, write_json)

NEGATIVE_LIKE = {"negative", "mixed"}


def merge_sentiments(values):
    values = set(values)
    if "mixed" in values or {"positive", "negative"} <= values:
        return "mixed"
    polar = values - {"neutral"}
    return polar.pop() if polar else "neutral"


def label_sets(rows):
    """annotator -> review -> {aspect: merged sentiment}; reviews with only `none` map to {}."""
    raw = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    evidence = defaultdict(list)
    for row in rows:
        review = raw[row["annotator_id"]][row["review_id"]]
        if row["aspect"] == "none":
            continue
        review[row["aspect"]].append(row["sentiment"])
        evidence[(row["annotator_id"], row["review_id"], row["aspect"])].append(row["evidence"])
    labels = {a: {r: {asp: merge_sentiments(s) for asp, s in aspects.items()}
                  for r, aspects in reviews.items()} for a, reviews in raw.items()}
    return labels, evidence


def gold_labels(labels):
    by_review = defaultdict(dict)
    for annotator, reviews in labels.items():
        for review_id, aspects in reviews.items():
            by_review[review_id][annotator] = aspects
    gold, source, pending = {}, {}, []
    for review_id, annotators in by_review.items():
        if ADJUDICATED_ID in annotators:
            gold[review_id], source[review_id] = annotators[ADJUDICATED_ID], ADJUDICATED_ID
        elif len(annotators) == 1:
            (annotator, aspects), = annotators.items()
            gold[review_id], source[review_id] = aspects, annotator
        else:
            pending.append(review_id)
    return gold, source, sorted(pending)


def prf(tp, fp, fn):
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = None
    if precision is not None and recall is not None:
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": rnd(precision), "recall": rnd(recall), "f1": rnd(f1)}


def rnd(value):
    return None if value is None else round(value, 4)


def pairs(labels_by_review, review_ids, aspects):
    return {(r, a): s for r in review_ids for a, s in labels_by_review.get(r, {}).items() if a in aspects}


def compare(reference, predicted, aspects, review_ids):
    ref, pred = pairs(reference, review_ids, aspects), pairs(predicted, review_ids, aspects)
    matched = ref.keys() & pred.keys()
    result = {"micro": prf(len(matched), len(pred.keys() - ref.keys()), len(ref.keys() - pred.keys()))}
    result["per_aspect"] = {}
    for aspect in aspects:
        r = {k for k in ref if k[1] == aspect}
        p = {k for k in pred if k[1] == aspect}
        result["per_aspect"][aspect] = {**prf(len(r & p), len(p - r), len(r - p)), "gold_support": len(r)}
    agree = sum(ref[k] == pred[k] for k in matched)
    result["sentiment_on_matched"] = {
        "matched_pairs": len(matched), "correct": agree,
        "accuracy": rnd(agree / len(matched)) if matched else None,
        "macro_f1": macro_f1([(ref[k], pred[k]) for k in matched]),
        "confusion": dict(Counter(f"{ref[k]}->{pred[k]}" for k in matched)),
    }
    return result, ref, pred, matched


def macro_f1(gold_pred):
    if not gold_pred:
        return None
    classes = sorted({g for g, _ in gold_pred} | {p for _, p in gold_pred})
    scores = []
    for c in classes:
        tp = sum(g == c and p == c for g, p in gold_pred)
        fp = sum(g != c and p == c for g, p in gold_pred)
        fn = sum(g == c and p != c for g, p in gold_pred)
        scores.append(prf(tp, fp, fn)["f1"] or 0.0)
    return rnd(sum(scores) / len(scores))


def cohen_kappa(a_labels, b_labels, review_ids, aspects):
    """Kappa on binary aspect presence over every review x aspect cell."""
    cells = [(int(asp in a_labels.get(r, {})), int(asp in b_labels.get(r, {})))
             for r in review_ids for asp in aspects]
    if not cells:
        return None
    n = len(cells)
    observed = sum(x == y for x, y in cells) / n
    pa, pb = sum(x for x, _ in cells) / n, sum(y for _, y in cells) / n
    expected = pa * pb + (1 - pa) * (1 - pb)
    return rnd((observed - expected) / (1 - expected)) if expected < 1 else None


def token_f1(a, b):
    ta, tb = Counter(tokens(a)), Counter(tokens(b))
    common = sum((ta & tb).values())
    if not common:
        return 0.0
    precision, recall = common / sum(tb.values()), common / sum(ta.values())
    return 2 * precision * recall / (precision + recall)


def agreement(labels, aspects, writer):
    annotators = sorted(a for a in labels if a != ADJUDICATED_ID)
    report = []
    for a, b in combinations(annotators, 2):
        shared = sorted(labels[a].keys() & labels[b].keys())
        if not shared:
            continue
        result, ref, pred, matched = compare(labels[a], labels[b], aspects, shared)
        report.append({"annotators": [a, b], "shared_reviews": len(shared),
                       "aspect_pair_f1": result["micro"]["f1"],
                       "aspect_presence_kappa": cohen_kappa(labels[a], labels[b], shared, aspects),
                       "sentiment_agreement_on_shared_pairs": result["sentiment_on_matched"]})
        for key in sorted(ref.keys() | pred.keys()):
            if ref.get(key) != pred.get(key):
                writer.writerow([key[0], key[1], a, ref.get(key, "(absent)"), b, pred.get(key, "(absent)")])
    return report


def criticized(labels_by_review, review_ids, voted_up, aspects):
    negative_reviews = [r for r in review_ids if voted_up.get(r) is False]
    counts = Counter(a for r in negative_reviews for a, s in labels_by_review.get(r, {}).items()
                     if a in aspects and s in NEGATIVE_LIKE)
    return {"voted_up_false_reviews": len(negative_reviews),
            "reviews_criticizing_aspect": dict(counts.most_common())}


def extractor_labels(records):
    merged = defaultdict(lambda: defaultdict(list))
    evidence = defaultdict(list)
    for rec in records:
        merged[rec["review_id"]][rec["aspect"]].append(rec["sentiment"])
        evidence[(rec["review_id"], rec["aspect"])].append(rec["evidence"])
    return {r: {a: merge_sentiments(s) for a, s in aspects.items()} for r, aspects in merged.items()}, evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", default=str(ROOT / "outputs/steam_pilot.jsonl"))
    parser.add_argument("--annotations", default=str(ROOT / "outputs/aspect_annotations_v0.csv"))
    parser.add_argument("--extraction", default=str(ROOT / "outputs/opinion_extraction_v0.jsonl"))
    parser.add_argument("--eval-ids", help="optional file of review_ids (held-out split) to score on")
    parser.add_argument("--metrics", default=str(ROOT / "outputs/opinion_validation_v0_metrics.json"))
    parser.add_argument("--disagreements", default=str(ROOT / "outputs/annotation_disagreements_v0.csv"))
    args = parser.parse_args()

    lexicon = load_lexicon()
    aspects = aspect_names(lexicon)
    source = {str(r["review_id"]): r for r in read_jsonl(args.source)}
    texts = {k: r.get("text") or "" for k, r in source.items()}
    voted_up = {k: bool(r.get("positive_interaction")) for k, r in source.items()}

    rows = read_annotations(args.annotations)
    problems = validate_annotations(rows, texts, lexicon)
    if problems:
        print("Annotation file has problems; fix them before scoring:")
        print("\n".join(f"  - {p}" for p in problems))
        raise SystemExit(1)

    labels, gold_evidence = label_sets(rows)
    with open(args.disagreements, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["review_id", "aspect", "annotator_a", "label_a", "annotator_b", "label_b"])
        agreement_report = agreement(labels, aspects, writer)

    gold, gold_source, pending = gold_labels(labels)
    eval_ids = sorted(gold)
    if args.eval_ids:
        wanted = {line.strip() for line in open(args.eval_ids, encoding="utf-8") if line.strip()}
        eval_ids = [r for r in eval_ids if r in wanted]

    metrics = {
        "annotations_file": args.annotations, "annotation_rows": len(rows),
        "annotators": sorted(labels), "gold_reviews": len(gold), "pending_adjudication": pending,
        "gold_source_counts": dict(Counter(gold_source.values())),
        "eval_reviews": len(eval_ids), "aspects": aspects,
        "agreement": agreement_report,
        "gold_criticized_aspects": criticized(gold, eval_ids, voted_up, aspects),
    }

    try:
        records = read_jsonl(args.extraction)
    except FileNotFoundError:
        records = []
    if records and eval_ids:
        predicted, pred_evidence = extractor_labels(records)
        result, ref, pred, matched = compare(gold, predicted, aspects, eval_ids)
        overall, *_ = compare(gold, predicted, ["overall"], eval_ids)
        spans = [max(token_f1(g, p) for g in gold_evidence[(gold_source[r], r, a)] for p in pred_evidence[(r, a)])
                 for r, a in matched]
        exact = sum(rec["evidence"] in texts.get(rec["review_id"], "") for rec in records
                    if rec["review_id"] in set(eval_ids))
        scored = sum(rec["review_id"] in set(eval_ids) for rec in records)
        metrics["extractor"] = {
            "run_id": records[0].get("run_id"), "model": records[0].get("model"),
            "model_version": records[0].get("model_version"),
            "aspect_detection": result, "overall_label": overall["micro"],
            "evidence": {"matched_pairs": len(spans),
                         "mean_best_token_f1_vs_gold_span": rnd(sum(spans) / len(spans)) if spans else None,
                         "predicted_spans_exact_substring": exact, "predicted_spans_scored": scored},
            "criticized_aspects_unvalidated": criticized(predicted, eval_ids, voted_up, aspects),
            "false_positive_examples": examples(pred.keys() - ref.keys(), pred_evidence),
            "false_negative_examples": examples(ref.keys() - pred.keys(),
                                                {(r, a): gold_evidence[(gold_source[r], r, a)] for r, a in ref}),
        }
    write_json(args.metrics, metrics)
    print(json.dumps({k: metrics[k] for k in ("annotation_rows", "gold_reviews", "eval_reviews")}, indent=2))
    if "extractor" in metrics:
        print("aspect micro:", metrics["extractor"]["aspect_detection"]["micro"])
        print("sentiment on matched:", {k: v for k, v in metrics["extractor"]["aspect_detection"]
                                        ["sentiment_on_matched"].items() if k != "confusion"})
    print(f"metrics -> {args.metrics}; disagreements -> {args.disagreements}")


def examples(keys, evidence, limit=15):
    return [{"review_id": r, "aspect": a, "evidence": evidence[(r, a)][0][:200]}
            for r, a in sorted(keys)[:limit]]


if __name__ == "__main__":
    main()
