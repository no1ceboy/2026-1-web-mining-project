import json
import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from steam_history_sampler import (anchor_seed_timestamps, before, dpapi, epoch, load_settings, parse_profile,
                                    priority_users, quality, text_before, training_games)


SETTINGS = json.loads((Path(__file__).resolve().parents[1] / "configs/steam_history_sampling_v2.json").read_text(encoding="utf-8"))


def box(app=570, review=123, label="Recommended", dates="Posted 1 May, 2024.", text="", extra=""):
    return f'''<div class="review_box"><div class="leftcol"><a href="https://steamcommunity.com/app/{app}">game</a></div>
    <div class="vote_header"><div class="title">{label}</div></div><div class="content">{text}</div>
    <div class="posted">{dates}</div><a id="RecommendationVoteUpBtn{review}"></a>{extra}</div>'''


def parsed(html):
    return parse_profile(html, "a" * 64, {"570": "Dota 2", "620": "Portal 2", "550": "Left 4 Dead 2"},
                         "2026-11-21T12:00:00Z", SETTINGS)


class HistoryParsingTests(unittest.TestCase):
    def test_priority_uses_only_past_seed_game_evidence(self):
        seeds = {"a" * 64: {"seed_app_id": "570", "training_seed_items": ["570"]},
                 "b" * 64: {"seed_app_id": "620", "training_seed_items": ["620", "550"]}}
        settings = {**SETTINGS, "seed_priority": "training_seed_degree_then_hash"}
        self.assertEqual(priority_users(seeds, settings)[0], "b" * 64)

    def test_blank_negative_is_preserved_and_id_is_stable(self):
        result = parsed(box(label="Not Recommended"))
        self.assertEqual(result["problems"], {})
        row = result["rows"][0]
        self.assertEqual(row["review_id"], "123")
        self.assertIs(row["positive_interaction"], False)
        self.assertEqual(row["text"], "")
        self.assertEqual(row["timestamp_precision"], "day")
        self.assertIsNone(row["helpful_votes"])
        self.assertEqual(row["source_url"], "https://steamcommunity.com")
        self.assertFalse(quality(row, SETTINGS)["opinion_text_eligible"])

    def test_listing_count_pagination_and_edit_date(self):
        html = box(dates="Posted 30 September. Last edited 10 October.") + '''
        <div class="workshopBrowsePagingInfo">Showing 1-10 of 1,020 entries</div>
        <div class="workshopBrowsePagingControls"><a href="?p=2">next</a></div>'''
        result = parsed(html)
        self.assertEqual(result["total"], 1020)
        self.assertEqual(result["page_numbers"], [2])
        row = result["rows"][0]
        self.assertEqual(row["timestamp_updated"], epoch("2026-10-10T00:00:00Z"))
        self.assertFalse(before(row, epoch(SETTINGS["test_cutoff_utc"])))

    def test_unparseable_in_catalog_review_is_not_silently_dropped(self):
        result = parsed(box(dates="Date unavailable"))
        self.assertEqual(result["rows"], [])
        self.assertEqual(result["problems"], {"unparsed_in_catalog_review": 1})

    def test_out_of_catalog_is_not_a_parse_failure(self):
        result = parsed(box(app=999999))
        self.assertEqual(result["rows"], [])
        self.assertEqual(result["problems"], {})

    def test_future_history_cannot_create_training_eligibility(self):
        rows = parsed(box(app=570, review=1, dates="Posted 1 July, 2026.") +
                      box(app=620, review=2, dates="Posted 1 October, 2026.") +
                      box(app=550, review=3, dates="Posted 2 October, 2026."))["rows"]
        self.assertEqual(len(training_games(rows, SETTINGS)), 1)
        for row in rows[1:]:
            row["timestamp"] = epoch("2026-08-10T00:00:00Z")
            row["timestamp_updated"] = row["timestamp"]
            row["event_time_lower_utc"] = row["timestamp"] - 14 * 3600
            row["available_after_utc"] = row["timestamp"] + 38 * 3600
        self.assertEqual(len(training_games(rows, SETTINGS)), 3)

    def test_boundary_day_is_excluded_conservatively(self):
        row = parsed(box(dates="Posted 31 August, 2026."))["rows"][0]
        self.assertFalse(before(row, epoch(SETTINGS["validation_cutoff_utc"])))

    def test_exact_seed_times_do_not_make_public_text_available_early(self):
        row = parsed(box(dates="Posted 31 August, 2026."))["rows"][0]
        seed = {"seed_review_id": "123", "seed_app_id": "570",
                "seed_timestamp": epoch("2026-08-31T01:00:00Z"),
                "seed_updated": epoch("2026-08-31T01:00:00Z")}
        anchored = anchor_seed_timestamps(row, seed, SETTINGS)
        self.assertEqual(anchored["timestamp_precision"], "second")
        self.assertTrue(before(anchored, epoch(SETTINGS["validation_cutoff_utc"])))
        self.assertFalse(text_before(anchored, epoch(SETTINGS["validation_cutoff_utc"])))

    def test_secondary_retained_seed_can_anchor_its_own_time(self):
        row = parsed(box(app=620, review=456, dates="Posted 31 August, 2026."))["rows"][0]
        seed = {"seed_review_id": "123", "seed_app_id": "570", "training_seed_reviews": [
            {"seed_review_id": "456", "seed_app_id": "620", "seed_timestamp": epoch("2026-08-31T02:00:00Z"),
             "seed_updated": epoch("2026-08-31T02:00:00Z")}]}
        self.assertEqual(anchor_seed_timestamps(row, seed, SETTINGS)["timestamp_precision"], "second")

    def test_frozen_catalogue_replaces_only_unverified_ids(self):
        settings, _, apps = load_settings(Path(__file__).resolve().parents[1] / "configs/steam_history_sampling_v2.json")
        self.assertEqual(len(apps), 100)
        ids = {app["app_id"] for app in apps}
        self.assertNotIn(2694490, ids)
        self.assertNotIn(39210, ids)
        self.assertIn(435150, ids)
        self.assertIn(1151340, ids)

    @unittest.skipUnless(os.name == "nt", "Windows DPAPI")
    def test_private_resume_state_is_encrypted_and_round_trips(self):
        original = b'{"private_lookup":"synthetic-test-only"}'
        encrypted = dpapi(original)
        self.assertNotIn(b"synthetic-test-only", encrypted)
        self.assertEqual(dpapi(encrypted, decrypt=True), original)


if __name__ == "__main__":
    unittest.main()
