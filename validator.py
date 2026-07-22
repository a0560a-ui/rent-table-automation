#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""描画前後の検証。"""

from __future__ import annotations

from config import ALLOWED_STATUSES, CANVAS_HEIGHT, CANVAS_WIDTH


def housing_rooms(prop):
    return [r for r in prop["rooms"] if r[5] == "住戸"]


def room_uid(prop_id, room):
    return f"{prop_id}:{room[1]}"


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
        floor, room_no, typ, rent, status, _ = room
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
    occupied = sum(1 for r in rooms if r[4] == "満室")
    non_recruit = sum(1 for r in rooms if r[4] == "非募集")

    if errors:
        return False, "\n".join(errors + warnings)

    msg = [
        "✅ データ検証合格",
        f"📊 物件名: {prop['name']}",
        f"🏢 階数: {min(floors)}〜{max(floors)}階（{len(floors)}階分）",
        f"🚪 総室数: {len(rooms)}室",
        f"   ├ 空室: {vacant}室",
        f"   ├ 満室: {occupied}室",
        f"   └ 非募集: {non_recruit}室",
        f"📐 タイプ数: {len(defined_types)}種類 {sorted(defined_types)}",
        f"🎯 募集対象: {vacant + occupied}室（空室{vacant} / 満室{occupied}）",
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
