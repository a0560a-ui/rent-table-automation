#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""募集賃料表ジェネレーター実行入口。"""

from __future__ import annotations

import argparse
from pathlib import Path

from config import MAX_FIXED_PAGE_SLOTS, OUTPUT_DIR
from imagekit import upload_fixed_page_set, upload_to_imagekit
from renderer import generate_image, render_placeholder_page
from sheets import fetch_sheets_data, load_property_data_from_sheets
from validator import validate_property_data


def run(
    sheets_data,
    prop_id,
    issue_date=None,
    output_dir=None,
    upload=False,
    brand_name="デュオメゾン",
    fixed_url_upload=False,
    max_slots=None,
):
    properties = load_property_data_from_sheets(sheets_data)
    success, message = validate_property_data(prop_id, properties)
    print(message)
    if not success:
        raise ValueError(message)

    pages = generate_image(prop_id, properties, issue_date=issue_date, output_dir=output_dir or OUTPUT_DIR)
    uploaded = []
    if fixed_url_upload:
        prop = properties[prop_id]
        placeholder_path = render_placeholder_page(
            prop["name"],
            Path(output_dir or OUTPUT_DIR) / f"{prop_id}_unused_page.png",
        )
        uploaded = upload_fixed_page_set(
            prop_id,
            pages,
            placeholder_paths=[placeholder_path],
            max_slots=max_slots or MAX_FIXED_PAGE_SLOTS,
        )
    elif upload:
        for page in pages:
            uploaded.append(upload_to_imagekit(page["path"], brand_name))
    return pages, uploaded


def run_from_google_sheets(
    prop_id,
    brand=None,
    spreadsheet_id=None,
    issue_date=None,
    output_dir=None,
    upload=False,
    brand_name=None,
    fixed_url_upload=False,
    max_slots=None,
):
    sheets_data = fetch_sheets_data(spreadsheet_id=spreadsheet_id, brand=brand)
    return run(
        sheets_data,
        prop_id,
        issue_date=issue_date,
        output_dir=output_dir,
        upload=upload,
        brand_name=brand_name or brand or "デュオメゾン",
        fixed_url_upload=fixed_url_upload,
        max_slots=max_slots,
    )


def sample_sheets_data():
    room_rows = [["物件ID", "階", "部屋番号", "タイプ", "間取り(自動)", "賃料(共益費込)", "状態", "備考", "区分"]]
    statuses = ["空室", "満室", "非募集"]
    type_keys = ["A", "B", "C", "D"]
    for floor in range(11, 0, -1):
        for index, type_key in enumerate(type_keys):
            room_rows.append(
                [
                    "P001",
                    str(floor),
                    f"{floor}{index + 1:02d}",
                    type_key,
                    "",
                    str(180000 + floor * 3000 + index * 12000),
                    statuses[(floor + index) % len(statuses)],
                    "",
                    "住戸",
                ]
            )
    return {
        "properties": [
            ["物件ID", "物件名（正式）", "略称（カンマ区切り）", "総戸数（自動計算）", "脚注1", "脚注2", "サブタイトル", "備考"],
            [
                "P001",
                "デュオメゾン品川戸越",
                "品川戸越,デュオメゾン品川戸越,戸越",
                "28",
                "※ 表示金額は税込・共益費込の月額賃料です。",
                "※ 別途、敷金・礼金・保証会社費用・火災保険料等が必要です。",
                "募 集 賃 料 表",
                "ペット可（小型犬1匹、猫2匹まで）",
            ],
        ],
        "types": [
            ["物件ID", "タイプ", "間取り", "専有面積(㎡)", "共益費", "表示順序", "表示ラベル"],
            ["P001", "A", "1DK", "33.34", "12000", "1", "A"],
            ["P001", "B", "1K", "24.65", "10000", "2", "B"],
            ["P001", "C", "1K", "24.65", "10000", "3", "C"],
            ["P001", "D", "2LDK", "51.3", "15000", "4", "D"],
        ],
        "rooms": room_rows,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="募集賃料表PNGを生成します")
    parser.add_argument("prop_id", nargs="?", default="P001")
    parser.add_argument("--brand", choices=["デュオメゾン", "DM", "デュオフラッツ", "DF"], default=None)
    parser.add_argument("--spreadsheet-id", default=None)
    parser.add_argument("--issue-date", default="2026年07月13日")
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    parser.add_argument("--upload", action="store_true")
    parser.add_argument("--fixed-url-upload", action="store_true", help="物件IDごとの固定ページURLへ上書きアップロードする")
    parser.add_argument("--max-slots", type=int, default=MAX_FIXED_PAGE_SLOTS)
    parser.add_argument("--sample", action="store_true", help="Google Sheetsではなく内蔵サンプルデータを使う")
    args = parser.parse_args()

    if args.sample or not (args.brand or args.spreadsheet_id):
        pages, uploaded = run(
            sample_sheets_data(),
            args.prop_id,
            issue_date=args.issue_date,
            output_dir=args.output_dir,
            upload=args.upload,
            fixed_url_upload=args.fixed_url_upload,
            max_slots=args.max_slots,
        )
    else:
        pages, uploaded = run_from_google_sheets(
            args.prop_id,
            brand=args.brand,
            spreadsheet_id=args.spreadsheet_id,
            issue_date=args.issue_date,
            output_dir=args.output_dir,
            upload=args.upload,
            fixed_url_upload=args.fixed_url_upload,
            max_slots=args.max_slots,
        )
    for page in pages:
        print(f"✅ 画像生成完了: {page['path']}")
    for item in uploaded:
        print(f"🔗 固定URL slot {item.get('slot', '-')}: {item}")
