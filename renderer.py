#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pillow描画処理。

既存 generate_image() のデザイン・描画順序を維持しつつ、ページ分割と
文字幅実測を追加する。
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw

from config import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    COLOR_BG,
    COLOR_BORDER,
    COLOR_GOLD,
    COLOR_GOLD_LIGHT,
    COLOR_GREIGE,
    COLOR_GREIGE_DARK,
    COLOR_GREIGE_LIGHT,
    COLOR_NON_RECRUIT_BG,
    COLOR_OCCUPIED_BG,
    COLOR_VACANT_BG,
    COLOR_WHITE,
    OUTPUT_DIR,
)
from pagination import split_property_pages
from text_fitting import TextDoesNotFit, draw_centered, fit_font_to_width, load_font
from validator import housing_rooms, validate_property_data, validate_render_result


def safe_filename(name):
    return re.sub(r'[\\/:*?"<>|\s]+', "", name)[:80] or "property"


def output_filename(prop, page_number=1, total_pages=1):
    base = f"募集賃料表_Lステップ_{safe_filename(prop['name'])}"
    if total_pages == 1:
        return f"{base}.png"
    return f"{base}_{page_number:02d}.png"


def _fit_and_draw_centered(draw, x, y, text, max_size, min_size, max_width, color, bold=False, metrics=None):
    font, size = fit_font_to_width(draw, text, max_size, min_size, max_width, bold=bold)
    if metrics is not None:
        metrics["min_font_used"] = min(metrics["min_font_used"], size)
    draw_centered(draw, x, y, text, font, color)
    return size


def _draw_text_block(draw, rect, text, max_size, min_size, text_color, fill_color, bold=False, metrics=None, outline=True):
    x1, y1, x2, y2 = rect
    if outline:
        draw.rectangle([x1, y1, x2, y2], fill=fill_color, outline=COLOR_BORDER, width=1)
    else:
        draw.rectangle([x1, y1, x2, y2], fill=fill_color)
    _fit_and_draw_centered(
        draw,
        (x1 + x2) // 2,
        (y1 + y2) // 2,
        text,
        max_size,
        min_size,
        max(1, x2 - x1 - 8),
        text_color,
        bold=bold,
        metrics=metrics,
    )


def _column_parts(column):
    if isinstance(column, dict):
        return column["type_key"], column["type_info"], column.get("slot_index", 0), column.get("slot_count", 1)
    type_key, type_info = column
    return type_key, type_info, 0, 1


def _cell_bg(status):
    if status == "空室":
        return COLOR_VACANT_BG
    if status == "満室":
        return COLOR_GREIGE_LIGHT
    return COLOR_BG


def _format_area(area):
    try:
        value = float(area)
    except (TypeError, ValueError):
        return ""
    return f"{value:g}㎡"


def _room_band_fill(status):
    if status == "空室":
        return COLOR_GOLD_LIGHT
    if status == "満室":
        return COLOR_OCCUPIED_BG
    return COLOR_NON_RECRUIT_BG


def _draw_room(draw, x, y, room_col_w, row_h, room, type_info, layout, metrics, slot_index=0, slot_count=1):
    fl, room_no, typ, rent, status, _ = room
    label, madori, area, kyoeki, _ = type_info
    slot_h = row_h // slot_count
    slot_y = y + slot_index * slot_h
    center_x = x + room_col_w // 2

    if slot_index:
        draw.line([x + 4, slot_y, x + room_col_w - 4, slot_y], fill=COLOR_BORDER, width=1)

    room_block_h = max(28, min(38, slot_h // 4))
    room_block_bottom = slot_y + 6 + room_block_h
    room_label = f"{room_no} / {_format_area(area)}" if _format_area(area) else room_no
    _draw_text_block(
        draw,
        [x + 6, slot_y + 6, x + room_col_w - 6, room_block_bottom],
        room_label,
        layout["font_room"],
        layout["min_font"],
        COLOR_GREIGE_DARK,
        _room_band_fill(status),
        bold=True,
        metrics=metrics,
        outline=False,
    )
    main_top = room_block_bottom + 6
    main_bottom = slot_y + slot_h - 6
    main_center_y = (main_top + main_bottom) // 2

    if status == "空室":
        price_text = f"¥{rent:,}"
        fee_text = f"共益費 ¥{kyoeki:,}"
        _fit_and_draw_centered(
            draw,
            center_x,
            main_center_y - 13,
            price_text,
            layout["font_price"],
            layout["min_font"],
            room_col_w - 8,
            COLOR_GOLD,
            bold=True,
            metrics=metrics,
        )
        if slot_h >= 64:
            _fit_and_draw_centered(
                draw,
                center_x,
                main_center_y + 20,
                fee_text,
                layout["font_kyoeki"],
                layout["min_font"],
                room_col_w - 8,
                COLOR_GREIGE,
                metrics=metrics,
            )
    elif status == "満室":
        _fit_and_draw_centered(
            draw,
            center_x,
            main_center_y,
            "満室",
            layout["font_price"],
            layout["min_font"],
            room_col_w - 8,
            COLOR_GREIGE,
            bold=True,
            metrics=metrics,
        )
    else:
        _fit_and_draw_centered(
            draw,
            center_x,
            main_center_y,
            "非募集",
            layout["font_price"],
            layout["min_font"],
            room_col_w - 8,
            COLOR_GREIGE,
            bold=True,
            metrics=metrics,
        )


def render_property_page(prop, page, layout, page_number=1, total_pages=1, issue_date=None, output_dir=None):
    output_dir = Path(output_dir or OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), COLOR_BG)
    draw = ImageDraw.Draw(img)
    metrics = {"min_font_used": 999}

    W, H = CANVAS_WIDTH, CANVAS_HEIGHT
    y_cursor = 40

    font_subtitle = load_font(layout["font_subtitle"], bold=True)
    draw_centered(draw, W // 2, y_cursor, prop["subtitle"], font_subtitle, COLOR_GREIGE)
    y_cursor += 50

    _fit_and_draw_centered(
        draw,
        W // 2,
        y_cursor,
        prop["name"],
        40,
        22,
        960,
        COLOR_GREIGE_DARK,
        bold=True,
        metrics=metrics,
    )
    y_cursor += 70

    page_rooms = page["rooms"]
    all_rooms = housing_rooms(prop)
    vacant_count = sum(1 for r in all_rooms if r[4] == "空室")
    occupied_count = sum(1 for r in all_rooms if r[4] == "満室")
    total_recruit = vacant_count + occupied_count
    font_status = load_font(layout["font_status"], bold=True)
    status_text = f"空室状況   {vacant_count} / {total_recruit} 戸"
    draw_centered(draw, W // 2, y_cursor, status_text, font_status, COLOR_GOLD)
    y_cursor += 60

    if issue_date is None:
        issue_date = datetime.now().strftime("%Y年%m月%d日")
    if total_pages > 1:
        issue_date = f"{issue_date}   {page_number} / {total_pages}"
    font_date = load_font(layout["font_date"])
    draw_centered(draw, W // 2, y_cursor, issue_date, font_date, COLOR_GREIGE)
    y_cursor += 50

    type_order = page["type_order"]
    floors_set = page["floors"]
    num_types = len(type_order)
    row_h = layout["rowH"]
    floor_col_w = layout["floorColW"]
    room_col_w = (layout["table_width"] - floor_col_w) // max(num_types, 1)
    table_x = (W - (floor_col_w + room_col_w * num_types)) // 2
    table_y = y_cursor
    header_y = table_y
    header_h = layout["header_h"]

    draw.rectangle([table_x, header_y, table_x + floor_col_w, header_y + header_h], fill=COLOR_GREIGE_LIGHT, outline=COLOR_BORDER, width=2)
    font_header = load_font(layout["font_header"], bold=True)
    draw_centered(draw, table_x + floor_col_w // 2, header_y + header_h // 2, "階", font_header, COLOR_GREIGE_DARK)

    for i, column in enumerate(type_order):
        type_key, type_info, slot_index, slot_count = _column_parts(column)
        label, madori, area, kyoeki, _ = type_info
        display_label = label if slot_count == 1 else f"{label}-{slot_index + 1}"
        x = table_x + floor_col_w + i * room_col_w
        draw.rectangle([x, header_y, x + room_col_w, header_y + header_h], fill=COLOR_GREIGE_LIGHT, outline=COLOR_BORDER, width=2)
        _fit_and_draw_centered(
            draw,
            x + room_col_w // 2,
            header_y + header_h // 2,
            display_label,
            layout["font_header"],
            layout["min_font"],
            room_col_w - 8,
            COLOR_GREIGE_DARK,
            bold=True,
            metrics=metrics,
        )

    data_y = header_y + header_h
    font_floor = load_font(layout["font_floor"], bold=True)
    rendered_room_uids = []

    for floor_idx, floor in enumerate(floors_set):
        y = data_y + floor_idx * row_h
        draw.rectangle([table_x, y, table_x + floor_col_w, y + row_h], fill=COLOR_GREIGE_LIGHT, outline=COLOR_BORDER, width=1)
        draw_centered(draw, table_x + floor_col_w // 2, y + row_h // 2, f"{floor}F", font_floor, COLOR_GREIGE_DARK)
        floor_rooms = [r for r in page_rooms if r[0] == floor]

        for i, column in enumerate(type_order):
            type_key, type_info, slot_index, slot_count = _column_parts(column)
            x = table_x + floor_col_w + i * room_col_w
            matching_rooms = sorted([r for r in floor_rooms if r[2] == type_key], key=lambda r: r[1])
            if slot_count > 1:
                matching_rooms = matching_rooms[slot_index : slot_index + 1]
            if not matching_rooms:
                draw.rectangle([x, y, x + room_col_w, y + row_h], fill=COLOR_BG, outline=COLOR_BORDER, width=1)
                continue
            draw.rectangle([x, y, x + room_col_w, y + row_h], fill=_cell_bg(matching_rooms[0][4]), outline=COLOR_BORDER, width=1)
            if len(matching_rooms) > 2 and row_h // len(matching_rooms) < 38:
                raise TextDoesNotFit("同一セル内の住戸数が多すぎます")
            for slot_index, room in enumerate(matching_rooms):
                _draw_room(draw, x, y, room_col_w, row_h, room, type_info, layout, metrics, slot_index, len(matching_rooms))
                rendered_room_uids.append(room[1])

    footer_y = data_y + len(floors_set) * row_h + 40
    font_footnote = load_font(layout["font_footnote"])
    if prop.get("footnote1"):
        draw_centered(draw, W // 2, footer_y, prop["footnote1"], font_footnote, COLOR_GREIGE)
        footer_y += 25
    if prop.get("footnote2"):
        draw_centered(draw, W // 2, footer_y, prop["footnote2"], font_footnote, COLOR_GREIGE)
        footer_y += 25
    if prop.get("notes"):
        footer_y += 15
        font_notes = load_font(layout["font_notes"], bold=True)
        draw_centered(draw, W // 2, footer_y, prop["notes"], font_notes, COLOR_GOLD)

    filename = output_filename(prop, page_number, total_pages)
    path = output_dir / filename
    img.save(path, "PNG", optimize=True)
    return {
        "image": img,
        "filename": filename,
        "path": str(path),
        "size": img.size,
        "page_number": page_number,
        "total_pages": total_pages,
        "layout": layout,
        "split_direction": page["split_direction"],
        "rendered_room_uids": rendered_room_uids,
        "status_text": status_text,
        "final_y": footer_y,
        "min_font_used": metrics["min_font_used"] if metrics["min_font_used"] != 999 else layout["min_font"],
    }


def render_placeholder_page(prop_name, output_path, message="このページは現在使用していません"):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), COLOR_BG)
    draw = ImageDraw.Draw(img)
    title_font = load_font(40, bold=True)
    message_font = load_font(28, bold=True)
    draw_centered(draw, CANVAS_WIDTH // 2, 760, prop_name, title_font, COLOR_GREIGE_DARK)
    draw_centered(draw, CANVAS_WIDTH // 2, 860, message, message_font, COLOR_GREIGE)
    img.save(output_path, "PNG", optimize=True)
    return str(output_path)


def generate_image(prop_id, properties, issue_date=None, output_dir=None):
    success, message = validate_property_data(prop_id, properties)
    if not success:
        raise ValueError(message)
    prop = properties[prop_id]
    pages, layout = split_property_pages(prop)
    rendered = [
        render_property_page(prop, page, layout, index, len(pages), issue_date, output_dir)
        for index, page in enumerate(pages, start=1)
    ]
    # rendered_room_uids は部屋番号なので、検証用に物件IDを付与する。
    for page in rendered:
        page["rendered_room_uids"] = [f"{prop_id}:{room_no}" for room_no in page["rendered_room_uids"]]
    validate_render_result(prop_id, properties, rendered)
    return rendered
