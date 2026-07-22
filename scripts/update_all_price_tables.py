#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全物件の価格表を生成し、固定URL枠へアップロードする週次バッチ。"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import MAX_FIXED_PAGE_SLOTS, OUTPUT_DIR, SITE_DIR, public_site_base_url  # noqa: E402
from imagekit import upload_fixed_page_set  # noqa: E402
from reporting import build_public_update_report, write_json_csv_reports  # noqa: E402
from renderer import generate_image, render_placeholder_page  # noqa: E402
from sheets import fetch_sheets_data, load_property_data_from_sheets  # noqa: E402
from html_pages import build_property_page  # noqa: E402
from validator import housing_rooms, validate_property_data  # noqa: E402


def _target_property_ids(properties, requested_ids=None):
    requested = set(requested_ids or [])
    ids = []
    for prop_id, prop in properties.items():
        if requested and prop_id not in requested:
            continue
        if housing_rooms(prop):
            ids.append(prop_id)
    return sorted(ids)


def _write_reports(report_rows, report_dir):
    return write_json_csv_reports(report_rows, report_dir)


def update_brand(brand, args):
    sheets_data = fetch_sheets_data(brand=brand)
    properties = load_property_data_from_sheets(sheets_data)
    prop_ids = _target_property_ids(properties, args.property_ids)
    rows = []
    for prop_id in prop_ids:
        prop = properties[prop_id]
        output_dir = args.output_dir / brand / prop_id
        try:
            success, message = validate_property_data(prop_id, properties)
            if not success:
                raise ValueError(message)
            pages = generate_image(prop_id, properties, issue_date=args.issue_date, output_dir=output_dir)
            uploaded = []
            page_info = {"path": "", "url": "", "image_count": 0}
            if not args.dry_run:
                placeholder = render_placeholder_page(
                    prop["name"],
                    output_dir / f"{prop_id}_unused_page.png",
                )
                uploaded = upload_fixed_page_set(
                    prop_id,
                    pages,
                    placeholder_paths=[placeholder],
                    max_slots=args.max_slots,
                )
                active_urls = [item["url"] for item in uploaded if item["active"]]
                page_info = build_property_page(
                    prop_id,
                    prop["name"],
                    active_urls,
                    args.site_dir,
                    base_url=args.site_base_url,
                    issue_date=args.issue_date,
                    cache_buster=args.cache_buster,
                )
            rendered_room_count = sum(len(page["rendered_room_uids"]) for page in pages)
            rows.append(
                {
                    "brand": brand,
                    "property_id": prop_id,
                    "property_name": prop["name"],
                    "status": "success",
                    "page_count": len(pages),
                    "input_room_count": len(housing_rooms(prop)),
                    "rendered_room_count": rendered_room_count,
                    "split_direction": pages[0]["split_direction"] if pages else "",
                    "template": pages[0]["layout"]["template"] if pages else "",
                    "files": [page["path"] for page in pages],
                    "urls": [item["url"] for item in uploaded],
                    "page_path": page_info["path"],
                    "page_url": page_info["url"],
                    "error": "",
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "brand": brand,
                    "property_id": prop_id,
                    "property_name": prop.get("name", ""),
                    "status": "failed",
                    "page_count": 0,
                    "input_room_count": len(housing_rooms(prop)),
                    "rendered_room_count": 0,
                    "split_direction": "",
                    "template": "",
                    "files": [],
                    "urls": [],
                    "page_path": "",
                    "page_url": "",
                    "error": str(exc),
                }
            )
    return rows


def main():
    parser = argparse.ArgumentParser(description="全物件の価格表を週次更新します")
    parser.add_argument("--brands", nargs="+", default=["DM", "DF"], choices=["DM", "DF", "デュオメゾン", "デュオフラッツ"])
    parser.add_argument("--property-ids", nargs="*", default=None)
    parser.add_argument("--issue-date", default=datetime.now().strftime("%Y年%m月%d日"))
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR / "batch")
    parser.add_argument("--site-dir", type=Path, default=SITE_DIR)
    parser.add_argument("--site-base-url", default=public_site_base_url() or "")
    parser.add_argument("--report-dir", type=Path, default=PROJECT_ROOT / "reports")
    parser.add_argument("--max-slots", type=int, default=MAX_FIXED_PAGE_SLOTS)
    parser.add_argument("--cache-buster", default=datetime.now().strftime("%Y%m%d%H%M%S"))
    parser.add_argument("--dry-run", action="store_true", help="ImageKitへアップロードせず画像生成と検証だけ行う")
    parser.add_argument("--allow-partial", action="store_true", help="一部物件が失敗しても成功物件の公開処理を継続する")
    args = parser.parse_args()

    all_rows = []
    for brand in args.brands:
        all_rows.extend(update_brand(brand, args))
    json_path, csv_path = _write_reports(all_rows, args.report_dir)
    public_report = build_public_update_report(
        all_rows,
        args.site_dir,
        base_url=args.site_base_url,
        generated_at=datetime.now().strftime("%Y年%m月%d日 %H:%M"),
    )
    failures = [row for row in all_rows if row["status"] != "success"]
    print(
        json.dumps(
            {
                "total": len(all_rows),
                "failed": len(failures),
                "json": str(json_path),
                "csv": str(csv_path),
                "public_report": public_report,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if failures and not args.allow_partial:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
