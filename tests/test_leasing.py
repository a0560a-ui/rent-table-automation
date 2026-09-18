import csv
import json

from leasing import build_leasing_dashboard, build_leasing_metrics, prepare_leasing_data


def _prop(statuses):
    return {
        "name": "テスト物件",
        "rooms": [
            (1, str(100 + index), "A", 100000, status, "住戸", status == "2期募集")
            for index, status in enumerate(statuses, start=1)
        ]
        + [(1, "店舗", "", 0, "空室", "店舗", False)],
    }


def test_build_leasing_metrics_excludes_non_recruit_and_second_phase():
    metrics = build_leasing_metrics(
        "DF",
        "F001",
        _prop(["空室", "空室", "申込", "満室", "非募集", "2期募集"]),
    )

    assert metrics["vacant_count"] == 2
    assert metrics["occupied_count"] == 1
    assert metrics["application_count"] == 1
    assert metrics["leasing_target_count"] == 4
    assert metrics["vacancy_rate"] == 50.0
    assert metrics["non_recruit_count"] == 1
    assert metrics["second_phase_count"] == 1


def test_prepare_leasing_data_adds_previous_and_seven_day_changes():
    history = {
        "history": [
            {"date": "2026-09-01", "properties": [{"property_id": "F001", "vacant_count": 8}]},
            {"date": "2026-09-07", "properties": [{"property_id": "F001", "vacant_count": 7}]},
            {"date": "2026-09-09", "properties": [{"property_id": "F001", "vacant_count": 6}]},
        ]
    }
    rows = [{
        "brand": "DF",
        "property_id": "F001",
        "property_name": "テスト物件",
        "vacant_count": 5,
        "leasing_target_count": 20,
        "vacancy_rate": 25.0,
        "occupied_count": 15,
        "non_recruit_count": 0,
        "second_phase_count": 0,
        "page_url": "https://example.com/F001/",
    }]

    data = prepare_leasing_data(rows, previous_data=history, snapshot_date="2026-09-10")

    row = data["properties"][0]
    assert row["previous_change"] == -1
    assert row["seven_day_change"] == -3
    assert row["priority"] == "注意"
    assert [item["date"] for item in data["history"]] == [
        "2026-09-01",
        "2026-09-07",
        "2026-09-09",
        "2026-09-10",
    ]


def test_stagnant_property_is_escalated_to_urgent():
    history = {
        "history": [
            {"date": "2026-09-01", "properties": [{"property_id": "F001", "vacant_count": 5}]},
            {"date": "2026-09-09", "properties": [{"property_id": "F001", "vacant_count": 5}]},
        ]
    }
    rows = [{
        "brand": "DF", "property_id": "F001", "property_name": "停滞物件",
        "vacant_count": 5, "leasing_target_count": 30, "vacancy_rate": 16.7,
        "occupied_count": 25, "non_recruit_count": 0, "second_phase_count": 0,
        "page_url": "",
    }]

    row = prepare_leasing_data(rows, history, snapshot_date="2026-09-10")["properties"][0]
    assert row["priority"] == "要確認"
    assert "7日間減少なし" in row["priority_reason"]


def test_build_leasing_dashboard_outputs_html_json_and_csv(tmp_path):
    metrics = build_leasing_metrics("DF", "F001", _prop(["空室", "満室"]))
    rows = [{**metrics, "page_url": "https://example.com/F001/"}]

    result = build_leasing_dashboard(
        rows,
        tmp_path,
        base_url="https://example.com/site",
        snapshot_date="2026-09-10",
        generated_at="2026年09月10日 05:00",
    )

    html = (tmp_path / "leasing" / "index.html").read_text(encoding="utf-8")
    data = json.loads((tmp_path / "leasing" / "latest.json").read_text(encoding="utf-8"))
    with (tmp_path / "leasing" / "latest.csv").open(encoding="utf-8-sig") as handle:
        csv_rows = list(csv.DictReader(handle))

    assert result["url"] == "https://example.com/site/leasing/"
    assert "リーシング進捗一覧" in html
    assert "https://example.com/F001/" in html
    assert data["properties"][0]["vacant_count"] == 1
    assert csv_rows[0]["property_id"] == "F001"
