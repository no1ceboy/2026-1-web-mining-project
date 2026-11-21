import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_history_dataset import build, dump_rows, temporal_coverage, validate_row
from steam_history_sampler import HistoryClient, epoch, load_settings
from steam_crawler import ROOT, read_jsonl, write_json

SETTINGS, API_CONFIG, APPS = load_settings(ROOT / "configs/steam_history_sampling_v2.json")


def row(review, user, item, date, positive=True, updated=None):
    created = epoch(date + "T00:00:00Z")
    edited = epoch((updated or date) + "T00:00:00Z")
    return {"review_id": str(review), "user_id": user * 64, "item_id": str(item), "item_title": str(item),
            "timestamp": created, "timestamp_updated": edited, "event_time_lower_utc": created - 14 * 3600,
            "timestamp_precision": "day", "available_after_utc": edited + 38 * 3600,
            "positive_interaction": positive, "source_feedback": positive, "text": "Good game.",
            "language": "unknown", "title": "", "helpful_votes": None,
            "source_url": "https://steamcommunity.com", "crawl_time_utc": "2026-11-21T00:00:00Z"}


def historical_rows():
    return [row(1, "a", 570, "2025-01-01"), row(2, "a", 620, "2025-02-01"),
            row(3, "a", 550, "2025-03-01"), row(4, "b", 105600, "2025-01-01"),
            row(5, "b", 400, "2025-02-01"), row(6, "b", 4000, "2025-03-01")]


class CoverageTests(unittest.TestCase):
    def test_private_profile_identifier_field_is_rejected_before_export(self):
        record = row(1, "a", 570, "2023-01-01")
        record["steam_id"] = "synthetic-private-lookup"
        with self.assertRaisesRegex(ValueError, "private identifier"):
            validate_row(record, SETTINGS, {"570"})

    def test_unseen_warm_target_and_negative_seen_item_mask(self):
        records = historical_rows() + [row(7, "a", 105600, "2026-09-10")]
        stats, _, targets, _ = temporal_coverage(records, SETTINGS,
            epoch(SETTINGS["validation_cutoff_utc"]), epoch(SETTINGS["test_cutoff_utc"]))
        self.assertEqual(stats["eligible_target_users"], 1)
        self.assertEqual(targets[0]["item_id"], "105600")
        records.append(row(8, "a", 105600, "2018-03-01", positive=False))
        stats, _, _, seen = temporal_coverage(records, SETTINGS,
            epoch(SETTINGS["validation_cutoff_utc"]), epoch(SETTINGS["test_cutoff_utc"]))
        self.assertEqual(stats["eligible_target_users"], 0)
        self.assertIn("105600", seen["a" * 64])

    def test_visible_later_edit_cannot_be_a_created_time_target(self):
        records = historical_rows() + [row(7, "a", 105600, "2026-09-10", updated="2026-09-15")]
        stats, _, _, _ = temporal_coverage(records, SETTINGS,
            epoch(SETTINGS["validation_cutoff_utc"]), epoch(SETTINGS["test_cutoff_utc"]))
        self.assertEqual(stats["eligible_target_users"], 0)
        self.assertEqual(stats["target_exclusion_observations"]["target_has_visible_later_edit"], 1)

    def test_future_targets_do_not_determine_cohort_membership(self):
        # a has three training games and no future targets. b has one training
        # game and several future positives; b must still be excluded.
        records = historical_rows()[:4] + [row(7, "b", 400, "2026-09-10"),
                                           row(8, "b", 4000, "2026-10-10")]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            dump_rows(output / "discovered_reviews.jsonl", records)
            write_json(output / "sampling_manifest.json", {
                "dataset_version": SETTINGS["dataset_version"], "settings": SETTINGS,
                "status": "paused_profile_budget", "apps": APPS,
                "data_sha256": hashlib.sha256((output / "discovered_reviews.jsonl").read_bytes()).hexdigest(),
                "profiles": {"a" * 64: {"status": "complete"}, "b" * 64: {"status": "complete"}}})
            write_json(output / "seed_manifest.json", {"seeds": [
                {"user_id": "a" * 64, "seed_review_id": "1"},
                {"user_id": "b" * 64, "seed_review_id": "4"}]})
            stats = build(output)
            split = json.loads((output / "split_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(split["cohort_user_ids"], ["a" * 64])
            self.assertEqual(stats["selected_users"], 1)
            self.assertEqual(stats["test"]["eligible_target_users"], 0)
            self.assertEqual(len(read_jsonl(output / "train_reviews.jsonl")), 3)

    def test_retry_cannot_exceed_the_global_request_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = {**SETTINGS, "max_http_attempts": 1}
            client = HistoryClient(API_CONFIG, Path(directory) / "requests.jsonl", settings)
            error = urllib.error.URLError("synthetic network failure")
            with patch("urllib.request.urlopen", side_effect=error) as opening, patch("time.sleep"):
                from steam_crawler import FetchError
                with self.assertRaises(FetchError):
                    client.fetch({"appid": 570, "num_per_page": 1})
            self.assertEqual(opening.call_count, 1)
            self.assertEqual(len(read_jsonl(client.log_path)), 1)


if __name__ == "__main__":
    unittest.main()
