from html_pages import build_property_page


def test_build_property_page_creates_one_url_page(tmp_path):
    result = build_property_page(
        "F008",
        "デュオフラッツ一之江East",
        ["https://example.com/F008_01.png", "https://example.com/F008_02.png"],
        tmp_path,
        base_url="https://example.com/price-tables",
        issue_date="2026年07月15日",
    )

    html_path = tmp_path / "rent-tables" / "F008" / "index.html"
    html = html_path.read_text(encoding="utf-8")
    assert result["url"] == "https://example.com/price-tables/rent-tables/F008/"
    assert result["image_count"] == 2
    assert "https://example.com/F008_01.png" in html
    assert "デュオフラッツ一之江East 募集賃料表" in html
