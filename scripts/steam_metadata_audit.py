"""Bounded metadata check for the configured games using Steam's public store."""

import argparse
import json
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request

from steam_crawler import ROOT, USER_AGENT, fingerprint, load_config, utc_now, write_json


def audit(config, output_dir):
    path = Path(output_dir) / "steam_metadata_audit.json"
    if path.exists():
        result = json.loads(path.read_text(encoding="utf-8"))
        if result["config_sha256"] != fingerprint(config):
            raise ValueError("Metadata config differs; use a new output directory.")
    else:
        result = {"started_at_utc": utc_now(), "config_sha256": fingerprint(config),
                  "source": "https://store.steampowered.com/api/appdetails",
                  "purpose": "Verify configured IDs are games; this is not a full category/metadata crawl.",
                  "apps": []}
    existing = {app["app_id"]: app for app in result["apps"]}
    for app in config["apps"]:
        if existing.get(app["app_id"], {}).get("status") == "success":
            continue
        if result["apps"]:
            time.sleep(config["request_interval_seconds"])
        url = result["source"] + "?" + urllib.parse.urlencode({"appids": app["app_id"], "filters": "basic"})
        entry = {"app_id": app["app_id"], "configured_title": app["game"],
                 "requested_at_utc": utc_now(), "source_url": url}
        blocked = False
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": USER_AGENT}),
                                        timeout=config["timeout_seconds"]) as response:
                entry["http_status"] = response.status
                raw = response.read(4 * 1024 * 1024 + 1)
            if len(raw) > 4 * 1024 * 1024:
                raise ValueError("Oversized response")
            item = json.loads(raw).get(str(app["app_id"]), {})
            data = item.get("data", {})
            if item.get("success") is not True or data.get("steam_appid") != app["app_id"]:
                raise ValueError("Missing app metadata")
            entry.update(status="success", official_title=data.get("name"),
                         app_type=data.get("type"), is_game=data.get("type") == "game")
        except urllib.error.HTTPError as exc:
            entry.update(status="failed", http_status=exc.code, error=f"HTTP {exc.code}")
            blocked = exc.code in {401, 403, 429}
            exc.close()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            entry.update(status="failed", error=type(exc).__name__)
            blocked = True
        except (ValueError, TypeError, AttributeError) as exc:
            entry.update(status="failed", error=f"Invalid metadata ({type(exc).__name__})")
        existing[app["app_id"]] = entry
        result["apps"] = [existing[item["app_id"]] for item in config["apps"] if item["app_id"] in existing]
        result["last_saved_utc"] = utc_now()
        write_json(path, result)
        print(f"{app['game']}: metadata {entry['status']}; type={entry.get('app_type', 'unknown')}", flush=True)
        if blocked:
            break
    result["successful_apps"] = sum(app["status"] == "success" for app in result["apps"])
    result["verified_game_apps"] = sum(app.get("is_game") is True for app in result["apps"])
    result["status"] = ("completed" if result["verified_game_apps"] == len(config["apps"]) else "incomplete")
    result["finished_at_utc"] = utc_now()
    write_json(path, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/steam_crawl_v0.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs")
    args = parser.parse_args()
    result = audit(load_config(args.config), args.output_dir)
    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
