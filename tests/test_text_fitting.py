from PIL import Image, ImageDraw
import pytest

from text_fitting import TextDoesNotFit, fit_font_to_width


def test_fit_font_to_width_uses_bbox():
    draw = ImageDraw.Draw(Image.new("RGB", (300, 100)))
    font, size = fit_font_to_width(draw, "¥123,456", 22, 8, 120, bold=True)
    assert 8 <= size <= 22


def test_fit_font_to_width_fails_when_too_small():
    draw = ImageDraw.Draw(Image.new("RGB", (300, 100)))
    with pytest.raises(TextDoesNotFit):
        fit_font_to_width(draw, "長すぎる長すぎる長すぎるタイプ名", 12, 12, 20)
