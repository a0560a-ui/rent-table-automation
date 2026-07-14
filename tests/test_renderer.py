from pathlib import Path

from PIL import Image

from renderer import generate_image
from sheets import load_property_data_from_sheets

from conftest import make_sheets_data


def test_render_image_size_and_room_count(tmp_path):
    props = load_property_data_from_sheets(make_sheets_data(4, 5))
    pages = generate_image("P001", props, issue_date="2026年07月13日", output_dir=tmp_path)
    assert len(pages) == 1
    assert Image.open(pages[0]["path"]).size == (1080, 1920)
    assert len(pages[0]["rendered_room_uids"]) == 20


def test_split_for_many_floors(tmp_path):
    data = make_sheets_data(4, 20)
    props = load_property_data_from_sheets(data)
    pages = generate_image("P001", props, issue_date="2026年07月13日", output_dir=tmp_path)
    assert len(pages) >= 2
    assert all(Path(page["path"]).exists() for page in pages)
    rendered = [uid for page in pages for uid in page["rendered_room_uids"]]
    assert len(rendered) == len(data["rooms"]) - 1


def test_duplicate_same_floor_type_not_dropped(tmp_path):
    props = load_property_data_from_sheets(make_sheets_data(4, 5, duplicate_same_cell=True))
    pages = generate_image("P001", props, issue_date="2026年07月13日", output_dir=tmp_path)
    rendered = [uid for page in pages for uid in page["rendered_room_uids"]]
    assert "P001:199" in rendered
    assert len(rendered) == 21


def test_missing_middle_floor_is_still_displayed(tmp_path):
    data = make_sheets_data(4, 5)
    data["rooms"] = [data["rooms"][0], *[row for row in data["rooms"][1:] if row[1] != "3"]]
    props = load_property_data_from_sheets(data)
    pages = generate_image("P001", props, issue_date="2026年07月13日", output_dir=tmp_path)
    assert pages[0]["layout"]["template"] == "STANDARD"
    # 入力住戸は欠落させず、表側の階行だけ 5F〜1F の連続表示にする。
    assert len(pages[0]["rendered_room_uids"]) == 16


def test_deterministic_output(tmp_path):
    props = load_property_data_from_sheets(make_sheets_data(6, 8))
    a = generate_image("P001", props, issue_date="2026年07月13日", output_dir=tmp_path / "a")
    b = generate_image("P001", props, issue_date="2026年07月13日", output_dir=tmp_path / "b")
    assert Path(a[0]["path"]).read_bytes() == Path(b[0]["path"]).read_bytes()
