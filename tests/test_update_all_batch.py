import csv
import json

from scripts.update_all_price_tables import _target_property_ids, _write_reports


def test_target_property_ids_skips_empty_properties():
    properties = {
        "A001": {"rooms": [(1, "101", "A", 100000, "空室", "住戸")]},
        "A002": {"rooms": []},
        "A003": {"rooms": [(1, "101", "A", 100000, "空室", "店舗")]},
    }
    assert _target_property_ids(properties) == ["A001"]


def test_write_reports_outputs_json_and_csv(tmp_path):
    rows = [
        {
            "brand": "DF",
            "property_id": "F008",
            "property_name": "デュオフラッツ一之江East",
            "status": "success",
            "page_count": 3,
            "input_room_count": 40,
            "rendered_room_count": 40,
            "split_direction": "TYPE",
            "template": "SPLIT",
            "error": "",
            "urls": ["https://example.com/F008_01.png"],
            "page_url": "https://example.com/rent-tables/F008/",
        }
    ]
    json_path, csv_path = _write_reports(rows, tmp_path)
    assert json.loads(json_path.read_text(encoding="utf-8"))[0]["property_id"] == "F008"
    with csv_path.open(encoding="utf-8") as handle:
        assert list(csv.DictReader(handle))[0]["status"] == "success"
