from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from opinion_common import clauses, load_lexicon, validate_annotations
from opinion_evaluate import cohen_kappa, compare, gold_labels, label_sets, merge_sentiments
from opinion_extract import AspectMatcher, LexiconSentiment, extract
from opinion_profiles import available_review_ids, build_profiles, score

LEXICON = load_lexicon()
ASPECTS = list(LEXICON["aspects"])
TEXT = "Combat feels great, but the story drags. Graphics hold up!"


def ann(review, annotator, aspect, sentiment="", evidence="", notes=""):
    return {"review_id": review, "annotator_id": annotator, "aspect": aspect,
            "sentiment": sentiment, "evidence": evidence, "notes": notes}


class SegmentationAndExtractionTests(unittest.TestCase):
    def test_clause_offsets_are_exact_substrings_and_split_on_contrast(self):
        spans = [TEXT[s:e] for s, e in clauses(TEXT)]
        self.assertEqual(spans, ["Combat feels great", "the story drags", "Graphics hold up"])

    def test_lexicon_baseline_separates_aspect_sentiments_from_voted_up(self):
        review = {"review_id": "1", "user_id": "u", "item_id": "9", "timestamp": 0, "text": TEXT,
                  "positive_interaction": True}
        records = extract([review], AspectMatcher(LEXICON), LexiconSentiment(LEXICON), {}, "t")
        got = {(r["aspect"], r["sentiment"]) for r in records}
        self.assertIn(("gameplay", "positive"), got)
        self.assertIn(("story_characters", "negative"), got)
        for r in records:
            self.assertEqual(TEXT[r["evidence_start"]:r["evidence_end"]], r["evidence"])

    def test_negation_flips_polarity(self):
        self.assertEqual(LexiconSentiment(LEXICON).polarity("the servers are not good"), "negative")


class AnnotationTests(unittest.TestCase):
    def test_validation_rejects_paraphrased_evidence_and_unknown_labels(self):
        texts = {"1": TEXT}
        rows = [ann("1", "m4", "gameplay", "positive", "Combat feels great"),
                ann("1", "m4", "story_characters", "negative", "story is slow"),
                ann("1", "m4", "physics", "positive", "Graphics hold up"),
                ann("1", "m4", "none", "positive")]
        problems = validate_annotations(rows, texts, LEXICON)
        self.assertEqual(len(problems), 3)

    def test_merge_and_gold_prefers_adjudication(self):
        self.assertEqual(merge_sentiments(["positive", "negative"]), "mixed")
        self.assertEqual(merge_sentiments(["neutral", "negative"]), "negative")
        rows = [ann("1", "a", "gameplay", "positive", "x"), ann("1", "b", "gameplay", "negative", "x"),
                ann("1", "adjudicated", "gameplay", "positive", "x"), ann("2", "a", "none"),
                ann("3", "a", "audiovisual", "positive", "x"), ann("3", "b", "none")]
        gold, source, pending = gold_labels(label_sets(rows)[0])
        self.assertEqual(gold["1"], {"gameplay": "positive"})
        self.assertEqual(gold["2"], {})
        self.assertEqual(pending, ["3"])


class MetricTests(unittest.TestCase):
    def test_pair_level_prf_and_sentiment_on_matched(self):
        gold = {"1": {"gameplay": "positive", "story_characters": "negative"}, "2": {}}
        pred = {"1": {"gameplay": "negative"}, "2": {"audiovisual": "positive"}}
        result, *_ = compare(gold, pred, ASPECTS, ["1", "2"])
        self.assertEqual((result["micro"]["tp"], result["micro"]["fp"], result["micro"]["fn"]), (1, 1, 1))
        self.assertEqual(result["micro"]["f1"], 0.5)
        self.assertEqual(result["sentiment_on_matched"]["accuracy"], 0.0)

    def test_kappa_is_one_for_identical_labels(self):
        labels = {"1": {"gameplay": "positive"}, "2": {"audiovisual": "negative"}}
        self.assertEqual(cohen_kappa(labels, labels, ["1", "2"], ASPECTS), 1.0)


class ProfileTests(unittest.TestCase):
    def test_profiles_exclude_targets_late_text_and_unknown_availability(self):
        reviews = [{"review_id": "1", "available_after_utc": 50}, {"review_id": "2", "available_after_utc": 150},
                   {"review_id": "3", "available_after_utc": 10}, {"review_id": "4"}]
        self.assertEqual(available_review_ids(reviews, 100, excluded={"3"}), {"1"})

    def test_score_is_bounded_and_missing_profile_falls_back(self):
        per_review = {"1": ("u", "i", {"gameplay": ["positive"]}), "2": ("v", "i", {"gameplay": ["negative"]}),
                      "3": ("u", "j", {"story_characters": ["negative"]})}
        items, users, _prior, _ = build_profiles(per_review, ASPECTS, k=2.0, beta=1.0)
        self.assertAlmostEqual(sum(users["u"].values()), 1.0, places=5)
        o = score(users["u"], items["j"])
        self.assertTrue(-1 < o < 0)
        self.assertIsNone(score(users["u"], items.get("missing")))


if __name__ == "__main__":
    unittest.main()
