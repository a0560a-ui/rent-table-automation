#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""固定テンプレート方式のレイアウト計算。

calculate_layout() は既存APIとして残し、無段階レスポンシブではなく
STANDARD / WIDE / COMPACT / SPLIT のプリセット選択へ寄せる。
"""

from __future__ import annotations

from copy import deepcopy

from config import CANVAS_HEIGHT, CANVAS_WIDTH


LAYOUT_PRESETS = {
    "STANDARD": {
        "template": "STANDARD",
        "max_types": 4,
        "max_floors": 8,
        "header_h": 82,
        "rowH": 150,
        "floorColW": 80,
        "font_room": 22,
        "font_price": 32,
        "font_kyoeki": 17,
        "font_header": 22,
        "font_info": 22,
        "font_non_recruit": 32,
        "font_subtitle": 24,
        "font_status": 28,
        "font_date": 17,
        "font_floor": 20,
        "font_footnote": 15,
        "font_notes": 18,
        "show_kyoeki_in_cell": True,
        "show_area": True,
        "min_font": 10,
        "table_width": 1000,
    },
    "WIDE": {
        "template": "WIDE",
        "max_types": 6,
        "max_floors": 8,
        "header_h": 80,
        "rowH": 138,
        "floorColW": 76,
        "font_room": 18,
        "font_price": 26,
        "font_kyoeki": 14,
        "font_header": 19,
        "font_info": 19,
        "font_non_recruit": 26,
        "font_subtitle": 23,
        "font_status": 26,
        "font_date": 16,
        "font_floor": 18,
        "font_footnote": 14,
        "font_notes": 17,
        "show_kyoeki_in_cell": True,
        "show_area": True,
        "min_font": 9,
        "table_width": 1000,
    },
    "COMPACT": {
        "template": "COMPACT",
        "max_types": 8,
        "max_floors": 12,
        "header_h": 76,
        "rowH": 112,
        "floorColW": 68,
        "font_room": 15,
        "font_price": 22,
        "font_kyoeki": 12,
        "font_header": 16,
        "font_info": 16,
        "font_non_recruit": 22,
        "font_subtitle": 21,
        "font_status": 24,
        "font_date": 15,
        "font_floor": 16,
        "font_footnote": 13,
        "font_notes": 16,
        "show_kyoeki_in_cell": False,
        "show_area": True,
        "min_font": 8,
        "table_width": 1000,
    },
}

HEADER_FIXED_HEIGHT = 40 + 50 + 70 + 60 + 50
FOOTER_RESERVED_HEIGHT = 120


def select_layout_template(nt: int, floors: int, settings: dict | None = None) -> str:
    settings = settings or {}
    override = settings.get("layout_override", "AUTO")
    if override in {"STANDARD", "WIDE", "COMPACT", "SPLIT"}:
        return override
    if floors > 12 or nt > 7:
        return "SPLIT"
    if 1 <= nt <= 4 and 1 <= floors <= 8:
        return "STANDARD"
    if 5 <= nt <= 6 and 1 <= floors <= 8:
        return "WIDE"
    if 1 <= nt <= 7 and 9 <= floors <= 12:
        return "COMPACT"
    return "SPLIT"


def calculate_required_height(layout: dict, floors: int) -> int:
    return HEADER_FIXED_HEIGHT + layout["header_h"] + floors * layout["rowH"] + FOOTER_RESERVED_HEIGHT


def fits_canvas(layout: dict, nt: int, floors: int) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if nt > layout["max_types"]:
        reasons.append(f"タイプ数{nt}が{layout['template']}上限{layout['max_types']}を超過")
    if floors > layout["max_floors"]:
        reasons.append(f"階数{floors}が{layout['template']}上限{layout['max_floors']}を超過")
    if calculate_required_height(layout, floors) > CANVAS_HEIGHT:
        reasons.append("高さが1920pxを超過")
    room_col_w = (layout["table_width"] - layout["floorColW"]) // max(nt, 1)
    if room_col_w < 80:
        reasons.append("列幅が最低幅を下回る")
    return not reasons, reasons


def calculate_layout(nt: int, floors: int, settings: dict | None = None) -> dict:
    """既存関数名を維持したレイアウト入口。"""
    template = select_layout_template(nt, floors, settings)
    if template == "SPLIT":
        base = deepcopy(LAYOUT_PRESETS["COMPACT"])
        base["template"] = "SPLIT"
    else:
        base = deepcopy(LAYOUT_PRESETS[template])

    base["roomColW"] = (base["table_width"] - base["floorColW"]) // max(nt, 1)
    base["canvas_width"] = CANVAS_WIDTH
    base["canvas_height"] = CANVAS_HEIGHT
    fit, reasons = fits_canvas(base, nt, floors)
    base["fits_canvas"] = fit
    base["fit_reasons"] = reasons
    return base
