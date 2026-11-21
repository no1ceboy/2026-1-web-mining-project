"""Offline tests for source handling, bounded resume and graph diagnostics."""

import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import steam_crawler as crawler
from steam_overlap_report import quality_errors, recommend, summarize


def config():
    value = crawler.load_config(crawler.ROOT / "configs/steam_crawl_v0.json")
    value["apps"] = [{"app_id": 1, "game": "Test A"}, {"app_id": 2, "game": "Test B"}]
    value.update(reviews_per_game=3, page_size=2)
    return value


def review(number, user=None, positive=True):
    return {"recommendationid": str(number), "author": {"steamid": str(user or number)},
            "review": "Test review text.", "timestamp_created": 1700000000 + number,
            "voted_up": positive, "language": "english", "votes_up": 0}


class FakeClient:
    def __init__(self):
        self.calls = []

    def fetch(self, params):
        self.calls.append(copy.deepcopy(params))
        base = params["appid"] * 100
        start = 1 if params["cursor"] == "*" else 3
        return {"reviews": [review(base + start), review(base + start + 1, positive=False)],
                "cursor": "page2" if start == 1 else "page3", "total_matching": 20}


class NormalizationTests(unittest.TestCase):
    def test_expanded_config_has_100_distinct_games_and_rejects_101(self):
        expanded = crawler.load_config(crawler.ROOT / "configs/steam_crawl_100games_v1.json")
        self.assertEqual(len(expanded["apps"]), 100)
        self.assertEqual(expanded["reviews_per_game"] * len(expanded["apps"]), 10000)
        expanded["apps"].append({"app_id": 999999999, "game": "Test"})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            crawler.write_json(path, expanded)
            with self.assertRaisesRegex(ValueError, "100 games"):
                crawler.load_config(path)

    def test_update_time_preserved_and_checked_without_changing_creation_time(self):
        source = review(1)
        source["timestamp_updated"] = source["timestamp_created"] + 100
        row = crawler.normalize_review(source, config()["apps"][0], crawler.utc_now())
        self.assertEqual(row["timestamp_updated"], source["timestamp_updated"])
        self.assertEqual(row["timestamp"], source["timestamp_created"])
        self.assertEqual(quality_errors(row), [])
        source["timestamp_updated"] = source["timestamp_created"] - 1
        with self.assertRaisesRegex(ValueError, "update_timestamp"):
            crawler.normalize_review(source, config()["apps"][0], crawler.utc_now())

    def test_hash_and_negative_feedback_preserved_without_author_object(self):
        source = review(1, user=123, positive=False)
        row = crawler.normalize_review(source, config()["apps"][0], crawler.utc_now())
        self.assertEqual(row["user_id"], hashlib.sha256(b"123").hexdigest())
        self.assertIs(row["source_feedback"], False)
        self.assertIs(row["positive_interaction"], False)
        self.assertEqual(row["item_id"], "1")
        self.assertEqual(quality_errors(row), [])
        self.assertNotIn("steamid", row)
        self.assertNotIn("author", row)

    def test_missing_feedback_is_not_silently_assumed_negative(self):
        source = review(1)
        del source["voted_up"]
        with self.assertRaisesRegex(ValueError, "voted_up"):
            crawler.normalize_review(source, config()["apps"][0], crawler.utc_now())

    def test_new_api_numeric_enums_and_cursor(self):
        params = crawler.request_parameters(config(), 1, "a+b/==")
        self.assertEqual(params["filter"], 1)
        self.assertEqual(params["purchase_type"], 1)
        self.assertEqual(params["review_type"], 0)
        self.assertEqual(params["languages"], ["english"])
        self.assertEqual(params["cursor"], "a+b/==")


class ResumeTests(unittest.TestCase):
    def test_pause_resume_exact_bound_and_completed_rerun_no_requests(self):
        with tempfile.TemporaryDirectory() as directory:
            client = FakeClient()
            first = crawler.crawl(config(), directory, client, max_pages_per_run=1)
            self.assertEqual(first["status"], "paused_page_budget")
            self.assertEqual(first["total_records"], 2)
            final = crawler.crawl(config(), directory, client)
            self.assertEqual(final["status"], "completed")
            records = crawler.read_jsonl(Path(directory) / "steam_expanded_pilot.jsonl")
            self.assertEqual(len(records), 6)
            self.assertEqual(len({row["review_id"] for row in records}), 6)
            self.assertEqual([app["records_saved"] for app in final["apps"]], [3, 3])
            call_count = len(client.calls)
            crawler.crawl(config(), directory, client)
            self.assertEqual(len(client.calls), call_count)

    def test_crash_between_data_and_manifest_replays_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            client = FakeClient()
            crawler.crawl(config(), directory, client, max_pages_per_run=1)
            manifest_path = Path(directory) / "steam_expanded_manifest.json"
            stale = json.loads(manifest_path.read_text(encoding="utf-8"))
            stale["apps"][0].update(cursor="*", pages_fetched=0, records_saved=0)
            crawler.write_json(manifest_path, stale)
            final = crawler.crawl(config(), directory, client)
            rows = crawler.read_jsonl(Path(directory) / "steam_expanded_pilot.jsonl")
            self.assertEqual(final["total_records"], 6)
            self.assertEqual(len({row["review_id"] for row in rows}), 6)
            self.assertEqual(final["apps"][0]["duplicate_reviews_skipped"], 2)

    def test_changed_config_rejected_before_network_call(self):
        with tempfile.TemporaryDirectory() as directory:
            client = FakeClient()
            crawler.crawl(config(), directory, client, max_pages_per_run=1)
            changed = config()
            changed["page_size"] = 1
            count = len(client.calls)
            with self.assertRaisesRegex(ValueError, "Config differs"):
                crawler.crawl(changed, directory, client)
            self.assertEqual(len(client.calls), count)

    def test_source_denial_stops_before_next_game(self):
        class Denied:
            calls = 0

            def fetch(self, params):
                self.calls += 1
                raise crawler.FetchError("HTTP 403", 403)

        with tempfile.TemporaryDirectory() as directory:
            client = Denied()
            result = crawler.crawl(config(), directory, client)
            self.assertEqual(client.calls, 1)
            self.assertEqual(result["status"], "blocked_source_access")
            self.assertEqual(result["total_records"], 0)

    def test_empty_or_stalled_cursor_terminates(self):
        class Empty:
            def fetch(self, params):
                return {"reviews": [], "cursor": "*"}

        class Stalled:
            def fetch(self, params):
                return {"reviews": [review(params["appid"])], "cursor": "*"}

        for client, status in [(Empty(), "exhausted"), (Stalled(), "cursor_stalled")]:
            with self.subTest(status=status), tempfile.TemporaryDirectory() as directory:
                result = crawler.crawl(config(), directory, client)
                self.assertTrue(all(app["status"] == status for app in result["apps"]))


class HttpTests(unittest.TestCase):
    def test_429_retry_after_then_success_without_persisting_raw_response(self):
        with tempfile.TemporaryDirectory() as directory:
            client = crawler.SteamClient(config(), Path(directory) / "log.jsonl")
            response = io.BytesIO(json.dumps({"response": {"reviews": [review(1)], "cursor": "next"}}).encode())
            response.status = 200
            error = urllib.error.HTTPError(crawler.ENDPOINT, 429, "rate limit", {"Retry-After": "3"}, None)
            with patch.object(crawler.urllib.request, "urlopen", side_effect=[error, response]), \
                    patch.object(crawler.time, "sleep") as sleep:
                result = client.fetch(crawler.request_parameters(config(), 1))
            self.assertEqual(len(result["reviews"]), 1)
            self.assertTrue(any(call.args == (3.0,) for call in sleep.call_args_list))
            logs = crawler.read_jsonl(client.log_path)
            self.assertEqual([entry["outcome"] for entry in logs], ["failure", "success"])
            self.assertNotIn("steamid", client.log_path.read_text())
            self.assertEqual(logs[0]["http_status"], 429)

    def test_long_retry_after_returns_control_without_early_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            client = crawler.SteamClient(config(), Path(directory) / "log.jsonl")
            error = urllib.error.HTTPError(crawler.ENDPOINT, 429, "rate limit", {"Retry-After": "120"}, None)
            with patch.object(crawler.urllib.request, "urlopen", side_effect=error) as opening, \
                    patch.object(crawler.time, "sleep") as sleep:
                with self.assertRaises(crawler.FetchError):
                    client.fetch(crawler.request_parameters(config(), 1))
            self.assertEqual(opening.call_count, 1)
            sleep.assert_not_called()


class GraphTests(unittest.TestCase):
    def test_source_assessment_does_not_reuse_small_catalog_claim_for_100_games(self):
        stats = {"items": 100, "positive_users_ge_2_games": 100, "positive_users_ge_3_games": 10}
        verdict, reason = recommend(stats, {"status": "completed"})
        self.assertIn("SPLIT CHECK", verdict)
        self.assertNotIn("makes Recall@20 trivial", reason)

    def test_known_component_degrees_and_negative_exclusion(self):
        rows = []
        for number, user, item, positive in [(1, 10, 1, True), (2, 10, 2, True),
                                            (3, 20, 2, True), (4, 20, 3, True),
                                            (5, 30, 1, True), (6, 40, 4, False)]:
            rows.append(crawler.normalize_review(review(number, user, positive),
                                                 {"app_id": item, "game": str(item)}, crawler.utc_now()))
        stats = summarize(rows)
        self.assertEqual(stats["positive_edges"], 5)
        self.assertEqual(stats["positive_graph_components"], 1)
        self.assertEqual(stats["positive_users_ge_2_games"], 2)
        self.assertEqual(stats["positive_users_ge_3_games"], 0)
        self.assertEqual(stats["largest_positive_component"]["users"], 3)
        self.assertEqual(stats["largest_positive_component"]["items"], 3)
        self.assertEqual(stats["largest_component_node_share"], 1)
        self.assertEqual(stats["negative_reviews"], 1)

    def test_raw_id_extra_field_fails_schema_audit(self):
        row = crawler.normalize_review(review(1), config()["apps"][0], crawler.utc_now())
        row["steamid"] = "123"
        with self.assertRaisesRegex(ValueError, "unexpected_fields"):
            summarize([row])


if __name__ == "__main__":
    unittest.main()
