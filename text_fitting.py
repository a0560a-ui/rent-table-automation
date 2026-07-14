#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pillow textbbox() による文字幅調整。"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PIL import ImageFont

from config import FONT_BOLD_PATH, FONT_PATH


class TextDoesNotFit(ValueError):
    pass


def _fallback_font_path(bold=False):
    candidates = [
        FONT_BOLD_PATH if bold else FONT_PATH,
        "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if path and Path(path).exists():
            return path
    return None


@lru_cache(maxsize=256)
def load_font(size, bold=False):
    path = _fallback_font_path(bold)
    if path:
        return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def text_width(draw, text, font):
    bbox = draw.textbbox((0, 0), str(text), font=font)
    return bbox[2] - bbox[0]


def text_height(draw, text, font):
    bbox = draw.textbbox((0, 0), str(text), font=font)
    return bbox[3] - bbox[1]


def fit_font_to_width(draw, text, max_font_size, min_font_size, max_width, bold=False):
    for size in range(max_font_size, min_font_size - 1, -1):
        font = load_font(size, bold=bold)
        if text_width(draw, text, font) <= max_width:
            return font, size
    raise TextDoesNotFit(f"'{text}' does not fit in {max_width}px")


def draw_centered(draw, x, y, text, font, color):
    bbox = draw.textbbox((0, 0), str(text), font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text((x - tw // 2, y - th // 2 - 2), str(text), fill=color, font=font)
