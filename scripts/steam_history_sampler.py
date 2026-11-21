"""User-history sampling with train-only cohort rules and bounded public collection.

Requires requirements-sampling.txt. Private profile lookup IDs live only in memory
and Windows DPAPI-encrypted state outside the repository, never in public outputs.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import ctypes
from datetime import datetime, timedelta, timezone
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
import urllib.robotparser

from bs4 import BeautifulSoup
from langdetect import DetectorFactory, LangDetectException, detect_langs

from steam_crawler import (ENDPOINT, ROOT, FetchError, SteamClient, atomic_text,
                           fingerprint, load_config, read_jsonl, utc_now, write_json)

COMMUNITY = "https://steamcommunity.com"
DetectorFactory.seed = 42


def epoch(value):
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())


def priority_users(seeds, settings):
    def key(user):
        degree = (len(seeds[user].get("training_seed_items", [seeds[user]["seed_app_id"]]))
                  if settings.get("seed_priority") == "training_seed_degree_then_hash" else 0)
        return (-degree, hashlib.sha256((settings["selection_seed"] + user).encode()).hexdigest())
    return sorted(seeds, key=key)


def dpapi(data, decrypt=False):
    """Account-bound encrypted local resume state; no plaintext IDs on disk."""
    if os.name != "nt":
        raise RuntimeError("Private resume state requires Windows DPAPI in this implementation.")

    class Blob(ctypes.Structure):
        _fields_ = [("size", ctypes.c_ulong), ("data", ctypes.POINTER(ctypes.c_ubyte))]

    backing = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(backing, ctypes.POINTER(ctypes.c_ubyte)))
    target = Blob()
    crypt = ctypes.WinDLL("crypt32", use_last_error=True)
    function = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    function.restype = ctypes.c_int
    function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                         ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(Blob)]
    if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(target.data, target.size)
    finally:
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.LocalFree.argtypes = [ctypes.c_void_p]
        kernel.LocalFree.restype = ctypes.c_void_p
        kernel.LocalFree(target.data)


def save_private(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    encrypted = dpapi(json.dumps(state).encode("utf-8"))
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(encrypted)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def write_seed_manifest(path, value):
    """Keep each public seed on one reviewable JSON line inside a JSON object."""
    header = {key: item for key, item in value.items() if key != "seeds"}
    prefix = json.dumps(header, ensure_ascii=False, indent=2).rstrip()[:-1].rstrip()
    entries = ",\n".join("    " + json.dumps(item, ensure_ascii=False, separators=(",", ":")) for item in value["seeds"])
    atomic_text(path, prefix + ',\n  "seeds": [\n' + entries + '\n  ]\n}\n')


def load_settings(path):
    settings = json.loads(Path(path).read_text(encoding="utf-8"))
    catalogue = load_config(ROOT / settings["catalogue_config"])
    metadata = json.loads((ROOT / settings["catalogue_metadata"]).read_text(encoding="utf-8"))
    if metadata["config_sha256"] != fingerprint(catalogue):
        raise ValueError("Catalogue metadata/config mismatch")
    replacements = {item["replace_app_id"]: item for item in settings["catalogue_replacements"]}
    verified = {app["app_id"] for app in metadata["apps"] if app.get("is_game") is True}
    apps = []
    for app in catalogue["apps"]:
        if app["app_id"] in replacements:
            replacement = replacements[app["app_id"]]
            apps.append({"app_id": replacement["app_id"], "game": replacement["game"],
                         "metadata_status": "needs_live_verification",
                         "replaces_unverified_app": app["app_id"]})
        elif app["app_id"] in verified:
            apps.append({**app, "metadata_status": "verified_existing_audit"})
        else:
            raise ValueError("Unverified app without a declared replacement")
    if len(apps) != 100 or len({app["app_id"] for app in apps}) != 100:
        raise ValueError("Exactly 100 distinct catalogue apps are required")
    if not (epoch(settings["observation_start_utc"]) < epoch(settings["validation_cutoff_utc"]) <
            epoch(settings["test_cutoff_utc"]) < epoch(settings["observation_end_utc"])):
        raise ValueError("Invalid chronological windows")
    if not 1 <= settings["seed_reviews_per_game"] <= 100:
        raise ValueError("Seed page must contain 1..100 reviews")
    if settings["request_interval_seconds"] < 1 or settings["minimum_positive_training_games"] < 1:
        raise ValueError("Invalid rate/history rule")
    return settings, catalogue, apps


def parse_day(value, collected_at):
    value = value.strip().strip(".").replace(",", "")
    if not re.search(r"\b\d{4}\b", value):
        value += " " + str(datetime.fromisoformat(collected_at.replace("Z", "+00:00")).year)
    for pattern in ["%d %B %Y", "%d %b %Y", "%B %d %Y", "%b %d %Y"]:
        try:
            result = datetime.strptime(value, pattern).replace(tzinfo=timezone.utc)
            if result > datetime.fromisoformat(collected_at.replace("Z", "+00:00")) + timedelta(days=1):
                raise ValueError("Date in future; do not guess a different year")
            return int(result.timestamp())
        except ValueError:
            pass
    raise ValueError("Unrecognized public review date")


def parse_profile(html, user_hash, titles, collected_at, settings):
    soup = BeautifulSoup(html, "html.parser")
    boxes = soup.select(".review_box")
    info = soup.select_one(".workshopBrowsePagingInfo")
    info_text = info.get_text(" ", strip=True).replace(",", "") if info else ""
    total_match = re.search(r"of\s+(\d+)\s+entr", info_text, re.I)
    total = int(total_match.group(1)) if total_match else None
    page_numbers = [int(number) for link in soup.select(".workshopBrowsePagingControls a[href]")
                    for number in re.findall(r"[?&]p=(\d+)", link["href"])]
    rows, problems = [], Counter()
    for box in boxes:
        app_match = next((re.search(r"/app/(\d+)", link.get("href", ""))
                          for link in box.select(".leftcol a[href]")
                          if re.search(r"/app/(\d+)", link.get("href", ""))), None)
        if not app_match:
            problems["unknown_app_id"] += 1
            continue
        app_id = app_match.group(1)
        if app_id not in titles:
            continue
        vote = box.select_one(".vote_header .title")
        posted = box.select_one(".posted")
        content = box.select_one(".content")
        recommendation = box.find(id=re.compile(r"^RecommendationVoteUpBtn[0-9]+$"))
        try:
            if vote is None or posted is None or content is None or recommendation is None:
                raise ValueError("Missing required public review elements")
            label = vote.get_text(" ", strip=True)
            if label not in {"Recommended", "Not Recommended"}:
                raise ValueError("Unknown recommendation label")
            dates = posted.get_text(" ", strip=True)
            creation = re.search(r"Posted\s*:?\s*(\d{1,2}\s+[A-Za-z]+(?:,?\s+\d{4})?)", dates)
            updated = re.search(r"Last edited\s*:?\s*(\d{1,2}\s+[A-Za-z]+(?:,?\s+\d{4})?)", dates)
            if creation is None:
                raise ValueError("Missing creation date")
            created = parse_day(creation.group(1), collected_at)
            edited = parse_day(updated.group(1), collected_at) if updated else created
            if edited < created:
                raise ValueError("Edit date before creation")
            review_id = re.sub(r"\D", "", recommendation["id"])
            rows.append({"review_id": review_id, "user_id": user_hash, "item_id": app_id,
                         "item_title": titles[app_id], "timestamp": created,
                         "timestamp_updated": edited, "timestamp_precision": "day",
                         "event_time_lower_utc": created - 14 * 3600,
                         "available_after_utc": max(created, edited) + settings["community_date_upper_bound_hours"] * 3600,
                         "edit_time_status": "shown_on_public_page" if updated else "not_shown_assumed_unedited",
                         "crawl_time_utc": collected_at, "source_feedback": label == "Recommended",
                         "positive_interaction": label == "Recommended", "title": "",
                         "text": content.get_text("\n", strip=True), "language": "unknown",
                         "helpful_votes": None, "source_url": COMMUNITY,
                         "source_method": "public_profile_review_listing"})
        except ValueError:
            problems["unparsed_in_catalog_review"] += 1
    return {"rows": rows, "boxes": len(boxes), "total": total,
            "page_numbers": page_numbers, "problems": dict(problems),
            "available": bool(boxes) or total == 0}


def quality(row, settings):
    tokens = len(row["text"].split())
    result = {"review_id": row["review_id"], "tokens": tokens,
              "blank": not row["text"].strip(), "short": tokens < settings["minimum_opinion_tokens"],
              "detected_language": "unknown", "language_score": None,
              "language_model": "langdetect-1.0.9; deterministic seed 42; score is not calibrated",
              "opinion_text_eligible": False}
    if not result["short"]:
        try:
            prediction = detect_langs(row["text"])[0]
            result["detected_language"] = "english" if prediction.lang == "en" else prediction.lang
            result["language_score"] = round(prediction.prob, 6)
            result["opinion_text_eligible"] = (prediction.lang == "en" and
                prediction.prob >= settings["minimum_english_detector_score"])
        except LangDetectException:
            pass
    return result


def before(row, cutoff):
    return row["available_after_utc"] < cutoff


def event_upper(row, settings):
    return row["timestamp"] if row["timestamp_precision"] == "second" else row["timestamp"] + settings["community_date_upper_bound_hours"] * 3600


def text_before(row, cutoff):
    return row.get("text_available_after_utc", row["available_after_utc"]) < cutoff


def anchor_seed_timestamps(row, seed, settings):
    """Use exact API times for the matching seed's interaction, not its UI text."""
    retained = seed.get("training_seed_reviews")
    if retained:
        seed = next((item for item in retained if item["seed_review_id"] == row["review_id"]), {})
    if not all(key in seed for key in ["seed_timestamp", "seed_updated", "seed_app_id"]):
        return row
    if (row["review_id"] != seed["seed_review_id"] or row["item_id"] != seed["seed_app_id"] or
            not row["positive_interaction"]):
        return row
    if row["timestamp_precision"] == "second":
        return row
    margin = settings["community_date_upper_bound_hours"] * 3600
    if not (row["event_time_lower_utc"] <= seed["seed_timestamp"] < row["timestamp"] + margin and
            row["timestamp_updated"] - 14 * 3600 <= seed["seed_updated"] < row["timestamp_updated"] + margin):
        return row
    result = row.copy()
    result.update(timestamp=seed["seed_timestamp"], timestamp_updated=seed["seed_updated"],
                  event_time_lower_utc=seed["seed_timestamp"], timestamp_precision="second",
                  text_available_after_utc=row["available_after_utc"], available_after_utc=seed["seed_updated"],
                  source_method="public_profile_listing_with_api_seed_timestamps")
    return result


def training_games(rows, settings):
    start, cutoff = epoch(settings["observation_start_utc"]), epoch(settings["validation_cutoff_utc"])
    return {row["item_id"] for row in rows if row["positive_interaction"] and
            row["event_time_lower_utc"] >= start and event_upper(row, settings) < cutoff and before(row, cutoff)}


class HistoryClient(SteamClient):
    def __init__(self, config, log_path, settings):
        super().__init__(config, log_path)
        self.settings = settings
        self.robot_rules = None

    def budget(self):
        return len(read_jsonl(self.log_path)) < self.settings["max_http_attempts"]

    def before_attempt(self):
        if not self.budget():
            raise FetchError("HTTP attempt budget exhausted")

    def fetch(self, params, purpose="seed_discovery"):
        return super().fetch(params, purpose)

    def get(self, url, purpose, user_hash=None, page=None):
        for attempt in range(self.settings["max_retries"] + 1):
            if not self.budget():
                raise FetchError("HTTP attempt budget exhausted")
            if self.last_request is not None:
                time.sleep(max(0, self.settings["request_interval_seconds"] - (time.monotonic() - self.last_request)))
            self.last_request = time.monotonic()
            event = {"requested_at_utc": utc_now(), "purpose": purpose, "user_id": user_hash,
                     "page": page, "attempt": attempt + 1}
            status, delay, retryable = None, self.settings["backoff_seconds"] * 2 ** attempt, False
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent":
                        "WebMiningCapstone/0.2 (bounded public review history study)"}),
                        timeout=self.settings["timeout_seconds"]) as response:
                    status = response.status
                    raw = response.read(4 * 1024 * 1024 + 1)
                if len(raw) > 4 * 1024 * 1024:
                    raise ValueError("Oversized response")
                event.update(http_status=status, outcome="success")
                self.log(event)
                return raw
            except urllib.error.HTTPError as exc:
                status = exc.code
                retryable = status in {429, 500, 502, 503, 504}
                if exc.headers and exc.headers.get("Retry-After"):
                    try:
                        delay = max(delay, float(exc.headers["Retry-After"]))
                    except ValueError:
                        retryable = False  # Do not retry early on an unparsed server date.
                exc.close()
            except (urllib.error.URLError, TimeoutError, OSError):
                retryable = True
            except ValueError:
                pass
            retry = retryable and attempt < self.settings["max_retries"] and delay <= 60
            event.update(http_status=status, outcome="failure", will_retry=retry,
                         wait_seconds=delay if retry else 0)
            self.log(event)
            if not retry:
                raise FetchError(f"Public source request failed (status {status})", status)
            time.sleep(delay)

    def check_robots(self):
        raw = self.get(COMMUNITY + "/robots.txt", "community_robots")
        rules = urllib.robotparser.RobotFileParser()
        rules.parse(raw.decode("utf-8", "replace").splitlines())
        self.robot_rules = rules
        return raw.decode("utf-8", "replace")

    def profile(self, steam_id, user_hash, page):
        url = COMMUNITY + "/profiles/" + steam_id + "/recommended/?" + urllib.parse.urlencode({"p": page, "l": "english"})
        if self.robot_rules is None or not self.robot_rules.can_fetch("WebMiningCapstone", url):
            raise FetchError("Community robots rules do not allow this profile path")
        return self.get(url, "public_history", user_hash, page).decode("utf-8", "replace")


def checkpoint(output, private_path, state, records, settings):
    data_path = output / "discovered_reviews.jsonl"
    atomic_text(data_path, "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records))
    save_private(private_path, state)
    public = {key: value for key, value in state.items() if key not in {"seeds", "profiles"}}
    public["seed_users"] = len(state["seeds"])
    public["profiles"] = {key: value for key, value in state["profiles"].items()}
    public["record_count"] = len(records)
    public["data_sha256"] = hashlib.sha256(data_path.read_bytes()).hexdigest()
    public["last_saved_utc"] = utc_now()
    public["private_state"] = "Windows DPAPI encrypted, outside repository, same account/machine required for resume"
    public["source_url_policy"] = "Profile URLs/usernames and raw SteamIDs are never published; source_url is the platform root, per-review stable key is review_id. Date precision is one day with a conservative +38h availability bound."
    write_json(output / "sampling_manifest.json", public)


def run(settings_path, output, max_profiles_per_run=None):
    settings, api_config, apps = load_settings(settings_path)
    api_config.update({key: settings[key] for key in ["request_interval_seconds", "timeout_seconds", "max_retries", "backoff_seconds"]})
    signature = fingerprint({"settings": settings, "apps": apps})
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    private_path = Path(os.environ.get("LOCALAPPDATA", "")) / "WebMining" / "private_sampling" / (signature + ".dpapi")
    if private_path.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("Private state must be outside the repository")
    if private_path.exists():
        state = json.loads(dpapi(private_path.read_bytes(), decrypt=True))
        if state["output_directory_sha256"] != hashlib.sha256(str(output).encode()).hexdigest():
            raise ValueError("Private resume state belongs to a different output directory")
    else:
        if (output / "sampling_manifest.json").exists() or (output / "discovered_reviews.jsonl").exists():
            raise ValueError("Public output exists but private resume state is missing")
        state = {"dataset_version": settings["dataset_version"], "settings": settings,
                 "config_sha256": signature, "started_at_utc": utc_now(), "status": "discovering_seeds",
                 "output_directory_sha256": hashlib.sha256(str(output).encode()).hexdigest(),
                 "apps": apps, "seed_app_index": 0, "seed_records_seen": 0,
                 "seed_records_excluded_after_edit": 0, "seeds": {}, "profiles": {}}
    records = read_jsonl(output / "discovered_reviews.jsonl")
    if (output / "sampling_manifest.json").exists():
        public = json.loads((output / "sampling_manifest.json").read_text(encoding="utf-8"))
        if public["config_sha256"] != signature:
            raise ValueError("Sampling config changed; use a new version")
    client = HistoryClient(api_config, output / "sampling_requests.jsonl", settings)
    titles = {str(app["app_id"]): app["game"] for app in apps}
    seen = {row["review_id"] for row in records}
    state.pop("last_error", None)
    try:
        for app in state["apps"]:
            if app["metadata_status"] == "needs_live_verification":
                url = "https://store.steampowered.com/api/appdetails?" + urllib.parse.urlencode({"appids": app["app_id"], "filters": "basic"})
                item = json.loads(client.get(url, "replacement_metadata")).get(str(app["app_id"]), {})
                data = item.get("data", {})
                if item.get("success") is not True or data.get("type") != "game":
                    raise FetchError("Replacement game metadata could not be verified")
                app.update(metadata_status="verified_live", metadata_url=url,
                           official_title=data["name"], metadata_checked_at_utc=utc_now())
        start, cutoff = epoch(settings["observation_start_utc"]), epoch(settings["validation_cutoff_utc"])
        while state["seed_app_index"] < len(apps):
            app = apps[state["seed_app_index"]]
            params = {"appid": app["app_id"], "filter": 1, "languages": ["english"],
                      "review_type": 1, "purchase_type": 1, "num_per_page": settings["seed_reviews_per_game"],
                      "cursor": "*", "filter_offtopic_activity": True,
                      "date_range_start": start, "date_range_end": cutoff - 1}
            body = client.fetch(params)
            for review in body["reviews"]:
                state["seed_records_seen"] += 1
                if (type(review.get("timestamp_created")) is not int or
                        type(review.get("timestamp_updated")) is not int or
                        not start <= review["timestamp_created"] < cutoff or
                        not review["timestamp_created"] <= review["timestamp_updated"] < cutoff or
                        review.get("voted_up") is not True):
                    state["seed_records_excluded_after_edit"] += 1
                    continue
                steam_id = str(review.get("author", {}).get("steamid", ""))
                if not re.fullmatch(r"[0-9]{17}", steam_id):
                    continue
                hashed = hashlib.sha256(steam_id.encode()).hexdigest()
                seed = state["seeds"].setdefault(hashed, {"steam_id": steam_id,
                    "seed_review_id": str(review["recommendationid"]), "seed_app_id": str(app["app_id"]),
                    "seed_timestamp": review["timestamp_created"], "seed_updated": review["timestamp_updated"],
                    "training_seed_items": []})
                items = seed.setdefault("training_seed_items", [seed["seed_app_id"]])
                if str(app["app_id"]) not in items:
                    items.append(str(app["app_id"]))
                evidence = seed.setdefault("training_seed_reviews", [])
                if not any(item["seed_review_id"] == str(review["recommendationid"]) for item in evidence):
                    evidence.append({"seed_review_id": str(review["recommendationid"]),
                                     "seed_app_id": str(app["app_id"]),
                                     "seed_timestamp": review["timestamp_created"],
                                     "seed_updated": review["timestamp_updated"]})
            state["seed_app_index"] += 1
            checkpoint(output, private_path, state, records, settings)
            print(f"Seed discovery {state['seed_app_index']}/100; {len(state['seeds'])} hashed candidates.", flush=True)
        write_seed_manifest(output / "seed_manifest.json", {"selection_seed": settings["selection_seed"],
                   "validation_cutoff_utc": settings["validation_cutoff_utc"],
                   "seeds": [{"user_id": key, **{k: v for k, v in value.items() if k != "steam_id"}}
                             for key, value in sorted(state["seeds"].items())]})
        robots = client.check_robots()
        atomic_text(output / "community_robots.txt", robots)
        state["status"] = "collecting_histories"
        priority = priority_users(state["seeds"], settings)
        processed = 0
        for user in priority[:settings["max_profile_users"]]:
            existing = state["profiles"].get(user)
            if existing and existing["status"] != "in_progress":
                continue
            if max_profiles_per_run is not None and processed >= max_profiles_per_run:
                state["status"] = "paused_profile_budget"
                break
            profile = state["profiles"].setdefault(user, {"status": "in_progress", "page": 1,
                "boxes_seen": 0, "records_saved": 0, "parse_problems": {}, "seed_review_id": state["seeds"][user]["seed_review_id"]})
            while profile["page"] <= settings["max_profile_pages"]:
                parsed = parse_profile(client.profile(state["seeds"][user]["steam_id"], user, profile["page"]),
                                       user, titles, utc_now(), settings)
                if not parsed["available"]:
                    profile["status"] = "unavailable"
                    break
                profile["boxes_seen"] += parsed["boxes"]
                problems = Counter(profile["parse_problems"])
                problems.update(parsed["problems"])
                profile["parse_problems"] = dict(problems)
                for row in parsed["rows"]:
                    row = anchor_seed_timestamps(row, state["seeds"][user], settings)
                    if row["review_id"] not in seen:
                        records.append(row)
                        seen.add(row["review_id"])
                        profile["records_saved"] += 1
                if (profile["page"] == 1 and parsed["total"] is not None and parsed["boxes"] and
                        parsed["total"] > parsed["boxes"] * settings["max_profile_pages"]):
                    # The same page cap would exclude this profile eventually;
                    # avoid fetching pages that cannot produce a complete history.
                    profile["status"] = "truncated_page_limit"
                    break
                if parsed["total"] is not None and profile["boxes_seen"] >= parsed["total"]:
                    profile["status"] = "complete" if not problems else "incomplete_parse"
                    break
                if not parsed["page_numbers"] and parsed["boxes"] < 10:
                    profile["status"] = "complete" if not problems else "incomplete_parse"
                    break
                profile["page"] += 1
                checkpoint(output, private_path, state, records, settings)
            if profile["status"] == "in_progress":
                profile["status"] = "truncated_page_limit"
            user_rows = [row for row in records if row["user_id"] == user]
            profile["positive_training_games"] = len(training_games(user_rows, settings))
            profile["seed_review_observed_in_training"] = any(
                row["review_id"] == profile["seed_review_id"] and row["positive_interaction"] and
                before(row, epoch(settings["validation_cutoff_utc"])) for row in user_rows)
            profile["train_eligible"] = (profile["status"] == "complete" and
                profile["positive_training_games"] >= settings["minimum_positive_training_games"] and
                profile["seed_review_observed_in_training"])
            processed += 1
            checkpoint(output, private_path, state, records, settings)
            print(f"Profiles this run {processed}: {profile['status']}; saved in-catalog reviews {len(records)}.", flush=True)
            if sum(item.get("train_eligible", False) for item in state["profiles"].values()) >= settings["target_cohort_users"]:
                state["status"] = "training_cohort_target_reached"
                break
        else:
            state["status"] = "profile_frame_exhausted_or_user_cap"
        checkpoint(output, private_path, state, records, settings)
    except (FetchError, KeyboardInterrupt) as exc:
        state["status"] = "paused_source_or_request_budget" if isinstance(exc, FetchError) else "interrupted"
        state["last_error"] = str(exc) if isinstance(exc, FetchError) else "KeyboardInterrupt"
        checkpoint(output, private_path, state, records, settings)
        print(state["status"], flush=True)
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/steam_history_sampling_v3.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs/steam_history_v3")
    parser.add_argument("--max-profiles-per-run", type=int)
    args = parser.parse_args()
    if args.max_profiles_per_run is not None and args.max_profiles_per_run < 1:
        parser.error("--max-profiles-per-run must be positive")
    result = run(args.config, args.output_dir, args.max_profiles_per_run)
    if result["status"] == "paused_source_or_request_budget":
        raise SystemExit(1)
    if result["status"] == "interrupted":
        raise SystemExit(130)


if __name__ == "__main__":
    main()
