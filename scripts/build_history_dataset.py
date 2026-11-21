"""Build train-defined user cohorts and audit temporal coverage, without model metrics.

Cutoffs here are a proposed sampling contract for review by the evaluation owner.
They do not silently replace an independently agreed final evaluator.
"""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

from steam_crawler import ROOT, atomic_text, read_jsonl, utc_now, write_json
from steam_history_sampler import anchor_seed_timestamps, before, epoch, event_upper, priority_users, quality, text_before, training_games


def dump_rows(path, rows):
    atomic_text(path, "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))


def validate_row(row, settings, catalogue):
    allowed = {"review_id", "user_id", "item_id", "item_title", "timestamp", "timestamp_updated",
               "timestamp_precision", "event_time_lower_utc", "available_after_utc", "text_available_after_utc",
               "edit_time_status", "crawl_time_utc", "source_feedback", "positive_interaction", "title", "text",
               "language", "helpful_votes", "source_url", "source_method"}
    if row.keys() - allowed:
        raise ValueError("Unexpected raw record fields; possible private identifier")
    if not re.fullmatch(r"[a-f0-9]{64}", row.get("user_id", "")) or not re.fullmatch(r"[0-9]+", row.get("review_id", "")):
        raise ValueError("Invalid pseudonymous user/review ID")
    if row["item_id"] not in catalogue or row.get("source_url") != "https://steamcommunity.com":
        raise ValueError("Out-of-frame item or unsafe profile source URL")
    if type(row["positive_interaction"]) is not bool or row["source_feedback"] is not row["positive_interaction"]:
        raise ValueError("Invalid feedback mapping")
    if not isinstance(row["text"], str):
        raise ValueError("Missing review text")
    for key in ["timestamp", "timestamp_updated", "event_time_lower_utc", "available_after_utc"]:
        if type(row[key]) is not int:
            raise ValueError("Invalid time bound type")
    if row["timestamp_precision"] not in {"day", "second"} or row["timestamp_updated"] < row["timestamp"]:
        raise ValueError("Invalid time precision or edit order")
    if row["available_after_utc"] < max(event_upper(row, settings), row["timestamp_updated"]):
        raise ValueError("Availability precedes its source event")


def temporal_coverage(all_rows, settings, cutoff, end):
    start = epoch(settings["observation_start_utc"])
    history = [row for row in all_rows if row["event_time_lower_utc"] >= start and
               event_upper(row, settings) < cutoff and before(row, cutoff)]
    positive_edges = {(row["user_id"], row["item_id"]) for row in history if row["positive_interaction"]}
    warm_users = {user for user, _ in positive_edges}
    warm_items = {item for _, item in positive_edges}
    seen = defaultdict(set)
    for row in all_rows:
        # An old review proves a prior reviewed item even if its current label/text
        # was edited later and cannot enter the historical positive graph.
        if event_upper(row, settings) < cutoff:
            seen[row["user_id"]].add(row["item_id"])
    targets = {}
    exclusions = Counter()
    for row in sorted(all_rows, key=lambda value: (value["timestamp"], value["review_id"])):
        if not row["positive_interaction"] or row["event_time_lower_utc"] < cutoff:
            continue
        if event_upper(row, settings) >= end:
            continue
        if row["timestamp_updated"] > row["timestamp"]:
            exclusions["target_has_visible_later_edit"] += 1
            continue
        if not before(row, end):
            exclusions["target_unavailable_by_window_end"] += 1
            continue
        user, item = row["user_id"], row["item_id"]
        if user not in warm_users:
            exclusions["cold_user"] += 1
        elif item not in warm_items:
            exclusions["cold_item"] += 1
        elif item in seen[user]:
            exclusions["previously_reviewed_item"] += 1
        elif user not in targets:
            targets[user] = {"user_id": user, "review_id": row["review_id"], "item_id": item,
                             "timestamp": row["timestamp"], "candidate_count": len(warm_items - seen[user])}
    target_rows = list(targets.values())
    return {"positive_training_edges": len(positive_edges), "warm_users": len(warm_users),
            "warm_items": len(warm_items), "eligible_target_users": len(target_rows),
            "candidate_count_min": min((row["candidate_count"] for row in target_rows), default=0),
            "candidate_count_max": max((row["candidate_count"] for row in target_rows), default=0),
            "targets_with_more_than_20_candidates": sum(row["candidate_count"] > 20 for row in target_rows),
            "target_exclusion_observations": dict(exclusions)}, history, target_rows, seen


def build(output):
    output = Path(output)
    manifest = json.loads((output / "sampling_manifest.json").read_text(encoding="utf-8"))
    settings = manifest["settings"]
    source = output / "discovered_reviews.jsonl"
    if hashlib.sha256(source.read_bytes()).hexdigest() != manifest["data_sha256"]:
        raise ValueError("Raw discovery data differs from its manifest; resume/check collection first")
    records = read_jsonl(source)
    if len({row["review_id"] for row in records}) != len(records):
        raise ValueError("Duplicate review IDs in discovery data")
    seed_manifest = json.loads((output / "seed_manifest.json").read_text(encoding="utf-8"))
    seeds = {row["user_id"]: row for row in seed_manifest["seeds"]}
    records = [anchor_seed_timestamps(row, seeds.get(row["user_id"], {}), settings) for row in records]
    by_user = defaultdict(list)
    catalogue = {str(app["app_id"]) for app in manifest["apps"]}
    for row in records:
        validate_row(row, settings, catalogue)
        by_user[row["user_id"]].append(row)
    priority = [user for user in priority_users(seeds, settings) if user in by_user]
    selected, exclusions = [], Counter()
    train_cutoff = epoch(settings["validation_cutoff_utc"])
    for user in priority:
        profile = manifest["profiles"].get(user, {})
        if profile.get("status") != "complete":
            exclusions["profile_not_complete"] += 1
            continue
        rows = by_user[user]
        if not any(row["review_id"] == seeds[user]["seed_review_id"] and row["positive_interaction"] and
                   before(row, train_cutoff) for row in rows):
            exclusions["seed_not_observed_before_cutoff"] += 1
            continue
        if len(training_games(rows, settings)) < settings["minimum_positive_training_games"]:
            exclusions["insufficient_training_positive_games"] += 1
            continue
        selected.append(user)
    # Membership and ordering depend only on training records, source completeness
    # and the fixed hash priority. Never choose users by future targets or row count.
    selected = selected[:settings["target_cohort_users"]]
    selected_set = set(selected)
    start, end = epoch(settings["observation_start_utc"]), epoch(settings["observation_end_utc"])
    all_selected = [row for row in records if row["user_id"] in selected_set]
    cohort_rows = [row.copy() for row in all_selected if row["event_time_lower_utc"] >= start and before(row, end)]
    quality_rows, opinion_rows = [], []
    for row in cohort_rows:
        text_quality = quality(row, settings)
        row["language"] = text_quality["detected_language"]
        text_quality["available_before_validation_cutoff"] = text_before(row, train_cutoff)
        quality_rows.append(text_quality)
        if text_quality["opinion_text_eligible"] and text_before(row, train_cutoff):
            opinion_rows.append(row)
    validation, train_rows, val_targets, val_seen = temporal_coverage(all_selected, settings, train_cutoff, epoch(settings["test_cutoff_utc"]))
    testing, refit_rows, test_targets, test_seen = temporal_coverage(all_selected, settings, epoch(settings["test_cutoff_utc"]), end)
    dump_rows(output / "cohort_reviews.jsonl", cohort_rows)
    dump_rows(output / "review_quality.jsonl", quality_rows)
    dump_rows(output / "opinion_train_candidates.jsonl", opinion_rows)
    dump_rows(output / "train_reviews.jsonl", train_rows)
    dump_rows(output / "refit_reviews.jsonl", refit_rows)
    dump_rows(output / "validation_targets.jsonl", val_targets)
    dump_rows(output / "test_targets.jsonl", test_targets)
    dump_rows(output / "seen_items_before_validation.jsonl", [{"user_id": user, "item_ids": sorted(items)} for user, items in sorted(val_seen.items())])
    dump_rows(output / "seen_items_before_test.jsonl", [{"user_id": user, "item_ids": sorted(items)} for user, items in sorted(test_seen.items())])
    raw_positive_histories = Counter()
    for rows in by_user.values():
        raw_positive_histories[len({row["item_id"] for row in rows if row["positive_interaction"]})] += 1
    complete_users = {user for user, profile in manifest["profiles"].items() if profile["status"] == "complete"}
    baseline = read_jsonl(ROOT / settings["baseline_reviews"])
    old_by_user = defaultdict(set)
    new_by_user = defaultdict(set)
    for row in baseline:
        if row["user_id"] in complete_users and row["positive_interaction"]:
            old_by_user[row["user_id"]].add(row["item_id"])
    for row in records:
        if row["user_id"] in complete_users and row["positive_interaction"]:
            new_by_user[row["user_id"]].add(row["item_id"])
    matched = set(old_by_user) & set(new_by_user)
    minimum_users = settings.get("minimum_cohort_users_for_evaluation", settings["target_cohort_users"])
    ready = (len(selected) >= minimum_users and
             validation["eligible_target_users"] >= settings["minimum_validation_users"] and
             testing["eligible_target_users"] >= settings["minimum_test_users"] and
             validation["targets_with_more_than_20_candidates"] >= settings["minimum_validation_users"] and
             testing["targets_with_more_than_20_candidates"] >= settings["minimum_test_users"])
    stats = {"generated_at_utc": utc_now(), "dataset_version": settings["dataset_version"],
             "collection_status": manifest["status"], "seed_users": len(seeds),
             "profiles_attempted": len(manifest["profiles"]),
             "profile_status_counts": dict(Counter(profile["status"] for profile in manifest["profiles"].values())),
             "discovered_reviews": len(records), "discovered_users_with_in_catalog_reviews": len(by_user),
             "unfiltered_discovered_positive_history_distribution": dict(sorted(raw_positive_histories.items())),
             "selected_users": len(selected), "selected_reviews": len(cohort_rows),
             "collection_user_target": settings["target_cohort_users"],
             "minimum_evaluation_cohort_users": minimum_users,
             "collection_targets_reached": (len(selected) >= settings["target_cohort_users"] and len(cohort_rows) >= settings["target_cohort_reviews"]),
             "selected_games_observed": len({row["item_id"] for row in cohort_rows}),
             "catalogue_games": len(manifest["apps"]),
             "cohort_exclusion_counts": dict(exclusions),
             "positive_reviews": sum(row["positive_interaction"] for row in cohort_rows),
             "negative_reviews": sum(not row["positive_interaction"] for row in cohort_rows),
             "blank_cohort_texts": sum(row["blank"] for row in quality_rows),
             "short_cohort_texts": sum(row["short"] for row in quality_rows),
             "opinion_train_candidates": len(opinion_rows), "validation": validation, "test": testing,
             "matched_old_new_positive_users": len(matched),
             "old_positive_edges_matched_users": sum(len(old_by_user[user]) for user in matched),
             "new_positive_edges_matched_users": sum(len(new_by_user[user]) for user in matched),
             "planning_gate_passed": ready,
             "planning_gate_note": f"{minimum_users} training-defined users and {settings['minimum_validation_users']}/{settings['minimum_test_users']} eligible users in validation/test with >20 candidates are declared project planning targets, not universal statistical requirements. No ranking metrics were computed.",
             "review_count_target_is_soft": True,
             "review_count_note": "Never truncate individual rows or select users using future review counts to hit exactly 10,000. Membership uses training history only; the final count may differ.",
             "raw_data_sha256": manifest["data_sha256"]}
    write_json(output / "sampling_audit.json", stats)
    write_json(output / "split_manifest.json", {"status": "proposed_sampling_contract_requires_evaluation_owner_review",
               "settings": settings, "cohort_user_ids": selected, "validation": validation, "test": testing,
               "date_policy": "Matching seed interactions can use their exact API creation/update times. Other public page dates are day precision: require date-14h >= interval start and date+38h < interval end. Public text availability always keeps its conservative latest-edit-date+38h bound, including API-anchored seeds. Exclude targets with a later visible edit. Missing edit dates are assumed unedited by the public UI and require spot validation.",
               "seen_item_policy": "Exclude any previously reviewed item, including negatives and pre-study-window items. Use the exported seen-item masks; a later edit cannot become a historical positive edge.",
               "source_scope": settings["scope"], "data_files_sha256": {
                   path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in output.glob("*.jsonl")},
               "source_manifests_sha256": {name: hashlib.sha256((output / name).read_bytes()).hexdigest()
                                            for name in ["sampling_manifest.json", "seed_manifest.json"]}})
    lines = ["# User-history sampling audit", "", f"Version: `{settings['dataset_version']}`. Generated {stats['generated_at_utc']}.", "",
             f"Collection status: **{manifest['status']}**. Planning gate passed: **{ready}**.", "",
             "This report evaluates a new acquisition strategy, not a claim that filtering single-review users fixes the original population. The target population is explicitly a train-defined active-reviewer cohort.", "",
             "| Check | Value |", "| --- | ---: |"]
    for title, key in [("Seed users discovered using pre-cutoff API records", "seed_users"),
                       ("Profiles attempted", "profiles_attempted"), ("Raw in-catalog reviews discovered", "discovered_reviews"),
                       ("Users with discovered in-catalog reviews, before cohort filtering", "discovered_users_with_in_catalog_reviews"),
                       ("Selected users (>=3 positive training games)", "selected_users"),
                       ("Selected review records", "selected_reviews"), ("Observed games in selected cohort", "selected_games_observed"),
                       ("Fixed catalogue games", "catalogue_games"), ("Positive reviews", "positive_reviews"),
                       ("Negative reviews", "negative_reviews"), ("Blank texts retained as interactions", "blank_cohort_texts"),
                       ("Short texts flagged separately", "short_cohort_texts"), ("English text candidates available before training cutoff", "opinion_train_candidates")]:
        lines.append(f"| {title} | {stats[key]} |")
    lines += ["", "## Distribution before filtering the cohort", "",
              "Do not present the selected cohort's minimum degree as an improvement in the whole Steam population. The following includes every user with an observed in-catalog review, including incomplete profiles.", "",
              "| Distinct positive games observed | Users |", "| --- | ---: |"]
    lines += [f"| {degree} | {count} |" for degree, count in sorted(raw_positive_histories.items())]
    lines += ["", "## Chronological coverage", "", "| Check | Validation | Test |", "| --- | ---: | ---: |",
              f"| Historical positive edges | {validation['positive_training_edges']} | {testing['positive_training_edges']} |",
              f"| Warm items | {validation['warm_items']} | {testing['warm_items']} |",
              f"| Eligible target users | {validation['eligible_target_users']} | {testing['eligible_target_users']} |",
              f"| Targets with >20 candidates | {validation['targets_with_more_than_20_candidates']} | {testing['targets_with_more_than_20_candidates']} |",
              f"| Candidate count, min..max | {validation['candidate_count_min']}..{validation['candidate_count_max']} | {testing['candidate_count_min']}..{testing['candidate_count_max']} |", "",
              "The windows are proposed coverage diagnostics, not Recall/NDCG results. A user is never required to have a future target to enter the training cohort. Evaluation eligibility is subsequently reported per window.", "",
              "## Acquisition versus filtering", "",
              f"- Profile statuses: `{stats['profile_status_counts']}`.",
              f"- Cohort exclusions: `{stats['cohort_exclusion_counts']}`.",
              f"- Matched positive users in the old snapshot and complete new profiles: {len(matched)}. Observed positive edges for those matched users: old {stats['old_positive_edges_matched_users']}, new {stats['new_positive_edges_matched_users']}.",
              "- This matched comparison has a different discovery window and source method. It measures additional observed history for shared users, not a causal or representative population comparison.", "",
              "## Limits and next actions", "",
              "- Do not report 10,000 new cohort reviews or 100 observed cohort games unless the table actually reaches those counts. The 100-game catalogue is a frame, not a quota that is forcibly filled.",
              "- Exact 10,000-row truncation is incompatible with preserving complete user histories and train-only membership. The row count is a planning target; the cohort size and hard HTTP budget govern collection.",
              "- Incomplete/private/parse-failed profiles are excluded from the cohort and counted; this introduces public-profile/nonresponse bias. Public pages can shift during collection and are not immutable snapshots.",
              "- Public dates have day precision and an unknown timezone. The +38h bound is conservative for UTC offsets within +/-14h, conditional on the displayed date being correct. Missing edit dates are assumed unedited by the UI, not guaranteed by an API; manually validate a spot sample before final historical claims.",
              "- Matching seed interactions are anchored to exact API times when review ID, app, label and displayed date bounds agree. This does not assign exact times to other records or relax the public text availability bound.",
              "- Keep multilingual/short/blank review interactions; English detection and a minimum 20-token rule affect the opinion-training view only. Detector scores are not calibrated accuracy, and these flags do not validate aspect extraction or remove all memes.",
              "- Popularity means positive count in this conditional cohort. Quota-free cohort acquisition does not estimate full-platform popularity, and no inverse-probability weighting is claimed.",
              f"- This config targets {settings['target_cohort_users']} cohort users and approximately {settings['target_cohort_reviews']} reviews. The evaluation planning gate requires at least {minimum_users} cohort users and {settings['minimum_validation_users']}/{settings['minimum_test_users']} eligible validation/test users with >20 candidates. If unmet, report the failure, resume within the registered budget or reconsider the source; never choose a different split based on ranking metrics.",
              "- Coordinate split/loader contracts with the evaluation owner. These files are sampling/coverage evidence; no recommendation models or gold human annotations were fabricated."]
    atomic_text(output / "sampling_report.md", "\n".join(lines) + "\n")
    return stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs/steam_history_v3")
    args = parser.parse_args()
    print(json.dumps(build(args.output_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
