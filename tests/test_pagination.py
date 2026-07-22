from pagination import split_property_pages
from sheets import load_property_data_from_sheets

from conftest import make_sheets_data


def test_type_split_prioritizes_vacant_types_on_first_page():
    data = make_sheets_data(type_count=10, floor_count=2)
    for row in data["rooms"][1:]:
        row[6] = "満室"
    for row in data["rooms"][1:]:
        if row[3] == "J":
            row[6] = "空室"

    props = load_property_data_from_sheets(data)
    pages, _ = split_property_pages(props["P001"])

    assert len(pages) >= 2
    first_page_types = [column["type_key"] for column in pages[0]["type_order"]]
    assert "J" in first_page_types
