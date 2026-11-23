"""Select a deterministic, stratified annotation batch for manual ABSA labels.

The worksheet deliberately omits `voted_up` so annotators label aspect
sentiment from the text alone instead of copying the overall recommendation.
Evaluation re-joins `voted_up` from the source JSONL by review_id.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
from collections import defaultdict

from opinion_common import ROOT, english_score, read_jsonl, tokens, write_json


def rank_key(seed, review_id):
    return hashlib.sha256(f"{seed}:{review_id}".encode()).hexdigest()


def select(rows, per_item, max_negative, overlap_per_item, seed, min_tokens, min_english):
    excluded = defaultdict(int)
    by_item = defaultdict(lambda: {True: [], False: []})
    for row in rows:
        text = row.get("text") or ""
        if len(tokens(text)) < min_tokens:
            excluded["too_short"] += 1
            continue
        if english_score(text) < min_english:
            excluded["likely_not_english"] += 1
            continue
        by_item[row["item_id"]][bool(row["positive_interaction"])].append(row)

    chosen = []
    for item_id in sorted(by_item):
        pools = {label: sorted(rs, key=lambda r: rank_key(seed, r["review_id"]))
                 for label, rs in by_item[item_id].items()}
        negatives = pools[False][:max_negative]
        positives = pools[True][:per_item - len(negatives)]
        picked = negatives + positives
        if len(picked) < per_item:  # top up with extra negatives if positives ran out
            picked += pools[False][max_negative:max_negative + per_item - len(picked)]
        picked.sort(key=lambda r: rank_key(seed + ":overlap", r["review_id"]))
        for position, row in enumerate(picked):
            chosen.append((row, position < overlap_per_item))
    chosen.sort(key=lambda pair: rank_key(seed + ":order", pair[0]["review_id"]))
    return chosen, dict(excluded)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=str(ROOT / "outputs/steam_pilot.jsonl"))
    parser.add_argument("--worksheet", default=str(ROOT / "outputs/annotation_batch_v0.csv"))
    parser.add_argument("--manifest", default=str(ROOT / "outputs/annotation_batch_v0_manifest.json"))
    parser.add_argument("--per-item", type=int, default=10)
    parser.add_argument("--max-negative", type=int, default=5)
    parser.add_argument("--overlap-per-item", type=int, default=3)
    parser.add_argument("--min-tokens", type=int, default=5)
    parser.add_argument("--min-english", type=float, default=0.15)
    parser.add_argument("--seed", default="member4-annotation-v0")
    args = parser.parse_args()

    rows = read_jsonl(args.input)
    chosen, excluded = select(rows, args.per_item, args.max_negative, args.overlap_per_item,
                              args.seed, args.min_tokens, args.min_english)
    with open(args.worksheet, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["batch_order", "review_id", "item_id", "item_title", "overlap", "text"])
        for order, (row, overlap) in enumerate(chosen, start=1):
            writer.writerow([order, row["review_id"], row["item_id"], row.get("item_title", ""),
                             "yes" if overlap else "no", row.get("text", "")])

    per_item = defaultdict(lambda: {"reviews": 0, "voted_up_false": 0, "overlap": 0})
    for row, overlap in chosen:
        stats = per_item[row["item_id"]]
        stats["reviews"] += 1
        stats["voted_up_false"] += not row["positive_interaction"]
        stats["overlap"] += overlap
    write_json(args.manifest, {
        "batch": "annotation_batch_v0",
        "source": str(args.input).replace(str(ROOT), "").lstrip("\\/").replace("\\", "/"),
        "purpose": "development batch for taxonomy and annotation guide; not a held-out evaluation set",
        "selection": {"per_item": args.per_item, "max_negative_per_item": args.max_negative,
                      "overlap_per_item": args.overlap_per_item, "min_tokens": args.min_tokens,
                      "min_english_function_word_share": args.min_english, "seed": args.seed,
                      "ordering": "sha256(seed:review_id)"},
        "blinding": "voted_up is omitted from the worksheet; evaluation joins it from the source by review_id",
        "source_reviews": len(rows),
        "excluded_before_sampling": excluded,
        "selected_reviews": len(chosen),
        "selected_voted_up_false": sum(not r["positive_interaction"] for r, _ in chosen),
        "overlap_reviews": sum(o for _, o in chosen),
        "per_item": dict(sorted(per_item.items())),
    })
    print(f"wrote {len(chosen)} reviews to {args.worksheet}; excluded {excluded}")


if __name__ == "__main__":
    main()
