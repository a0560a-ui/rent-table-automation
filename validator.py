#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""描画前後の検証。"""

from __future__ import annotations

import math

from config import ALLOWED_STATUSES, CANVAS_HEIGHT, CANVAS_WIDTH
from sheets import normalize_second_phase, normalize_status, normalize_type_key


def housing_rooms(prop):
    return [r for r in prop["rooms"] if r[5] == "住戸"]


def room_uid(prop_id, room):
    return f"{prop_id}:{room[1]}"


def validate_sheet_data(sheets_data):
    """Return spreadsheet-level and property-level input errors before parsing."""
    issues = {}
    required = {
        "properties": {"物件ID", "物件名（正式）"},
        "types": {"物件ID", "タイプ", "間取り", "専有面積(㎡)", "共益費", "表示順序"},
        "rooms": {"物件ID", "階", "部屋番号", "タイプ", "賃料(共益費込)", "区分"},
    }
    headers = {}
    for key, columns in required.items():
        values = sheets_data.get(key) or []
        headers[key] = values[0] if values else []
        if not values:
            _add_sheet_issue(issues, f"「{key}」シートを読み込めません。")
            continue
        missing = sorted(columns - set(headers[key]))
        if key == "rooms" and "状態" not in headers[key] and "空室" in headers[key]:
            missing = [column for column in missing if column != "状態"]
        if key == "rooms" and "状態" not in headers[key] and "空室" not in headers[key]:
            missing.append("状態または空室")
        if missing:
            _add_sheet_issue(issues, f"「{key}」シートに必須列がありません: {missing}")
    if issues:
        return issues

    property_headers = headers["properties"]
    property_id_col = property_headers.index("物件ID")
    property_name_col = property_headers.index("物件名（正式）")
    properties = {}
    for row_number, row in enumerate(sheets_data["properties"][1:], start=2):
        if not any(str(value or "").strip() for value in row):
            continue
        prop_id = _cell(row, property_id_col)
        name = _cell(row, property_name_col)
        if not prop_id:
            _add_issue(issues, "(物件IDなし)", name, f"物件マスター {row_number}行目: 物件IDが空欄です。")
            continue
        if prop_id in properties:
            _add_issue(issues, prop_id, name, "物件マスターに同じ物件IDが重複しています。")
        properties[prop_id] = name
        if not name:
            _add_issue(issues, prop_id, name, "物件名（正式）が空欄です。")
    if not properties:
        _add_sheet_issue(issues, "物件マスターに物件の登録がありません。")
        return issues

    type_headers = headers["types"]
    type_id_col = type_headers.index("物件ID")
    type_key_col = type_headers.index("タイプ")
    seen_types = set()
    for row_number, row in enumerate(sheets_data["types"][1:], start=2):
        if not any(str(value or "").strip() for value in row):
            continue
        prop_id = _cell(row, type_id_col)
        type_key = normalize_type_key(_cell(row, type_key_col))
        if not prop_id:
            _add_issue(issues, "(物件IDなし)", "", f"タイプ定義 {row_number}行目: 物件IDが空欄です。")
            continue
        if prop_id not in properties:
            _add_issue(issues, prop_id, "", "タイプ定義にありますが、物件マスターに物件IDがありません。")
            continue
        if not type_key:
            _add_issue(issues, prop_id, properties[prop_id], f"タイプ定義 {row_number}行目: タイプが空欄です。")
            continue
        for column in ("間取り", "専有面積(㎡)", "共益費", "表示順序"):
            if column not in type_headers:
                continue
            value = _cell(row, type_headers.index(column)).replace(",", "")
            try:
                if column == "間取り":
                    if not value:
                        raise ValueError
                else:
                    number = float(value)
                    if not math.isfinite(number):
                        raise ValueError
                    if number < 0:
                        raise ValueError
                    if column == "専有面積(㎡)" and number <= 0:
                        raise ValueError
                    if column == "表示順序" and (number <= 0 or not number.is_integer()):
                        raise ValueError
                    if column == "共益費" and not number.is_integer():
                        raise ValueError
            except (ValueError, TypeError):
                requirement = "空欄不可" if column == "間取り" else "0より大きい数" if column in {"専有面積(㎡)", "表示順序"} else "0以上の数"
                _add_issue(issues, prop_id, properties[prop_id], f"タイプ定義 {row_number}行目: {column}は{requirement}で入力してください（{value or '空欄'}）。")
        type_uid = (prop_id, type_key)
        if type_uid in seen_types:
            _add_issue(issues, prop_id, properties[prop_id], f"タイプ定義でタイプ「{type_key}」が重複しています。")
        seen_types.add(type_uid)

    room_headers = headers["rooms"]
    room_id_col = room_headers.index("物件ID")
    room_number_col = room_headers.index("部屋番号")
    room_floor_col = room_headers.index("階")
    room_type_col = room_headers.index("タイプ")
    room_rent_col = room_headers.index("賃料(共益費込)")
    room_category_col = room_headers.index("区分")
    status_col = room_headers.index("状態") if "状態" in room_headers else room_headers.index("空室")
    seen_rooms = set()
    housing_counts = {prop_id: 0 for prop_id in properties}
    for row_number, row in enumerate(sheets_data["rooms"][1:], start=2):
        if not any(str(value or "").strip() for value in row):
            continue
        prop_id = _cell(row, room_id_col)
        room_no = _cell(row, room_number_col)
        if not prop_id:
            _add_issue(issues, "(物件IDなし)", "", f"部屋マスター {row_number}行目: 物件IDが空欄です。")
            continue
        if prop_id not in properties:
            _add_issue(issues, prop_id, "", "部屋マスターにありますが、物件マスターに物件IDがありません。")
            continue
        category = _cell(row, room_category_col)
        if not category:
            _add_issue(issues, prop_id, properties[prop_id], f"部屋マスター {row_number}行目: 区分が空欄です。")
            continue
        if category != "住戸":
            continue
        housing_counts[prop_id] += 1
        if not room_no:
            _add_issue(issues, prop_id, properties[prop_id], f"部屋マスター {row_number}行目: 部屋番号が空欄です。")
        else:
            room_uid = (prop_id, room_no)
            if room_uid in seen_rooms:
                _add_issue(issues, prop_id, properties[prop_id], f"部屋番号「{room_no}」が重複しています。")
            seen_rooms.add(room_uid)
        _validate_numeric_cell(issues, prop_id, properties[prop_id], row, room_floor_col, "階", row_number, integer=True, positive=True)
        _validate_numeric_cell(issues, prop_id, properties[prop_id], row, room_rent_col, "賃料", row_number, integer=True, positive=True)
        if not _cell(row, room_type_col):
            _add_issue(issues, prop_id, properties[prop_id], f"部屋マスター {row_number}行目: タイプが空欄です。")
        raw_status = normalize_status(_cell(row, status_col))
        if normalize_second_phase(raw_status):
            raw_status = "2期募集"
        if raw_status not in ALLOWED_STATUSES:
            _add_issue(issues, prop_id, properties[prop_id], f"部屋マスター {row_number}行目: 募集状況が不正です（{raw_status or '空欄'}）。")

    for prop_id, name in properties.items():
        if not housing_counts[prop_id]:
            _add_issue(issues, prop_id, name, "部屋マスターに住戸がありません。新規物件は住戸データを登録してください。")
    return issues


def _cell(row, index):
    return str(row[index] or "").strip() if len(row) > index else ""


def _add_sheet_issue(issues, message):
    _add_issue(issues, "(シート構成)", "", message)


def _add_issue(issues, prop_id, name, message):
    item = issues.setdefault(prop_id, {"property_name": name, "errors": []})
    if name and not item["property_name"]:
        item["property_name"] = name
    if message not in item["errors"]:
        item["errors"].append(message)


def _validate_numeric_cell(issues, prop_id, name, row, index, label, row_number, integer=False, positive=False):
    value = _cell(row, index).replace(",", "")
    try:
        number = float(value)
        if not math.isfinite(number):
            raise ValueError
        if integer and not number.is_integer():
            raise ValueError
        if positive and number <= 0:
            raise ValueError
        if not positive and number < 0:
            raise ValueError
    except (ValueError, TypeError):
        requirement = "正の整数" if positive and integer else "正の数" if positive else "0以上の数"
        _add_issue(issues, prop_id, name, f"部屋マスター {row_number}行目: {label}は{requirement}で入力してください（{value or '空欄'}）。")


def is_second_phase_room(room):
    return len(room) > 6 and bool(room[6])


def validate_property_data(prop_id, properties):
    if prop_id not in properties:
        return False, f"❌ エラー: 物件ID {prop_id} が見つかりません"

    prop = properties[prop_id]
    errors = []
    warnings = []
    rooms = housing_rooms(prop)
    if not rooms:
        return False, "❌ エラー: 住戸データが存在しません"

    floors = sorted(set(r[0] for r in rooms if isinstance(r[0], int) and r[0] > 0))
    if not floors:
        return False, "❌ エラー: 階数データが取得できません"

    seen_rooms = set()
    for room in rooms:
        floor, room_no, typ, rent, status, *_ = room
        if not room_no:
            errors.append("❌ 部屋番号が空の住戸があります")
        uid = room_uid(prop_id, room)
        if uid in seen_rooms:
            errors.append(f"❌ 重複住戸: {room_no}")
        seen_rooms.add(uid)
        if floor <= 0:
            errors.append(f"❌ 階数不正: {room_no}")
        if not isinstance(rent, int) or rent < 0:
            errors.append(f"❌ 賃料不正: {room_no}")
        if status not in ALLOWED_STATUSES:
            errors.append(f"❌ 不明な状態: {room_no}={status}")

    defined_types = set(prop["types"].keys())
    used_types = set(r[2] for r in rooms if r[2])
    undefined_types = used_types - defined_types
    if undefined_types:
        missing = sorted(undefined_types)
        errors.append(
            "❌ 未定義タイプ: "
            f"{missing} がタイプ定義に存在しません\n"
            "対応: 該当ブランドの「タイプ定義」シートで、"
            f"物件ID {prop_id} に上記タイプを追加してください。"
        )

    vacant = sum(1 for r in rooms if r[4] == "空室")
    application = sum(1 for r in rooms if r[4] == "申込")
    occupied = sum(1 for r in rooms if r[4] == "満室")
    non_recruit = sum(1 for r in rooms if r[4] == "非募集")
    second_phase = sum(1 for r in rooms if is_second_phase_room(r))

    if errors:
        return False, "\n".join(errors + warnings)

    msg = [
        "✅ データ検証合格",
        f"📊 物件名: {prop['name']}",
        f"🏢 階数: {min(floors)}〜{max(floors)}階（{len(floors)}階分）",
        f"🚪 総室数: {len(rooms)}室",
        f"   ├ 空室: {vacant}室",
        f"   ├ 申込: {application}室",
        f"   ├ 満室: {occupied}室",
        f"   └ 非募集: {non_recruit}室",
        f"🔖 2期募集: {second_phase}室",
        f"📐 タイプ数: {len(defined_types)}種類 {sorted(defined_types)}",
        f"🎯 募集対象: {vacant + application + occupied}室"
        f"（空室{vacant} / 申込{application} / 満室{occupied}）",
    ]
    return True, "\n".join(msg)


def validate_render_result(prop_id, properties, pages):
    prop = properties[prop_id]
    input_uids = [room_uid(prop_id, room) for room in housing_rooms(prop)]
    rendered_uids = [uid for page in pages for uid in page["rendered_room_uids"]]
    missing = sorted(set(input_uids) - set(rendered_uids))
    duplicate = sorted(uid for uid in set(rendered_uids) if rendered_uids.count(uid) > 1)
    errors = []
    for page in pages:
        if page["size"] != (CANVAS_WIDTH, CANVAS_HEIGHT):
            errors.append(f"画像サイズ不正: {page['filename']}={page['size']}")
        if page["final_y"] >= CANVAS_HEIGHT:
            errors.append(f"描画Y座標超過: {page['filename']}={page['final_y']}")
        if page["min_font_used"] < page["layout"]["min_font"]:
            errors.append(f"最低フォントサイズ未満: {page['filename']}")
    if missing:
        errors.append(f"欠落住戸: {missing}")
    if duplicate:
        errors.append(f"重複描画住戸: {duplicate}")
    if errors:
        raise ValueError("\n".join(errors))
    return {
        "input_room_count": len(input_uids),
        "rendered_room_count": len(rendered_uids),
        "missing_room_count": len(missing),
        "duplicate_room_count": len(duplicate),
    }
