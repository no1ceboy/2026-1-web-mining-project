"""Build training-only aspect profiles and the opinion compatibility score O(u,i).

Definition (draft v0, see outputs/opinion_feature_spec_v0.md):

  item opinion   s[i,a] = (pos - neg) / (pos + neg + neu + k)          in (-1, 1)
                 counted once per review; `mixed` adds 0.5 to pos and neg.
  user salience  w[u,a] = (n[u,a] + beta * p[a]) / (sum_a n[u,a] + beta)
                 n[u,a] = user's reviews mentioning aspect a (any sentiment),
                 p[a]   = share of all aspect mentions that are aspect a.
  compatibility  O_raw(u,i) = sum_a w[u,a] * s[i,a]                       in (-1, 1)
                 O(u,i)     = (O_raw + 1) / 2                             in (0, 1)

Only reviews whose text was available strictly before the cutoff
(`available_after_utc < cutoff`) enter profiles, and target reviews are always
excluded. `overall` labels are ignored. Pairs where either profile is missing
get O = null and the flags tell the fusion code to fall back to LightGCN.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
from collections import Counter, defaultdict
from pathlib import Path

from opinion_common import ROOT, aspect_names, load_lexicon, read_jsonl, write_json
from opinion_evaluate import merge_sentiments

SPLIT = ROOT / "outputs/steam_history_v3"


def epoch(iso):
    return int(dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp())


def available_review_ids(reviews, cutoff, excluded):
    ok = set()
    for r in reviews:
        when = r.get("available_after_utc")
        if when is None:
            continue  # unknown availability is not admissible for a historical profile
        if when < cutoff and str(r["review_id"]) not in excluded:
            ok.add(str(r["review_id"]))
    return ok


def review_aspects(records, allowed_ids, aspects):
    """review_id -> (user_id, item_id, {aspect: [sentiments]})."""
    out = {}
    for rec in records:
        rid = str(rec["review_id"])
        if rid not in allowed_ids or rec["aspect"] not in aspects:
            continue
        entry = out.setdefault(rid, (rec["user_id"], str(rec["item_id"]), defaultdict(list)))
        entry[2][rec["aspect"]].append(rec["sentiment"])
    return out


def build_profiles(per_review, aspects, k, beta):
    item_counts = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0, 0.0]))  # pos, neg, neu
    user_mentions = defaultdict(Counter)
    for user_id, item_id, labelled in per_review.values():
        for aspect, sentiments in labelled.items():
            s = merge_sentiments(sentiments)
            counts = item_counts[item_id][aspect]
            if s == "mixed":
                counts[0] += 0.5
                counts[1] += 0.5
            else:
                counts[{"positive": 0, "negative": 1, "neutral": 2}[s]] += 1
            user_mentions[user_id][aspect] += 1

    item_profiles = {i: {a: round((c[0] - c[1]) / (sum(c) + k), 6) for a, c in by_aspect.items()}
                     for i, by_aspect in item_counts.items()}
    totals = Counter()
    for mentions in user_mentions.values():
        totals.update(mentions)
    grand = sum(totals.values())
    prior = {a: (totals[a] / grand if grand else 1 / len(aspects)) for a in aspects}
    user_profiles = {}
    for user_id, mentions in user_mentions.items():
        denom = sum(mentions.values()) + beta
        user_profiles[user_id] = {a: round((mentions[a] + beta * prior[a]) / denom, 6) for a in aspects}
    return item_profiles, user_profiles, prior, item_counts


def score(user_profile, item_profile):
    if user_profile is None or item_profile is None:
        return None
    return sum(w * item_profile.get(a, 0.0) for a, w in user_profile.items())


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--split", choices=["validation", "test"], required=True)
    parser.add_argument("--reviews", default=str(SPLIT / "opinion_train_candidates.jsonl"),
                        help="opinion-eligible review texts with available_after_utc")
    parser.add_argument("--extraction", required=True, help="extractor output run on --reviews")
    parser.add_argument("--catalogue-reviews", default=str(SPLIT / "cohort_reviews.jsonl"),
                        help="used only to list catalogue item ids observed in the cohort")
    parser.add_argument("--out-dir", default=str(ROOT / "outputs/opinion_profiles_v0"))
    parser.add_argument("--k", type=float, default=2.0, help="item shrinkage toward 0")
    parser.add_argument("--beta", type=float, default=1.0, help="user prior strength")
    args = parser.parse_args()

    manifest = read_json(SPLIT / "split_manifest.json")
    cutoff_iso = manifest["settings"][f"{args.split}_cutoff_utc"]
    cutoff = epoch(cutoff_iso)
    targets = read_jsonl(SPLIT / f"{args.split}_targets.jsonl")
    seen = {r["user_id"]: set(r["item_ids"]) for r in read_jsonl(SPLIT / f"seen_items_before_{args.split}.jsonl")}
    excluded = {str(t["review_id"]) for name in ("validation", "test")
                for t in read_jsonl(SPLIT / f"{name}_targets.jsonl")}

    aspects = aspect_names(load_lexicon())
    reviews = read_jsonl(args.reviews)
    allowed = available_review_ids(reviews, cutoff, excluded)
    per_review = review_aspects(read_jsonl(args.extraction), allowed, aspects)
    item_profiles, user_profiles, prior, item_counts = build_profiles(per_review, aspects, args.k, args.beta)

    items = sorted({str(r["item_id"]) for r in read_jsonl(args.catalogue_reviews)})
    users = sorted({t["user_id"] for t in targets})
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    scores_path = out_dir / f"opinion_scores_{args.split}.csv"
    scored = 0
    with open(scores_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["user_id", "item_id", "O_raw", "O", "has_user_profile", "has_item_profile", "seen_before_cutoff"])
        for user_id in users:
            for item_id in items:
                raw = score(user_profiles.get(user_id), item_profiles.get(item_id))
                scored += raw is not None
                writer.writerow([user_id, item_id, "" if raw is None else round(raw, 6),
                                 "" if raw is None else round((raw + 1) / 2, 6),
                                 int(user_id in user_profiles), int(item_id in item_profiles),
                                 int(item_id in seen.get(user_id, set()))])

    write_json(out_dir / f"opinion_profiles_{args.split}.json", {
        "split": args.split, "cutoff_utc": cutoff_iso, "definition": "see module docstring / opinion_feature_spec_v0.md",
        "parameters": {"k": args.k, "beta": args.beta}, "aspects": aspects,
        "input_reviews": len(reviews), "reviews_available_before_cutoff": len(allowed),
        "reviews_with_extracted_aspects": len(per_review),
        "extraction_run_id": next((r.get("run_id") for r in read_jsonl(args.extraction)), None),
        "aspect_prior": {a: round(p, 6) for a, p in prior.items()},
        "item_profiles": item_profiles,
        "item_profile_support": {i: {a: c for a, c in by.items()} for i, by in item_counts.items()},
        "user_profiles": user_profiles,
    })
    coverage = {
        "split": args.split, "cutoff_utc": cutoff_iso,
        "target_users": len(users), "target_users_with_profile": sum(u in user_profiles for u in users),
        "catalogue_items_observed": len(items), "items_with_profile": sum(i in item_profiles for i in items),
        "targets_whose_item_has_profile": sum(str(t["item_id"]) in item_profiles for t in targets),
        "user_item_pairs": len(users) * len(items), "pairs_with_score": scored,
        "status": "pilot coverage; extractor not yet validated against human labels",
    }
    write_json(out_dir / f"opinion_coverage_{args.split}.json", coverage)
    print(coverage)


def read_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


if __name__ == "__main__":
    main()
