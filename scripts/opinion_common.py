"""Shared helpers for the opinion-mining workstream (Member 4).

Dependency-free so the annotation tools and evaluator run on any teammate's
machine. Model backends live in opinion_extract.py and import heavy packages
lazily.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEXICON = ROOT / "configs/aspect_lexicon_v0.json"

ANNOTATION_FIELDS = ["review_id", "annotator_id", "aspect", "sentiment", "evidence", "notes"]
ADJUDICATED_ID = "adjudicated"
SPECIAL_LABELS = ("overall", "none")

# Clause boundaries: sentence punctuation, newlines, semicolons, and a contrast
# conjunction. Contrast splitting keeps "Combat feels great, but the story drags"
# as two evidence clauses.
_BOUNDARY = re.compile(r"[.!?;\n]+|,?\s+\bbut\b\s+|,?\s+\bhowever\b,?\s+", re.IGNORECASE)
_TOKEN = re.compile(r"[a-z0-9]+(?:['’][a-z]+)?|[a-z0-9]+-[a-z0-9]+", re.IGNORECASE)


def read_jsonl(path):
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path, rows):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_json(path, payload):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def load_lexicon(path=DEFAULT_LEXICON):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def aspect_names(lexicon):
    return list(lexicon["aspects"])


def tokens(text):
    return [t.lower() for t in _TOKEN.findall(text or "")]


def clauses(text):
    """Yield (start, end) offsets of non-empty clauses; text[start:end] is exact."""
    text = text or ""
    start = 0
    for match in _BOUNDARY.finditer(text):
        yield from _trim(text, start, match.start())
        start = match.end()
    yield from _trim(text, start, len(text))


def _trim(text, start, end):
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    if end > start and re.search(r"\w", text[start:end]):
        yield start, end


def term_pattern(term):
    escaped = r"\s+".join(re.escape(part) for part in term.split())
    return re.compile(rf"(?<![\w-]){escaped}(?![\w-])", re.IGNORECASE)


def english_score(text):
    """Share of tokens that are common English function words.

    A cheap, documented heuristic used only to skip clearly non-English pilot
    reviews when assembling an annotation batch; annotators still flag any
    misses with `not_english` in notes. It is not a language-ID benchmark.
    """
    common = {"the", "a", "an", "and", "or", "but", "is", "it", "this", "that", "to", "of",
              "in", "for", "with", "you", "i", "my", "game", "was", "are", "be", "on", "not",
              "have", "so", "just", "if", "they", "at", "all", "me", "your", "can", "play"}
    words = tokens(text)
    if not words:
        return 0.0
    return sum(w in common for w in words) / len(words)


def read_annotations(path):
    with open(path, encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [f for f in ANNOTATION_FIELDS if f not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path}: missing columns {missing}")
        return [{k: (row.get(k) or "").strip() if k != "evidence" else (row.get(k) or "")
                 for k in ANNOTATION_FIELDS} for row in reader]


def validate_annotations(rows, texts, lexicon):
    """Return a list of human-readable problems; empty means the file is usable.

    Checks label vocabularies and that every evidence span is an exact
    substring of the review text, so evidence can be shown in the demo verbatim.
    """
    valid_aspects = set(aspect_names(lexicon)) | set(SPECIAL_LABELS)
    valid_sentiments = set(lexicon["sentiments"])
    problems = []
    for number, row in enumerate(rows, start=2):  # header is line 1
        where = f"line {number} (review {row['review_id'] or '?'})"
        if not row["review_id"] or not row["annotator_id"]:
            problems.append(f"{where}: review_id and annotator_id are required")
            continue
        if row["review_id"] not in texts:
            problems.append(f"{where}: review_id not found in the source reviews")
            continue
        if row["aspect"] not in valid_aspects:
            problems.append(f"{where}: unknown aspect {row['aspect']!r}")
        if row["aspect"] == "none":
            if row["sentiment"] or row["evidence"].strip():
                problems.append(f"{where}: aspect 'none' must have empty sentiment and evidence")
            continue
        if row["sentiment"] not in valid_sentiments:
            problems.append(f"{where}: unknown sentiment {row['sentiment']!r}")
        if not row["evidence"].strip():
            problems.append(f"{where}: evidence span is required")
        elif row["evidence"] not in texts[row["review_id"]]:
            problems.append(f"{where}: evidence is not an exact substring of the review text")
    return problems
