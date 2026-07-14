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

    for row in sheets_data["properties"][1:]:
        if not row or not row[0]:
            continue
        prop_id = row[0]
        properties[prop_id] = {
            "name": row[1] if len(row) > 1 else "",
            "aliases": row[2].split(",") if len(row) > 2 and row[2] else [],
            "subtitle": row[6] if len(row) > 6 else "募 集 賃 料 表",
            "notes": row[7] if len(row) > 7 else "",
            "footnote1": row[4] if len(row) > 4 else "",
            "footnote2": row[5] if len(row) > 5 else "",
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
        type_key = row[1]
        properties[prop_id]["types"][type_key] = (
            row[6] if len(row) > 6 else row[1],
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
                row[3] if len(row) > 3 else "",
                int(float(str(row[5]).replace(",", ""))) if len(row) > 5 and str(row[5]).replace(",", "").replace(".", "", 1).isdigit() else 0,
                row[6] if len(row) > 6 else "空室",
                row[8] if len(row) > 8 else "住戸",
            )
        )

    return properties
