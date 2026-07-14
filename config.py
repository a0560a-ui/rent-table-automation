#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""募集賃料表ジェネレーター共通設定。

既存本番コードのブランドカラー、画像サイズ、基本フォント指定を維持する。
"""

from __future__ import annotations

import os
from pathlib import Path

CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1920

# ===== 既存ブランドカラー定義（変更禁止） =====
COLOR_BG = (250, 247, 240)
COLOR_GOLD = (184, 147, 47)
COLOR_GOLD_LIGHT = (232, 217, 168)
COLOR_GREIGE_DARK = (92, 84, 74)
COLOR_GREIGE = (138, 127, 112)
COLOR_GREIGE_LIGHT = (237, 231, 221)
COLOR_WHITE = (255, 255, 255)
COLOR_VACANT_BG = (255, 255, 255)
COLOR_OCCUPIED_BG = (220, 215, 205)
COLOR_NON_RECRUIT_BG = (245, 240, 230)
COLOR_BORDER = (199, 189, 168)

ALLOWED_STATUSES = {"空室", "満室", "非募集"}

FONT_PATH = os.getenv("RENT_TABLE_FONT_PATH", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
FONT_BOLD_PATH = os.getenv("RENT_TABLE_FONT_BOLD_PATH", "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output"
SITE_DIR = PROJECT_ROOT / "site"
IMAGEKIT_PRICE_TABLE_FOLDER = "/lstep/rent-tables"
MAX_FIXED_PAGE_SLOTS = int(os.getenv("MAX_FIXED_PAGE_SLOTS", "5"))

BRAND_SPREADSHEET_IDS = {
    "デュオメゾン": "16_hW9qmyJAJnRPNeZZmC-HHK--yi4AoM1VG_65JV-1I",
    "DM": "16_hW9qmyJAJnRPNeZZmC-HHK--yi4AoM1VG_65JV-1I",
    "デュオフラッツ": "1RIyD_TmPFxWCsc40YCGnruiWb2jYineu8LwYwQqnPgQ",
    "DF": "1RIyD_TmPFxWCsc40YCGnruiWb2jYineu8LwYwQqnPgQ",
}

SHEET_TITLES = {
    "properties": "物件マスター",
    "types": "タイプ定義",
    "rooms": "部屋マスター",
}


def imagekit_private_key() -> str | None:
    return os.getenv("IMAGEKIT_PRIVATE_KEY")


def imagekit_public_key() -> str | None:
    return os.getenv("IMAGEKIT_PUBLIC_KEY")


def imagekit_endpoint() -> str | None:
    return os.getenv("IMAGEKIT_URL_ENDPOINT")


def google_spreadsheet_id() -> str | None:
    return os.getenv("GOOGLE_SPREADSHEET_ID")


def google_service_account_json() -> str | None:
    return os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")


def google_application_credentials() -> str | None:
    return os.getenv("GOOGLE_APPLICATION_CREDENTIALS")


def public_site_base_url() -> str | None:
    return os.getenv("PUBLIC_SITE_BASE_URL")
