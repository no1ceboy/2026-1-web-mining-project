"""Extract aspect-level opinions with an exact evidence span from review text.

Backends
--------
lexicon   Transparent, dependency-free baseline. Aspect cues come from
          configs/aspect_lexicon_v0.json; clause sentiment comes from a small
          polarity lexicon with negation. Useful as a floor and for smoke tests.
hf-absa   Same aspect-cue detection, but the sentiment toward each cue is
          predicted by a pretrained aspect-based sentiment classifier
          (default: yangheng/deberta-v3-base-absa-v1.1). Requires
          `pip install torch transformers sentencepiece`.

Both backends emit one record per (review, aspect, clause). The evidence is the
clause text, an exact substring of the review (offsets included). Neither
backend has been validated on game reviews until opinion_evaluate.py is run
against human labels.

Guardrail: refuses to process more than --max-reviews reviews so nobody starts
a full-corpus run before the small benchmark has been reviewed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json 
import platform
import re
import time
from pathlib import Path

from opinion_common import (DEFAULT_LEXICON, ROOT, clauses, load_lexicon, read_jsonl,
                            term_pattern, tokens, write_json, write_jsonl)

HF_DEFAULT_MODEL = "yangheng/deberta-v3-base-absa-v1.1"
OVERALL_CUE = term_pattern("game")
SCORE_CUE = re.compile(r"\b\d{1,3}\s*/\s*10\b")


class AspectMatcher:
    def __init__(self, lexicon):
        self.patterns = [(aspect, term, term_pattern(term))
                         for aspect, spec in lexicon["aspects"].items() for term in spec["terms"]]

    def find(self, clause_text):
        """Return {aspect: first matching cue term} for one clause."""
        found = {}
        for aspect, term, pattern in self.patterns:
            if aspect not in found and pattern.search(clause_text):
                found[aspect] = term
        return found


class LexiconSentiment:
    name = "lexicon"
    version = "aspect_lexicon_v0"

    def __init__(self, lexicon):
        spec = lexicon["baseline_sentiment_lexicon"]
        self.positive = set(spec["positive"])
        self.negative = set(spec["negative"])
        self.negators = set(spec["negators"])

    def polarity(self, clause_text):
        words = tokens(clause_text)
        pos = neg = 0
        for index, word in enumerate(words):
            sign = 1 if word in self.positive else -1 if word in self.negative else 0
            if not sign:
                continue
            if any(w in self.negators for w in words[max(0, index - 3):index]):
                sign = -sign
            pos += sign > 0
            neg += sign < 0
        if pos and neg:
            return "mixed"
        return "positive" if pos else "negative" if neg else "neutral"

    def classify(self, pairs):
        return [(self.polarity(clause), None) for clause, _term in pairs]


class HFAbsaSentiment:
    name = "hf-absa"

    def __init__(self, model_name, device, batch_size):
        try:
            import torch
            from transformers import pipeline
        except ImportError as error:  # pragma: no cover - depends on local install
            raise SystemExit("hf-absa needs `pip install torch transformers sentencepiece`") from error
        if device == "auto":
            device = 0 if torch.cuda.is_available() else -1
        self.device = device
        self.batch_size = batch_size
        self.version = model_name
        self.pipe = pipeline("text-classification", model=model_name, tokenizer=model_name,
                             device=device, truncation=True, max_length=256)
        self.hardware = (torch.cuda.get_device_name(device) if device != -1 else "cpu")
        self.torch_version = torch.__version__

    def classify(self, pairs):
        if not pairs:
            return []
        inputs = [{"text": clause, "text_pair": term} for clause, term in pairs]
        outputs = self.pipe(inputs, batch_size=self.batch_size)
        return [(o["label"].lower(), round(float(o["score"]), 4)) for o in outputs]


def candidates(review, matcher, include_overall):
    text = review.get("text") or ""
    for start, end in clauses(text):
        clause = text[start:end]
        found = matcher.find(clause)
        for aspect, term in found.items():
            yield aspect, term, start, end
        if include_overall and not found and (OVERALL_CUE.search(clause) or SCORE_CUE.search(clause)):
            yield "overall", "game", start, end


def extract(reviews, matcher, backend, config, run_id, include_overall=True):
    pending = []
    for review in reviews:
        for aspect, term, start, end in candidates(review, matcher, include_overall):
            pending.append((review, aspect, term, start, end))
    labels = backend.classify([(r["text"][s:e], t) for r, _a, t, s, e in pending])
    records = []
    for (review, aspect, term, start, end), (sentiment, confidence) in zip(pending, labels):
        records.append({
            "review_id": str(review["review_id"]), "user_id": review.get("user_id"),
            "item_id": str(review.get("item_id")), "timestamp": review.get("timestamp"),
            "aspect": aspect, "aspect_term": term, "sentiment": sentiment,
            "evidence": review["text"][start:end], "evidence_start": start, "evidence_end": end,
            "confidence": confidence, "model": backend.name, "model_version": backend.version,
            "config": config, "run_id": run_id,
        })
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", default=str(ROOT / "outputs/steam_pilot.jsonl"))
    parser.add_argument("--review-ids", help="optional CSV/TXT whose review_id column or lines restrict the input")
    parser.add_argument("--output", default=str(ROOT / "outputs/opinion_extraction_v0.jsonl"))
    parser.add_argument("--manifest", help="defaults to <output>_manifest.json")
    parser.add_argument("--backend", choices=["lexicon", "hf-absa"], default="lexicon")
    parser.add_argument("--model", default=HF_DEFAULT_MODEL)
    parser.add_argument("--device", default="auto", help="auto, -1 for CPU, or a CUDA index")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lexicon", default=str(DEFAULT_LEXICON))
    parser.add_argument("--no-overall", action="store_true")
    parser.add_argument("--max-reviews", type=int, default=500)
    args = parser.parse_args()

    reviews = [r for r in read_jsonl(args.input) if (r.get("text") or "").strip()]
    if args.review_ids:
        reviews = [r for r in reviews if str(r["review_id"]) in load_ids(args.review_ids)]
    if len(reviews) > args.max_reviews:
        raise SystemExit(f"{len(reviews)} reviews exceeds --max-reviews={args.max_reviews}; "
                         "benchmark a small batch first and raise the limit deliberately")

    lexicon = load_lexicon(args.lexicon)
    if args.backend == "lexicon":
        backend = LexiconSentiment(lexicon)
        hardware, extra = platform.processor() or "cpu", {}
    else:
        device = args.device if args.device == "auto" else int(args.device)
        load_start = time.perf_counter()
        backend = HFAbsaSentiment(args.model, device, args.batch_size)
        hardware = backend.hardware
        extra = {"model_load_seconds": round(time.perf_counter() - load_start, 2),
                 "torch": backend.torch_version}

    config = {"backend": args.backend, "lexicon": lexicon["version"],
              "include_overall": not args.no_overall,
              "segmentation": "clauses split on . ! ? ; newline, 'but', 'however'"}
    if args.backend == "hf-absa":
        config.update({"model": args.model, "batch_size": args.batch_size, "max_length": 256})
    run_id = f"{args.backend}-{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

    start = time.perf_counter()
    records = extract(reviews, AspectMatcher(lexicon), backend, config, run_id, not args.no_overall)
    seconds = time.perf_counter() - start
    write_jsonl(args.output, records)

    manifest = args.manifest or str(Path(args.output).with_suffix("")) + "_manifest.json"
    write_json(manifest, {
        "run_id": run_id, "input": rel(args.input), "review_id_filter": rel(args.review_ids) if args.review_ids else None,
        "output": rel(args.output), "config": config, "reviews": len(reviews), "records": len(records),
        "reviews_with_any_record": len({r["review_id"] for r in records}),
        "inference_seconds": round(seconds, 3),
        "reviews_per_second": round(len(reviews) / seconds, 2) if seconds else None,
        "hardware": hardware, "python": platform.python_version(), **extra,
        "validation_status": "unvalidated until compared with human labels by opinion_evaluate.py",
    })
    print(f"{len(records)} records from {len(reviews)} reviews in {seconds:.2f}s -> {args.output}")


def load_ids(path):
    import csv
    with open(path, encoding="utf-8-sig", newline="") as handle:
        if str(path).endswith(".csv"):
            return {row["review_id"] for row in csv.DictReader(handle)}
        return {line.strip() for line in handle if line.strip()}


def rel(path):
    try:
        return Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


if __name__ == "__main__":
    main()
