"""Bounded Steam review crawl. Python 3.10+, standard library only.

Run from the repository root; see docs/steam_data_collection.md.
Raw API responses and SteamIDs are deliberately never written to disk.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs/steam_crawl_100games_v1.json"
DEFAULT_OUTPUT_DIR = ROOT / "outputs/steam_100games_v1"
ENDPOINT = "https://api.steampowered.com/IUserReviewsService/GetAppReviews/v1/"
DOCUMENTATION = "https://partner.steamgames.com/doc/webapi/IUserReviewsService?l=english"
USER_AGENT = "WebMiningCapstone/0.1 (bounded academic feasibility pilot)"
LIMITATIONS = [
    "Bounded convenience sample, not representative of Steam or all game players.",
    "Recent English reviews only; manually selected games; off-topic filtering enabled.",
    "No complete purchase/exposure histories; unobserved games are not verified dislikes.",
    "Steam voted_up is overall binary recommendation feedback, not aspect sentiment.",
    "SHA-256 reviewer identifiers are pseudonymous, not anonymous.",
    "Review text can be edited after creation: timestamp is creation time, not proof that the collected text existed then. Strict historical text evaluation needs an edit-time policy or historical snapshots.",
    "API responses may be cached; collection settings do not reproduce an immutable server snapshot.",
    "App names are manually configured labels, not a complete metadata audit.",
]


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def atomic_text(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=path.parent, delete=False, suffix=".tmp") as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def write_json(path, value):
    atomic_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def read_jsonl(path):
    if not Path(path).exists():
        return []
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()
            if line.strip()]


def fingerprint(config):
    return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()


def load_config(path):
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    apps = config["apps"]
    if not 1 <= len(apps) <= 100:
        raise ValueError("Configure between 1 and 100 games.")
    ids = [app["app_id"] for app in apps]
    if len(ids) != len(set(ids)) or any(type(i) is not int or i <= 0 for i in ids):
        raise ValueError("App IDs must be unique positive integers.")
    if any(not isinstance(app["game"], str) or not app["game"].strip() for app in apps):
        raise ValueError("Each app needs a game label.")
    for key, low, high in [("reviews_per_game", 1, 100), ("page_size", 1, 100),
                           ("max_pages_per_game", 1, 10), ("max_retries", 0, 3)]:
        if type(config[key]) is not int or not low <= config[key] <= high:
            raise ValueError(f"{key} must be an integer between {low} and {high}.")
    for key in ["request_interval_seconds", "timeout_seconds", "backoff_seconds"]:
        if not isinstance(config[key], (int, float)) or config[key] <= 0:
            raise ValueError(f"{key} must be positive.")
    if config["request_interval_seconds"] < 1:
        raise ValueError("Use at least one second between requests.")
    if (config["language"], config["sort"], config["purchase_type"], config["review_type"]) != (
            "english", "recent", "all", "all"):
        raise ValueError("This pilot requires recent English reviews, all purchases and both labels.")
    if config["filter_offtopic_activity"] is not True:
        raise ValueError("Keep the source's off-topic filter enabled for this pilot.")
    return config


def request_parameters(config, app_id, cursor="*", page_size=None):
    # These are the NEW API's numeric enums, passed inside input_json.
    return {"appid": app_id, "filter": 1, "languages": [config["language"]],
            "review_type": 0, "purchase_type": 1,
            "num_per_page": page_size or config["page_size"], "cursor": cursor,
            "filter_offtopic_activity": config["filter_offtopic_activity"]}


class FetchError(Exception):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


class SteamClient:
    def __init__(self, config, log_path):
        self.config = config
        self.log_path = Path(log_path)
        self.last_request = None

    def before_attempt(self):
        """Extension point for clients with an overall HTTP attempt budget."""

    def log(self, event):
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
            handle.flush()

    def fetch(self, params, purpose="crawl"):
        url = ENDPOINT + "?" + urllib.parse.urlencode({"input_json": json.dumps(params)})
        for attempt in range(self.config["max_retries"] + 1):
            self.before_attempt()
            if self.last_request is not None:
                time.sleep(max(0, self.config["request_interval_seconds"] -
                               (time.monotonic() - self.last_request)))
            self.last_request = time.monotonic()
            event = {"requested_at_utc": utc_now(), "purpose": purpose,
                     "parameters": params, "attempt": attempt + 1}
            status, retry_after, error, retryable = None, None, None, False
            try:
                request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(request, timeout=self.config["timeout_seconds"]) as response:
                    status = response.status
                    raw = response.read(4 * 1024 * 1024 + 1)
                if len(raw) > 4 * 1024 * 1024:
                    raise ValueError("Response exceeds 4 MiB limit")
                payload = json.loads(raw)
                body = payload.get("response", payload)
                # Steam omits the repeated reviews field for explicit zero-result
                # queries (for example a game released after a historical cutoff).
                if (isinstance(body, dict) and "reviews" not in body and body.get("total_matching") == 0 and
                        isinstance(body.get("query_summary"), dict) and body["query_summary"].get("num_reviews") == 0):
                    body["reviews"] = []
                if not isinstance(body, dict) or not isinstance(body.get("reviews"), list):
                    raise ValueError("Response has no reviews list")
                if len(body["reviews"]) > params["num_per_page"]:
                    raise ValueError("Response exceeds requested page size")
                event.update(http_status=status, outcome="success",
                             elapsed_seconds=round(time.monotonic() - self.last_request, 3),
                             reviews_returned=len(body["reviews"]), next_cursor=body.get("cursor"),
                             total_matching=body.get("total_matching"))
                self.log(event)
                return body
            except urllib.error.HTTPError as exc:
                status = exc.code
                retry_after = exc.headers.get("Retry-After") if exc.headers else None
                error = f"HTTP {status}"
                retryable = status == 429 or status in {500, 502, 503, 504}
                exc.close()
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
                # Exception text/raw response can contain source content. Log type only.
                error, retryable = type(exc).__name__, True
            except (ValueError, TypeError, AttributeError) as exc:
                error = f"Invalid API response ({type(exc).__name__})"
            delay = min(60, self.config["backoff_seconds"] * 2 ** attempt)
            if retry_after:
                try:
                    seconds = float(retry_after)
                except ValueError:
                    try:
                        seconds = (parsedate_to_datetime(retry_after) -
                                   datetime.now(timezone.utc)).total_seconds()
                    except (ValueError, TypeError, OverflowError):
                        seconds = 0
                delay = max(delay, seconds)
            retry = retryable and attempt < self.config["max_retries"] and delay <= 60
            event.update(http_status=status, outcome="failure", error=error,
                         elapsed_seconds=round(time.monotonic() - self.last_request, 3),
                         retry_after=retry_after, will_retry=retry,
                         wait_seconds=delay if retry else 0)
            self.log(event)
            if not retry:
                raise FetchError(error, status)
            print(f"Request failed ({error}); retrying in {delay:g}s.", flush=True)
            time.sleep(delay)
        raise AssertionError("Unreachable")


def normalize_review(review, app, collected_at):
    if not isinstance(review, dict):
        raise ValueError("invalid_review_object")
    author = review.get("author")
    steam_id = author.get("steamid") if isinstance(author, dict) else None
    if not isinstance(steam_id, str) or not re.fullmatch(r"[0-9]+", steam_id):
        raise ValueError("missing_or_invalid_reviewer_id")
    review_id = str(review.get("recommendationid", ""))
    if not re.fullmatch(r"[0-9]+", review_id):
        raise ValueError("missing_or_invalid_review_id")
    if type(review.get("voted_up")) is not bool:
        raise ValueError("missing_or_invalid_voted_up")
    if type(review.get("timestamp_created")) is not int or review["timestamp_created"] <= 0:
        raise ValueError("missing_or_invalid_timestamp")
    if not isinstance(review.get("review"), str):
        raise ValueError("missing_or_invalid_review_text")
    if review.get("language") != "english":
        raise ValueError("unexpected_language")
    votes = review.get("votes_up", 0)
    if type(votes) is not int or votes < 0:
        raise ValueError("invalid_helpful_votes")
    record = {"review_id": review_id,
            "user_id": hashlib.sha256(steam_id.encode("utf-8")).hexdigest(),
            "item_id": str(app["app_id"]), "item_title": app["game"],
            "timestamp": review["timestamp_created"], "crawl_time_utc": collected_at,
            "source_feedback": review["voted_up"], "positive_interaction": review["voted_up"],
            "title": "", "text": review["review"], "language": review["language"],
            "helpful_votes": votes, "source_url": ENDPOINT}
    if "timestamp_updated" in review:
        updated = review["timestamp_updated"]
        if type(updated) is not int or updated < record["timestamp"]:
            raise ValueError("invalid_update_timestamp")
        record["timestamp_updated"] = updated
    return record


def initial_manifest(config):
    return {"manifest_version": 1, "dataset_version": config["dataset_version"],
            "config_sha256": fingerprint(config), "config": config,
            "endpoint": ENDPOINT, "api_documentation": DOCUMENTATION,
            "crawl_started_utc": utc_now(), "crawl_finished_utc": None, "status": "in_progress",
            "user_id_transform": "SHA-256 of UTF-8 SteamID; unsalted; consistent with original pilot",
            "known_limitations": LIMITATIONS,
            "apps": [{"app_id": app["app_id"], "game": app["game"], "cursor": "*",
                      "pages_fetched": 0, "records_saved": 0, "reviews_returned": 0,
                      "duplicate_reviews_skipped": 0, "invalid_reviews_skipped": 0,
                      "invalid_reasons": {}, "status": "pending", "error": None}
                     for app in config["apps"]]}


def checkpoint(output_dir, records, manifest):
    # Data first, manifest second. A crash between replacements replays the old cursor;
    # loading saved IDs on resume makes that replay idempotent.
    data_path = Path(output_dir) / "steam_expanded_pilot.jsonl"
    atomic_text(data_path, "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records))
    manifest["total_records"] = len(records)
    manifest["unique_review_ids"] = len({row["review_id"] for row in records})
    manifest["unique_hashed_reviewers"] = len({row["user_id"] for row in records})
    manifest["data_sha256"] = hashlib.sha256(data_path.read_bytes()).hexdigest()
    manifest["last_saved_utc"] = utc_now()
    if manifest.get("run_history"):
        run = manifest["run_history"][-1]
        run["status"] = manifest["status"]
        run["pages_fetched_this_run"] = sum(app["pages_fetched"] for app in manifest["apps"]) - run["pages_before_run"]
        if manifest["status"] != "in_progress":
            run["finished_at_utc"] = manifest["last_saved_utc"]
    write_json(Path(output_dir) / "steam_expanded_manifest.json", manifest)


def check_access(config, output_dir, client):
    result = {"tested_at_utc": utc_now(), "endpoint": ENDPOINT,
              "environment": "This execution machine and its current network; no VPN/proxy was configured by this crawler.",
              "parameters": request_parameters(config, config["apps"][0]["app_id"], page_size=2)}
    started = time.monotonic()
    try:
        body = client.fetch(result["parameters"], purpose="access_check")
        reviews = body["reviews"]
        for review in reviews:
            normalize_review(review, config["apps"][0], result["tested_at_utc"])
        if not reviews:
            raise FetchError("No reviews returned to validate the schema")
        result.update(status="success", http_status=200, reviews_returned=len(reviews),
                      schema_check="passed", has_cursor=bool(body.get("cursor")))
    except (FetchError, ValueError) as exc:
        result.update(status="failed", error=str(exc), http_status=getattr(exc, "status", None))
    result["elapsed_seconds"] = round(time.monotonic() - started, 3)
    write_json(Path(output_dir) / "steam_access_check.json", result)
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return result["status"] == "success"


def crawl(config, output_dir, client, max_pages_per_run=None):
    output_dir = Path(output_dir)
    manifest_path = output_dir / "steam_expanded_manifest.json"
    data_path = output_dir / "steam_expanded_pilot.jsonl"
    if data_path.exists() and not manifest_path.exists():
        raise ValueError("Data exists without its manifest; use a new output directory.")
    manifest = (json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists()
                else initial_manifest(config))
    if manifest["config_sha256"] != fingerprint(config):
        raise ValueError("Config differs from saved crawl. Restore it or use a new output directory.")
    records = read_jsonl(data_path)
    seen = {row["review_id"] for row in records}
    counts = Counter(row["item_id"] for row in records)
    allowed = {str(app["app_id"]) for app in config["apps"]}
    if len(seen) != len(records) or set(counts) - allowed:
        raise ValueError("Saved dataset has duplicate IDs or unexpected games.")
    if any(n > config["reviews_per_game"] for n in counts.values()):
        raise ValueError("Saved dataset exceeds the configured bound.")
    if not data_path.exists() and manifest.get("total_records", 0):
        raise ValueError("Saved dataset is missing; refusing to resume from advanced cursors.")
    manifest["status"], manifest["crawl_finished_utc"] = "in_progress", None
    manifest.setdefault("run_history", []).append({"started_at_utc": utc_now(),
        "pages_before_run": sum(app["pages_fetched"] for app in manifest["apps"]),
        "max_pages_per_run": max_pages_per_run, "status": "in_progress"})
    checkpoint(output_dir, records, manifest)
    pages_this_run = 0
    try:
        for app in manifest["apps"]:
            app["records_saved"] = counts[str(app["app_id"])]
            if app["records_saved"] >= config["reviews_per_game"]:
                app.update(status="target_reached", error=None)
                continue
            if app["status"] in {"exhausted", "page_limit", "cursor_stalled"}:
                continue
            while app["pages_fetched"] < config["max_pages_per_game"]:
                if max_pages_per_run is not None and pages_this_run >= max_pages_per_run:
                    manifest["status"] = "paused_page_budget"
                    checkpoint(output_dir, records, manifest)
                    return manifest
                params = request_parameters(config, app["app_id"], app["cursor"])
                try:
                    body = client.fetch(params)
                except FetchError as exc:
                    app.update(status="failed", error=str(exc))
                    checkpoint(output_dir, records, manifest)
                    # Access denial / exhausted rate limit is a source gate, not a reason
                    # to send another nineteen failing requests.
                    if exc.status in {401, 403, 429} or exc.status is None:
                        manifest["status"] = "blocked_source_access"
                        checkpoint(output_dir, records, manifest)
                        return manifest
                    break
                pages_this_run += 1
                app["pages_fetched"] += 1
                app["reviews_returned"] += len(body["reviews"])
                app["total_matching_reported"] = body.get("total_matching", app.get("total_matching_reported"))
                app["error"] = None
                collected_at = utc_now()
                reasons = Counter(app["invalid_reasons"])
                for review in body["reviews"]:
                    try:
                        record = normalize_review(review, app, collected_at)
                    except ValueError as exc:
                        app["invalid_reviews_skipped"] += 1
                        reasons[str(exc)] += 1
                        continue
                    if record["review_id"] in seen:
                        app["duplicate_reviews_skipped"] += 1
                        continue
                    if app["records_saved"] >= config["reviews_per_game"]:
                        continue
                    seen.add(record["review_id"])
                    records.append(record)
                    app["records_saved"] += 1
                app["invalid_reasons"] = dict(reasons)
                previous_cursor = app["cursor"]
                next_cursor = body.get("cursor")
                if next_cursor:
                    app["cursor"] = next_cursor
                if app["records_saved"] >= config["reviews_per_game"]:
                    app["status"] = "target_reached"
                elif not body["reviews"]:
                    app["status"] = "exhausted"
                elif not next_cursor or next_cursor == previous_cursor:
                    app["status"] = "cursor_stalled"
                elif app["pages_fetched"] >= config["max_pages_per_game"]:
                    app["status"] = "page_limit"
                else:
                    app["status"] = "in_progress"
                checkpoint(output_dir, records, manifest)
                print(f"{app['game']}: {app['records_saved']}/{config['reviews_per_game']} reviews; "
                      f"page {app['pages_fetched']}; {app['status']}", flush=True)
                if app["status"] != "in_progress":
                    break
        manifest["status"] = ("completed" if all(app["status"] == "target_reached"
                                                  for app in manifest["apps"]) else "completed_with_limits")
        manifest["crawl_finished_utc"] = utc_now()
        checkpoint(output_dir, records, manifest)
    except KeyboardInterrupt:
        manifest["status"] = "interrupted"
        checkpoint(output_dir, records, manifest)
        print("Interrupted safely. Run the same command to resume.", flush=True)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--check-access", action="store_true", help="Only probe access; save no review text.")
    parser.add_argument("--max-pages-per-run", type=int, help="Pause safely after this many successful pages.")
    args = parser.parse_args()
    try:
        config = load_config(args.config)
        if args.max_pages_per_run is not None and args.max_pages_per_run < 1:
            raise ValueError("--max-pages-per-run must be positive.")
        client = SteamClient(config, args.output_dir / "steam_crawl_requests.jsonl")
        if args.check_access:
            return 0 if check_access(config, args.output_dir, client) else 1
        result = crawl(config, args.output_dir, client, args.max_pages_per_run)
        print(f"Crawl status: {result['status']}; saved {result['total_records']} reviews.")
        return 0 if result["status"] in {"completed", "paused_page_budget"} else 1
    except (ValueError, KeyError, OSError) as exc:
        print(f"Cannot run crawler: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
