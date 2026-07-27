#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Google Sheetsデータ変換。

既存の sheets_data 入力構造と戻り値構造を維持する。
"""

from __future__ import annotations

import json

from config import (
    BRAND_SPREADSHEET_IDS,
    SHEET_TITLES,
    google_application_credentials,
    google_service_account_json,
    google_spreadsheet_id,
)


def resolve_spreadsheet_id(brand_or_id=None):
    if brand_or_id in BRAND_SPREADSHEET_IDS:
        return BRAND_SPREADSHEET_IDS[brand_or_id]
    if brand_or_id:
        return brand_or_id
    spreadsheet_id = google_spreadsheet_id()
    if spreadsheet_id:
        return spreadsheet_id
    raise RuntimeError("ブランド名、spreadsheet_id、または GOOGLE_SPREADSHEET_ID を指定してください")


def normalize_type_key(value):
    """タイプキーの見た目が同じ引用符ゆれを吸収する。"""
    return str(value or "").strip().replace("'", "’").replace("‘", "’").replace("`", "’")


def _authorize_gspread():
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError as exc:
        raise RuntimeError("Google Sheets取得には gspread と google-auth が必要です") from exc

    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    service_account_json = google_service_account_json()
    credentials_path = google_application_credentials()
    if service_account_json:
        info = json.loads(service_account_json)
        credentials = Credentials.from_service_account_info(info, scopes=scopes)
    elif credentials_path:
        credentials = Credentials.from_service_account_file(credentials_path, scopes=scopes)
    else:
        raise RuntimeError(
            "GOOGLE_SERVICE_ACCOUNT_JSON または GOOGLE_APPLICATION_CREDENTIALS を設定してください"
        )
    return gspread.authorize(credentials)


def fetch_sheets_data(spreadsheet_id=None, brand=None):
    """Google Sheetsから既存 sheets_data 形式で3シートを取得する。"""
    resolved_id = resolve_spreadsheet_id(spreadsheet_id or brand)
    client = _authorize_gspread()
    spreadsheet = client.open_by_key(resolved_id)
    return {
        key: spreadsheet.worksheet(title).get_all_values()
        for key, title in SHEET_TITLES.items()
    }


def load_property_data_from_sheets(sheets_data):
    properties = {}
    property_headers = sheets_data["properties"][0] if sheets_data.get("properties") else []

    def property_value(row, header_name, fallback_index=None, default=""):
        if header_name in property_headers:
            index = property_headers.index(header_name)
            return row[index] if len(row) > index else default
        if fallback_index is not None:
            return row[fallback_index] if len(row) > fallback_index else default
        return default

    for row in sheets_data["properties"][1:]:
        if not row or not row[0]:
            continue
        prop_id = row[0]
        properties[prop_id] = {
            "name": property_value(row, "物件名（正式）", 1),
            "aliases": property_value(row, "略称（カンマ区切り）", 2).split(",")
            if property_value(row, "略称（カンマ区切り）", 2)
            else [],
            "subtitle": property_value(row, "サブタイトル", 6, "募 集 賃 料 表"),
            "notes": property_value(row, "備考", 7),
            "footnote1": property_value(row, "脚注1", 4),
            "footnote2": property_value(row, "脚注2", 5),
            "footnote3": property_value(row, "脚注3"),
            "settings": {},
            "types": {},
            "rooms": [],
        }

    for row in sheets_data["types"][1:]:
        if not row or not row[0]:
            continue
        prop_id = row[0]
        if prop_id not in properties:
            continue
        type_key = normalize_type_key(row[1])
        properties[prop_id]["types"][type_key] = (
            normalize_type_key(row[6]) if len(row) > 6 and row[6] else type_key,
            row[2] if len(row) > 2 else "",
            float(row[3]) if len(row) > 3 and row[3] else 0,
            int(float(row[4])) if len(row) > 4 and row[4] else 0,
            int(float(row[5])) if len(row) > 5 and row[5] else 0,
        )

    for row in sheets_data["rooms"][1:]:
        if not row or not row[0]:
            continue
        prop_id = row[0]
        if prop_id not in properties:
            continue
        properties[prop_id]["rooms"].append(
            (
                int(row[1]) if len(row) > 1 and str(row[1]).isdigit() else 0,
                row[2] if len(row) > 2 else "",
                normalize_type_key(row[3]) if len(row) > 3 else "",
                int(float(str(row[5]).replace(",", ""))) if len(row) > 5 and str(row[5]).replace(",", "").replace(".", "", 1).isdigit() else 0,
                row[6] if len(row) > 6 else "空室",
                row[8] if len(row) > 8 else "住戸",
            )
        )

    return properties
