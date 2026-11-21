"""Recompute crawler-owned quality/connectivity evidence without training models."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from steam_crawler import ENDPOINT, ROOT, atomic_text, read_jsonl, utc_now, write_json


REQUIRED = {"review_id", "user_id", "item_id", "item_title", "timestamp", "crawl_time_utc",
            "source_feedback", "positive_interaction", "title", "text", "language",
            "helpful_votes", "source_url"}


def quality_errors(row):
    errors = [f"missing_{key}" for key in sorted(REQUIRED - row.keys())]
    for key in ["review_id", "item_id"]:
        if not isinstance(row.get(key), str) or not re.fullmatch(r"[0-9]+", row[key]):
            errors.append(f"invalid_{key}")
    if not isinstance(row.get("user_id"), str) or not re.fullmatch(r"[a-f0-9]{64}", row["user_id"]):
        errors.append("invalid_user_hash")
    if type(row.get("timestamp")) is not int or row.get("timestamp", 0) <= 0:
        errors.append("invalid_timestamp")
    for key in ["source_feedback", "positive_interaction"]:
        if type(row.get(key)) is not bool:
            errors.append(f"invalid_{key}")
    if row.get("source_feedback") != row.get("positive_interaction"):
        errors.append("feedback_mapping_mismatch")
    for key in ["title", "text", "item_title", "crawl_time_utc"]:
        if not isinstance(row.get(key), str):
            errors.append(f"invalid_{key}")
    try:
        if datetime.fromisoformat(row.get("crawl_time_utc", "").replace("Z", "+00:00")).utcoffset() is None:
            errors.append("crawl_time_missing_timezone")
    except (ValueError, AttributeError):
        errors.append("invalid_crawl_time")
    if row.get("language") != "english":
        errors.append("unexpected_language")
    if row.get("source_url") != ENDPOINT:
        errors.append("unexpected_source_url")
    if type(row.get("helpful_votes")) is not int or row.get("helpful_votes", -1) < 0:
        errors.append("invalid_helpful_votes")
    # The saved schema is an allowlist, so raw author objects cannot slip through.
    if row.keys() - REQUIRED:
        errors.append("unexpected_fields")
    return errors


def summarize(records):
    errors = Counter(error for row in records for error in quality_errors(row))
    if errors:
        raise ValueError(f"Schema validation failed: {dict(errors)}")
    users, positive_users = defaultdict(set), defaultdict(set)
    per_item = {}
    review_ids, pairs, positive_edges = set(), set(), set()
    for row in records:
        user, item = row["user_id"], row["item_id"]
        users[user].add(item)
        review_ids.add(row["review_id"])
        pairs.add((user, item))
        stats = per_item.setdefault(item, {"item_id": item, "item_title": row["item_title"],
                                          "reviews": 0, "positive_reviews": 0, "negative_reviews": 0})
        stats["reviews"] += 1
        stats["positive_reviews" if row["positive_interaction"] else "negative_reviews"] += 1
        if row["positive_interaction"]:
            positive_users[user].add(item)
            positive_edges.add((user, item))

    parent = {}

    def find(node):
        parent.setdefault(node, node)
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for user, item in positive_edges:
        left, right = find(("user", user)), find(("item", item))
        if left != right:
            parent[left] = right
    components = defaultdict(lambda: {"users": 0, "items": 0, "edges": 0, "item_ids": []})
    for node in sorted(parent):
        component = components[find(node)]
        component["users" if node[0] == "user" else "items"] += 1
        if node[0] == "item":
            component["item_ids"].append(node[1])
    for user, _ in positive_edges:
        components[find(("user", user))]["edges"] += 1
    component_list = sorted(components.values(), key=lambda c: (-(c["users"] + c["items"]), c["item_ids"]))
    largest = component_list[0] if component_list else {"users": 0, "items": 0, "edges": 0, "item_ids": []}
    node_count = len(parent)
    positive_count = sum(row["positive_interaction"] for row in records)
    timestamps = [row["timestamp"] for row in records]
    return {"records": len(records), "unique_review_ids": len(review_ids),
            "duplicate_review_ids": len(records) - len(review_ids),
            "duplicate_user_item_records": len(records) - len(pairs),
            "blank_texts": sum(not row["text"].strip() for row in records),
            "very_short_texts_le_3_whitespace_tokens": sum(len(row["text"].split()) <= 3 for row in records),
            "schema_invalid_records": 0, "unique_reviewers": len(users), "items": len(per_item),
            "positive_reviews": positive_count, "negative_reviews": len(records) - positive_count,
            "reviewers_on_multiple_games": sum(len(items) >= 2 for items in users.values()),
            "reviewer_game_count_distribution": dict(sorted(Counter(map(len, users.values())).items())),
            "positive_users": len(positive_users),
            "positive_users_ge_2_games": sum(len(items) >= 2 for items in positive_users.values()),
            "positive_users_ge_3_games": sum(len(items) >= 3 for items in positive_users.values()),
            "positive_history_distribution": dict(sorted(Counter(map(len, positive_users.values())).items())),
            "positive_items": len({item for _, item in positive_edges}),
            "positive_edges": len(positive_edges), "positive_graph_nodes": node_count,
            "positive_graph_components": len(component_list), "positive_components": component_list,
            "largest_positive_component": largest,
            "largest_component_node_share": (largest["users"] + largest["items"]) / node_count if node_count else 0,
            "largest_component_edge_share": largest["edges"] / len(positive_edges) if positive_edges else 0,
            "earliest_review_utc": datetime.fromtimestamp(min(timestamps), timezone.utc).isoformat() if timestamps else None,
            "latest_review_utc": datetime.fromtimestamp(max(timestamps), timezone.utc).isoformat() if timestamps else None,
            "per_game": sorted(per_item.values(), key=lambda item: int(item["item_id"]))}


def recommend(stats, manifest):
    if manifest["status"] != "completed":
        return ("SOURCE GATE UNRESOLVED", "The crawl did not reach every configured target. Review access errors and coverage before choosing the source; do not claim collection is complete.")
    # This is a bounded 20-item source pilot, not an automated model-selection gate.
    return ("RECOMMEND AMAZON FALLBACK FOR MAIN EVALUATION",
            f"This bounded pilot has only {stats['items']} games, "
            f"{stats['positive_users_ge_2_games']} users with at least two distinct positive games, "
            f"and {stats['positive_users_ge_3_games']} with at least three. These are descriptive "
            "history counts, not eligibility measured by the shared evaluator. The small candidate "
            "catalog also makes Recall@20 trivial. The recommended fallback is a project planning "
            "judgment for this pilot, not an agreed numerical acceptance threshold; Members 2/3 "
            "should verify the global split before the lead finalizes the source decision.")


def build_report(records, manifest, request_log, baseline=None, metadata=None):
    if metadata is not None and metadata["config_sha256"] != manifest["config_sha256"]:
        raise ValueError("Metadata audit does not match the crawl configuration.")
    stats = summarize(records)
    requests = [entry for entry in request_log if entry.get("purpose") == "crawl"]
    successes = [entry for entry in requests if entry["outcome"] == "success"]
    failures = [entry for entry in requests if entry["outcome"] == "failure"]
    stats["request_attempts"] = len(requests)
    stats["failed_request_attempts"] = len(failures)
    stats["successful_request_attempts"] = len(successes)
    stats["http_429_attempts"] = sum(entry.get("http_status") == 429 for entry in failures)
    stats["duplicate_observations_skipped"] = sum(app["duplicate_reviews_skipped"] for app in manifest["apps"])
    stats["invalid_observations_skipped"] = sum(app["invalid_reviews_skipped"] for app in manifest["apps"])
    stats["failed_games"] = [app["app_id"] for app in manifest["apps"] if app["status"] == "failed"]
    verdict, reason = recommend(stats, manifest)
    stats["recommendation"] = verdict
    stats["recommendation_reason"] = reason
    largest = stats["largest_positive_component"]
    lines = ["# Steam expanded pilot: crawl, quality and overlap", "",
             f"Generated at {utc_now()}. Dataset: `{manifest['dataset_version']}`. Crawl status: **{manifest['status']}**.", "",
             f"**{verdict}.** {reason}", "",
             "This is a recommendation for the project lead, not an automatic dataset switch. No Amazon data was fetched or merged.", "",
             "## Collection and provenance", "",
             f"- Source: {ENDPOINT}",
             f"- API documentation: {manifest['api_documentation']}",
             f"- Start / finish UTC: {manifest['crawl_started_utc']} / {manifest['crawl_finished_utc']}",
             f"- Configured games: {len(manifest['apps'])}; target per game: {manifest['config']['reviews_per_game']}; page size: {manifest['config']['page_size']}.",
             "- Parameters: recent (filter=1), English, all recommendation labels (review_type=0), all purchase types (purchase_type=1), off-topic filtering enabled. Parameters are passed as input_json.",
             f"- Selection: {manifest['config']['selection']}",
             f"- Crawl attempts: {len(requests)}; successful: {len(successes)}; failed: {len(failures)}; HTTP 429: {stats['http_429_attempts']}.",
             "- Access probe attempts are recorded separately in the same request log and excluded from these crawl counts.",
             "- See steam_access_check.json for this machine's access test; a teammate on a different network must test there separately.",
             "- Cursor and per-game progress are saved after each page. Data is saved atomically before the manifest; a replay after a crash deduplicates existing review IDs.",
             "- Local synthetic tests cover crash/replay and HTTP 429. Live bounded pause/resume is recorded in the manifest run_history; these are distinct from simulated failures.", "",
             "## Data quality", "", "| Check | Value |", "| --- | ---: |"]
    for title, key in [("Saved reviews", "records"), ("Unique review IDs", "unique_review_ids"),
                       ("Duplicate IDs in saved file", "duplicate_review_ids"),
                       ("Repeated user-game records", "duplicate_user_item_records"),
                       ("Blank review bodies", "blank_texts"),
                       ("Bodies with at most 3 whitespace tokens (descriptive only)", "very_short_texts_le_3_whitespace_tokens"),
                       ("Schema-invalid saved records", "schema_invalid_records"),
                       ("Duplicate observations skipped during requests/replay", "duplicate_observations_skipped"),
                       ("Invalid observations excluded before saving", "invalid_observations_skipped"),
                       ("Distinct reviewers", "unique_reviewers"), ("Distinct games", "items"),
                       ("Positive recommendations", "positive_reviews"), ("Negative recommendations", "negative_reviews")]:
        lines.append(f"| {title} | {stats[key]} |")
    lines += ["", f"Review creation-time range UTC: {stats['earliest_review_utc']} to {stats['latest_review_utc']}.",
              "All saved reviewer IDs pass the 64-character lowercase SHA-256 format check. The saved schema excludes raw author objects and SteamIDs. Source language labels were checked; no independent language classifier was run.", "",
              "## Per-game coverage", "", "| App ID | Configured game label | Reviews | Positive | Negative | Pages | Status |", "| --- | --- | ---: | ---: | ---: | ---: | --- |"]
    by_item = {row["item_id"]: row for row in stats["per_game"]}
    for app in manifest["apps"]:
        row = by_item.get(str(app["app_id"]), {"reviews": 0, "positive_reviews": 0, "negative_reviews": 0})
        lines.append(f"| {app['app_id']} | {app['game']} | {row['reviews']} | {row['positive_reviews']} | {row['negative_reviews']} | {app['pages_fetched']} | {app['status']} |")
    lines += ["", "## Metadata audit", ""]
    if metadata is None:
        lines.append("Metadata audit was not supplied. App names are configured labels; game types remain unverified.")
    else:
        lines += [f"- Public Steam store appdetails check: **{metadata['status']}**.",
                  f"- Verified game app types: **{metadata['verified_game_apps']} / {len(manifest['apps'])}**.",
                  "- Official app IDs, titles, types, request times and source URLs are saved in steam_metadata_audit.json.",
                  "- The review file keeps the configured human-readable game labels; the audit retains official titles separately (including trademark punctuation).",
                  "- This verifies the selected IDs are games; it is not a full genre/category audit or historical metadata snapshot."]
    lines += ["", "## Reviewer overlap and positive graph", "",
              "Positive graph: undirected bipartite graph with one edge per distinct user-game pair whose positive_interaction is true. Negative reviews are retained in the data but create no positive edges. Only nodes incident to positive edges are counted.", "",
              f"- Reviewers of at least two games (either feedback label): **{stats['reviewers_on_multiple_games']} / {stats['unique_reviewers']}**.",
              f"- Positive users / items / unique edges: **{stats['positive_users']} / {stats['positive_items']} / {stats['positive_edges']}**.",
              f"- Users with at least two distinct positive games: **{stats['positive_users_ge_2_games']} / {stats['positive_users']}**.",
              f"- Users with at least three distinct positive games: **{stats['positive_users_ge_3_games']} / {stats['positive_users']}**.",
              f"- Positive connected components: **{stats['positive_graph_components']}**.",
              f"- Largest component (by total nodes): **{largest['users']} users, {largest['items']} games, {largest['edges']} edges**.",
              f"- Largest component shares: **{stats['largest_component_node_share']:.2%} of positive nodes**, **{stats['largest_component_edge_share']:.2%} of positive edges**.", "",
              "| Distinct positive games per user | Users |", "| --- | ---: |"]
    for degree, count in stats["positive_history_distribution"].items():
        lines.append(f"| {degree} | {count} |")
    if baseline is not None:
        before = summarize(baseline)
        lines += ["", "## Comparison with original pilot", "",
                  "These are separate time-dependent convenience snapshots, not a random-sample comparison. The original files were not modified.", "",
                  "| Check | Original pilot | Expanded pilot |", "| --- | ---: | ---: |"]
        for title, key in [("Reviews", "records"), ("Games", "items"), ("Reviewers", "unique_reviewers"),
                           ("Multi-game reviewers", "reviewers_on_multiple_games"),
                           ("Users with >=2 positive games", "positive_users_ge_2_games"),
                           ("Users with >=3 positive games", "positive_users_ge_3_games")]:
            lines.append(f"| {title} | {before[key]} | {stats[key]} |")
    lines += ["", "## Evaluation implications and handoff", "",
              "- History counts are upper bounds only. Member 2 owns global chronological cutoffs, warm-user/item eligibility and the final evaluator; this report does not invent a competing split.",
              "- Two positive games can potentially support a user's historical interaction plus one held-out target. Three can potentially support history plus separate validation and test targets for that same user; the global protocol does not require every evaluated user to occur in both windows.",
              "- Having a large connected component does not imply that users have long histories: a few cross-game reviewers can connect many item-centered stars.",
              f"- With only {stats['items']} sampled games and seen games excluded, K=20 can cover every eligible candidate in this pilot. Recall@20 would then be trivial; do not use it as evidence of recommendation quality.",
              "- Keep both feedback labels for opinion mining. A negative recommendation is not an aspect sentiment label. Unobserved items are not verified negative labels.",
              "- Review creation timestamps do not certify historical text contents; collected reviews may have been edited later. Member 2/4 must establish an edit-time policy before historical text features are used.",
              "- Share the versioned JSONL and manifest with Member 2, and these graph diagnostics with Member 3. Member 4 can use this pilot to develop annotation guidelines; ranking features must later respect the agreed historical split.",
              "- The limited metadata check above establishes only the fields it records; do not claim a full metadata audit.",
              "- Ask the lead to confirm the Steam/Amazon decision. Do not collect beyond this bound or silently mix sources.", "",
              "## Limitations", ""]
    lines.extend(f"- {limitation}" for limitation in manifest["known_limitations"])
    return stats, "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs")
    parser.add_argument("--baseline", type=Path, default=ROOT / "outputs/steam_pilot.jsonl")
    args = parser.parse_args()
    data_path = args.output_dir / "steam_expanded_pilot.jsonl"
    manifest = json.loads((args.output_dir / "steam_expanded_manifest.json").read_text(encoding="utf-8"))
    if hashlib.sha256(data_path.read_bytes()).hexdigest() != manifest["data_sha256"]:
        raise ValueError("Dataset hash differs from the saved manifest; finish/resume the crawl first.")
    stats, report = build_report(read_jsonl(data_path), manifest,
                                 read_jsonl(args.output_dir / "steam_crawl_requests.jsonl"),
                                 read_jsonl(args.baseline) if args.baseline.exists() else None,
                                 json.loads((args.output_dir / "steam_metadata_audit.json").read_text(encoding="utf-8"))
                                 if (args.output_dir / "steam_metadata_audit.json").exists() else None)
    stats["generated_at_utc"] = utc_now()
    stats["data_sha256"] = manifest["data_sha256"]
    write_json(args.output_dir / "steam_overlap_stats.json", stats)
    atomic_text(args.output_dir / "steam_overlap_report.md", report)
    print(json.dumps({key: value for key, value in stats.items() if key not in {"per_game", "positive_components"}}, indent=2))


if __name__ == "__main__":
    main()
