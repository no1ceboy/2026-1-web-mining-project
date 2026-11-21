"""Prepare an unlabeled 20-review source audit; profile links stay outside Git."""

import argparse
import csv
import hashlib
import html
import io
import json
import os
from pathlib import Path

from steam_crawler import ROOT, atomic_text, read_jsonl
from steam_history_sampler import dpapi


def export(output, limit=20):
    output = Path(output)
    manifest = json.loads((output / "sampling_manifest.json").read_text(encoding="utf-8"))
    rows = read_jsonl(output / "cohort_reviews.jsonl")
    rows = sorted(rows, key=lambda row: hashlib.sha256(row["review_id"].encode()).hexdigest())[:limit]
    buffer = io.StringIO(newline="")
    fields = ["review_id", "user_id", "item_title", "recorded_creation_utc_seconds", "recorded_update_utc_seconds",
              "timestamp_precision", "human_date_check", "human_language", "human_meaningful_text", "human_evidence_fidelity", "notes"]
    writer = csv.DictWriter(buffer, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        writer.writerow({"review_id": row["review_id"], "user_id": row["user_id"], "item_title": row["item_title"],
                         "recorded_creation_utc_seconds": row["timestamp"],
                         "recorded_update_utc_seconds": row["timestamp_updated"],
                         "timestamp_precision": row["timestamp_precision"]})
    atomic_text(output / "source_spotcheck_template.csv", buffer.getvalue())
    private = Path(os.environ["LOCALAPPDATA"]) / "WebMining/private_sampling"
    state = json.loads(dpapi((private / (manifest["config_sha256"] + ".dpapi")).read_bytes(), decrypt=True))
    parts = ["<!doctype html><meta charset='utf-8'><title>Private source spot check</title>",
             "<style>body{max-width:1000px;margin:40px auto;font-family:Arial;line-height:1.6}article{border-top:1px solid #ccc;padding:16px 0}pre{white-space:pre-wrap}</style>",
             "<h1>Private source spot check</h1><p>Local-only profile lookup links. Do not commit or upload this HTML. Fill the public CSV template yourself; its human labels are blank.</p>"]
    for row in rows:
        steam_id = state["seeds"][row["user_id"]]["steam_id"]
        review_url = f"https://steamcommunity.com/profiles/{steam_id}/recommended/{row['item_id']}/"
        history_url = f"https://steamcommunity.com/profiles/{steam_id}/recommended/?l=english"
        parts.append(f"<article><h2>{html.escape(row['item_title'])} — review {html.escape(row['review_id'])}</h2>"
                     f"<a href='{review_url}' target='_blank' rel='noreferrer'>Public review</a> · "
                     f"<a href='{history_url}' target='_blank' rel='noreferrer'>Public history</a>"
                     f"<p>Precision: {html.escape(row['timestamp_precision'])}; creation {row['timestamp']}; update {row['timestamp_updated']}</p>"
                     f"<pre>{html.escape(row['text'])}</pre></article>")
    destination = private / (manifest["dataset_version"] + "_spotcheck.html")
    atomic_text(destination, "\n".join(parts))
    print(f"Unlabeled public CSV: {output / 'source_spotcheck_template.csv'}")
    print(f"Private HTML (outside repository): {destination}")
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs/steam_history_v3")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    if not 1 <= args.limit <= 100:
        parser.error("limit must be 1..100")
    export(args.output_dir, args.limit)
