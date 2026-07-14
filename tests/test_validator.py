from sheets import load_property_data_from_sheets
from validator import validate_property_data

from conftest import make_sheets_data


def test_validate_ok():
    props = load_property_data_from_sheets(make_sheets_data())
    success, message = validate_property_data("P001", props)
    assert success, message


def test_unknown_status_fails():
    data = make_sheets_data()
    data["rooms"][1][6] = "商談中"
    props = load_property_data_from_sheets(data)
    success, message = validate_property_data("P001", props)
    assert not success
    assert "不明な状態" in message


def test_undefined_type_fails():
    data = make_sheets_data()
    data["rooms"][1][3] = "Z"
    props = load_property_data_from_sheets(data)
    success, message = validate_property_data("P001", props)
    assert not success
    assert "未定義タイプ" in message


def test_type_apostrophe_variants_are_normalized():
    data = make_sheets_data(type_count=1, floor_count=1)
    data["types"][1][1] = "B’"
    data["types"][1][6] = "B`"
    data["rooms"][1][3] = "B'"
    props = load_property_data_from_sheets(data)
    success, message = validate_property_data("P001", props)
    assert success, message
    assert "B’" in props["P001"]["types"]
