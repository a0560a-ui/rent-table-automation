import csv
import json

from reporting import build_public_update_report, write_json_csv_reports


def test_public_update_report_shows_failures_first_and_links(tmp_path):
    rows = [
        {
            "brand": "DF",
            "property_id": "F008",
            "property_name": "デュオフラッツ一之江East",
            "status": "success",
            "page_count": 2,
            "input_room_count": 40,
            "rendered_room_count": 40,
            "split_direction": "TYPE",
            "template": "SPLIT",
            "error": "",
            "urls": ["https://example.com/F008_01.png"],
            "page_url": "https://example.com/rent-tables/F008/",
        },
        {
            "brand": "DM",
            "property_id": "P008",
            "property_name": "デュオメゾン渋谷",
            "status": "failed",
            "page_count": 0,
            "input_room_count": 18,
            "rendered_room_count": 0,
            "split_direction": "",
            "template": "",
            "error": "未定義タイプ: ['C']",
            "urls": [],
            "page_url": "",
        },
    ]

    result = build_public_update_report(
        rows,
        tmp_path,
        base_url="https://example.com/rent-table-automation",
        generated_at="2026年07月22日 12:00",
    )

    html_path = tmp_path / "reports" / "index.html"
    html = html_path.read_text(encoding="utf-8")
    assert result["url"] == "https://example.com/rent-table-automation/reports/"
    assert result["failed"] == 1
    assert "募集賃料表 更新診断レポート" in html
    assert "P008" in html
    assert "未定義タイプ" in html
    assert "全40住戸 表示完了" in html
    assert "住戸表示: 0 / 18件（18件未表示）" in html
    assert html.index("P008") < html.index("F008")
    assert "https://example.com/rent-tables/F008/" in html
    assert json.loads((tmp_path / "reports" / "latest.json").read_text(encoding="utf-8"))[0]["property_id"] == "F008"


def test_write_json_csv_reports_serializes_list_values(tmp_path):
    rows = [
        {
            "brand": "DF",
            "property_id": "F008",
            "urls": ["https://example.com/F008_01.png"],
        }
    ]

    json_path, csv_path = write_json_csv_reports(rows, tmp_path)

    assert json.loads(json_path.read_text(encoding="utf-8"))[0]["urls"] == ["https://example.com/F008_01.png"]
    with csv_path.open(encoding="utf-8") as handle:
        csv_row = list(csv.DictReader(handle))[0]
    assert csv_row["urls"] == '["https://example.com/F008_01.png"]'
