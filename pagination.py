#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""画像分割計画。"""

from __future__ import annotations

from layout import calculate_layout, fits_canvas
from validator import housing_rooms


def _chunks(values, size):
    return [values[i : i + size] for i in range(0, len(values), size)]


def _type_order(prop, type_keys=None):
    items = sorted(prop["types"].items(), key=lambda x: x[1][4])
    if type_keys is not None:
        items = [item for item in items if item[0] in type_keys]
    return items


def _expanded_type_order(prop, rooms, type_keys=None):
    columns = []
    for type_key, type_info in _type_order(prop, type_keys):
        max_count = 1
        for floor in {room[0] for room in rooms}:
            count = sum(1 for room in rooms if room[0] == floor and room[2] == type_key)
            max_count = max(max_count, count)
        for slot_index in range(max_count):
            columns.append(
                {
                    "type_key": type_key,
                    "type_info": type_info,
                    "slot_index": slot_index,
                    "slot_count": max_count,
                }
            )
    return columns


def _floor_range(rooms):
    floors = sorted({r[0] for r in rooms if r[0] > 0}, reverse=True)
    if not floors:
        return []
    return list(range(max(floors), min(floors) - 1, -1))


def _same_floor_type_multiple(rooms):
    seen = set()
    for room in rooms:
        key = (room[0], room[2])
        if key in seen:
            return True
        seen.add(key)
    return False


def make_single_page(prop):
    rooms = housing_rooms(prop)
    floors = _floor_range(rooms)
    types = _expanded_type_order(prop, rooms)
    return {
        "rooms": rooms,
        "floors": floors,
        "type_order": types,
        "split_direction": "NONE",
    }


def _pages_by_floor(prop, max_floors):
    rooms = housing_rooms(prop)
    floors = _floor_range(rooms)
    pages = []
    for floor_group in _chunks(floors, max_floors):
        floor_set = set(floor_group)
        page_rooms = [r for r in rooms if r[0] in floor_set]
        used_types = {r[2] for r in page_rooms}
        pages.append(
            {
                "rooms": page_rooms,
                "floors": floor_group,
                "type_order": _expanded_type_order(prop, page_rooms, used_types),
                "split_direction": "FLOOR",
            }
        )
    return pages


def _pages_by_type(prop, max_types):
    rooms = housing_rooms(prop)
    pages = []
    for type_group in _chunks(_type_order(prop), max_types):
        type_set = {t[0] for t in type_group}
        page_rooms = [r for r in rooms if r[2] in type_set]
        pages.append(
            {
                "rooms": page_rooms,
                "floors": _floor_range(page_rooms),
                "type_order": _expanded_type_order(prop, page_rooms, type_set),
                "split_direction": "TYPE",
            }
        )
    return pages


def needs_split(prop, layout):
    rooms = housing_rooms(prop)
    floors = len(set(r[0] for r in rooms))
    types = len(prop["types"])
    fit, _ = fits_canvas(layout, types, floors)
    return layout["template"] == "SPLIT" or not fit or _same_floor_type_multiple(rooms)


def split_property_pages(prop, settings=None):
    settings = settings or prop.get("settings", {})
    rooms = housing_rooms(prop)
    floors_count = len(_floor_range(rooms))
    type_count = len(prop["types"])
    layout = calculate_layout(type_count, floors_count, settings)
    if not needs_split(prop, layout):
        return [make_single_page(prop)], layout

    base_max_floors = int(settings.get("max_floors_per_page") or 8)
    base_max_types = int(settings.get("max_types_per_page") or 6)
    floor_pages = _pages_by_floor(prop, max(1, min(base_max_floors, 8)))
    type_pages = _pages_by_type(prop, max(1, min(base_max_types, 6)))
    direction = settings.get("split_direction", "AUTO")

    candidates = []
    if direction in {"AUTO", "FLOOR"}:
        candidates.append(floor_pages)
    if direction in {"AUTO", "TYPE"}:
        candidates.append(type_pages)

    def candidate_fits(pages):
        for page in pages:
            page_layout = calculate_layout(
                len(page["type_order"]),
                len(page["floors"]),
                {"layout_override": "COMPACT"},
            )
            fit, _ = fits_canvas(page_layout, len(page["type_order"]), len(page["floors"]))
            if not fit:
                return False
        return True

    valid_candidates = [pages for pages in candidates if candidate_fits(pages)]
    if valid_candidates:
        candidates = valid_candidates
    elif direction == "AUTO":
        candidates = [type_pages]

    def score(pages):
        return (
            len(pages),
            max(len(page["type_order"]) for page in pages),
            max(len(page["floors"]) for page in pages),
        )

    pages = sorted(candidates, key=score)[0]
    page_layout = calculate_layout(
        max(len(page["type_order"]) for page in pages),
        max(len(page["floors"]) for page in pages),
        {"layout_override": "COMPACT"},
    )
    page_layout["template"] = "SPLIT"
    return pages, page_layout
