#!/usr/bin/env python3
"""Replace 4.3 screenshots/metadata, attach VALID build 7, and resubmit.

The rejected submission is intentionally reused so its ready-for-review Unlock
IAP stays grouped with the corrected app version.

Dry-run status:
  python3 ios/scripts/resubmit_build7_after_43.py

Apply only after archive upload reports build 7 VALID:
  python3 ios/scripts/resubmit_build7_after_43.py --apply
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from ship_12_listing import upsert_listing  # noqa: E402
from ship_asc import api, load_token  # noqa: E402

APP_ID = "6800090745"
VERSION_ID = "e4dcdbc1-84d8-49ae-850a-e6c63227b0c5"
SUBMISSION_ID = "f3217cc9-eb33-4bf4-8076-ffdef07bc004"
BUILD_NUMBER = "7"

SCREEN_GROUPS = {
    "APP_IPHONE_65": (
        ROOT / "docs" / "asc_screens",
        (1284, 2778),
    ),
    "APP_IPAD_PRO_3GEN_129": (
        ROOT / "docs" / "asc_screens_ipad",
        (2048, 2732),
    ),
}


def require(status: int, body: object, action: str, allowed: tuple[int, ...] = (200, 201)) -> dict:
    if status not in allowed or not isinstance(body, dict):
        raise SystemExit(f"{action} failed: HTTP {status} {str(body)[:600]}")
    return body


def png_dimensions(path: Path) -> tuple[int, int]:
    raw = path.read_bytes()[:24]
    if len(raw) != 24 or raw[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit(f"not a PNG: {path}")
    return struct.unpack(">II", raw[16:24])


def screenshot_files(folder: Path, expected: tuple[int, int]) -> list[Path]:
    files = sorted(folder.glob(f"screen_*_{expected[0]}x{expected[1]}.png"))
    if len(files) < 3:
        raise SystemExit(f"need at least 3 screenshots in {folder}; found {len(files)}")
    for path in files:
        actual = png_dimensions(path)
        if actual != expected:
            raise SystemExit(f"{path.name}: expected {expected}, got {actual}")
    return files[:10]


def en_us_localization(token: str) -> str:
    status, body = api(
        token,
        "GET",
        f"/v1/appStoreVersions/{VERSION_ID}/appStoreVersionLocalizations?limit=20",
    )
    body = require(status, body, "list localizations")
    for item in body.get("data") or []:
        if (item.get("attributes") or {}).get("locale") == "en-US":
            return item["id"]
    raise SystemExit("en-US localization missing")


def screenshot_sets(token: str, localization_id: str) -> list[dict]:
    status, body = api(
        token,
        "GET",
        f"/v1/appStoreVersionLocalizations/{localization_id}/appScreenshotSets?limit=50",
    )
    body = require(status, body, "list screenshot sets")
    return body.get("data") or []


def ensure_set(token: str, localization_id: str, display_type: str) -> str:
    for item in screenshot_sets(token, localization_id):
        if (item.get("attributes") or {}).get("screenshotDisplayType") == display_type:
            return item["id"]
    status, body = api(
        token,
        "POST",
        "/v1/appScreenshotSets",
        {
            "data": {
                "type": "appScreenshotSets",
                "attributes": {"screenshotDisplayType": display_type},
                "relationships": {
                    "appStoreVersionLocalization": {
                        "data": {
                            "type": "appStoreVersionLocalizations",
                            "id": localization_id,
                        }
                    }
                },
            }
        },
    )
    body = require(status, body, f"create {display_type} screenshot set")
    return body["data"]["id"]


def clear_set(token: str, set_id: str) -> None:
    status, body = api(token, "GET", f"/v1/appScreenshotSets/{set_id}/appScreenshots?limit=20")
    body = require(status, body, "list old screenshots")
    for item in body.get("data") or []:
        delete_status, delete_body = api(token, "DELETE", f"/v1/appScreenshots/{item['id']}")
        if delete_status != 204:
            raise SystemExit(
                f"delete screenshot {item['id']} failed: HTTP {delete_status} {str(delete_body)[:300]}"
            )


def upload_screenshot(token: str, set_id: str, path: Path) -> None:
    data = path.read_bytes()
    status, body = api(
        token,
        "POST",
        "/v1/appScreenshots",
        {
            "data": {
                "type": "appScreenshots",
                "attributes": {"fileName": path.name, "fileSize": len(data)},
                "relationships": {
                    "appScreenshotSet": {
                        "data": {"type": "appScreenshotSets", "id": set_id}
                    }
                },
            }
        },
    )
    body = require(status, body, f"reserve {path.name}")
    resource = body["data"]
    for operation in (resource.get("attributes") or {}).get("uploadOperations") or []:
        offset = int(operation["offset"])
        length = int(operation["length"])
        request = urllib.request.Request(
            operation["url"],
            data=data[offset : offset + length],
            method=operation["method"],
        )
        for header in operation.get("requestHeaders") or []:
            request.add_header(header["name"], header["value"])
        with urllib.request.urlopen(request, timeout=120) as response:
            if not 200 <= response.status < 300:
                raise SystemExit(f"asset upload failed: {path.name} HTTP {response.status}")

    status, body = api(
        token,
        "PATCH",
        f"/v1/appScreenshots/{resource['id']}",
        {
            "data": {
                "type": "appScreenshots",
                "id": resource["id"],
                "attributes": {
                    "uploaded": True,
                    "sourceFileChecksum": hashlib.md5(data).hexdigest(),
                },
            }
        },
    )
    require(status, body, f"commit {path.name}", allowed=(200,))
    print("uploaded", path.name)


def replace_screenshots(token: str) -> None:
    localization_id = en_us_localization(token)
    for display_type, (folder, expected) in SCREEN_GROUPS.items():
        files = screenshot_files(folder, expected)
        set_id = ensure_set(token, localization_id, display_type)
        clear_set(token, set_id)
        for path in files:
            upload_screenshot(token, set_id, path)


def valid_build_7(token: str) -> dict:
    status, body = api(
        token,
        "GET",
        f"/v1/builds?filter[app]={APP_ID}&filter[version]={BUILD_NUMBER}&limit=10",
    )
    body = require(status, body, "find build 7")
    for build in body.get("data") or []:
        if (build.get("attributes") or {}).get("processingState") == "VALID":
            return build
    raise SystemExit("build 7 is not VALID yet")


def attach_build(token: str, build: dict) -> None:
    status, body = api(
        token,
        "PATCH",
        f"/v1/appStoreVersions/{VERSION_ID}",
        {
            "data": {
                "type": "appStoreVersions",
                "id": VERSION_ID,
                "relationships": {
                    "build": {
                        "data": {"type": "builds", "id": build["id"]}
                    }
                },
            }
        },
    )
    require(status, body, "attach build 7", allowed=(200,))
    print("attached build", BUILD_NUMBER, build["id"])


def resubmit_unresolved(token: str) -> None:
    status, submission = api(token, "GET", f"/v1/reviewSubmissions/{SUBMISSION_ID}")
    submission = require(status, submission, "read rejected submission")
    state = (submission["data"].get("attributes") or {}).get("state")
    if state != "UNRESOLVED_ISSUES":
        raise SystemExit(f"expected UNRESOLVED_ISSUES, got {state}")

    status, items = api(token, "GET", f"/v1/reviewSubmissions/{SUBMISSION_ID}/items?limit=20")
    items = require(status, items, "list rejected submission items")
    rows = items.get("data") or []
    rejected = [row for row in rows if (row.get("attributes") or {}).get("state") == "REJECTED"]
    ready = [row for row in rows if (row.get("attributes") or {}).get("state") == "READY_FOR_REVIEW"]
    if len(rejected) != 1 or not ready:
        raise SystemExit(
            f"unexpected submission items: rejected={len(rejected)} ready={len(ready)}"
        )

    rejected_id = rejected[0]["id"]
    status, body = api(
        token,
        "PATCH",
        f"/v1/reviewSubmissionItems/{rejected_id}",
        {
            "data": {
                "type": "reviewSubmissionItems",
                "id": rejected_id,
                "attributes": {"resolved": True},
            }
        },
    )
    require(status, body, "mark rejected app item resolved", allowed=(200,))

    status, body = api(
        token,
        "PATCH",
        f"/v1/reviewSubmissions/{SUBMISSION_ID}",
        {
            "data": {
                "type": "reviewSubmissions",
                "id": SUBMISSION_ID,
                "attributes": {"submitted": True},
            }
        },
    )
    body = require(status, body, "resubmit app and Unlock", allowed=(200,))
    print("submission", (body["data"].get("attributes") or {}).get("state"))


def status_snapshot(token: str) -> None:
    files = {
        kind: [path.name for path in screenshot_files(folder, expected)]
        for kind, (folder, expected) in SCREEN_GROUPS.items()
    }
    status, submission = api(token, "GET", f"/v1/reviewSubmissions/{SUBMISSION_ID}")
    submission = require(status, submission, "read submission")
    status, builds = api(
        token,
        "GET",
        f"/v1/builds?filter[app]={APP_ID}&filter[version]={BUILD_NUMBER}&limit=10",
    )
    builds = require(status, builds, "read build 7")
    print(
        json.dumps(
            {
                "submissionState": (submission["data"].get("attributes") or {}).get("state"),
                "build7": [
                    {
                        "id": row["id"],
                        "processingState": (row.get("attributes") or {}).get("processingState"),
                    }
                    for row in builds.get("data") or []
                ],
                "screenshots": files,
            },
            indent=2,
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    token = load_token()
    if not args.apply:
        status_snapshot(token)
        return 0

    build = valid_build_7(token)
    upsert_listing(token, VERSION_ID)
    token = load_token()
    replace_screenshots(token)
    token = load_token()
    attach_build(token, build)
    time.sleep(5)
    token = load_token()
    resubmit_unresolved(token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
