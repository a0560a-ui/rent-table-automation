from pathlib import Path

from PIL import Image

from renderer import display_rent_excluding_fee, generate_image
from sheets import load_property_data_from_sheets

from conftest import make_sheets_data


def test_render_image_size_and_room_count(tmp_path):
    props = load_property_data_from_sheets(make_sheets_data(4, 5))
    pages = generate_image("P001", props, issue_date="2026年07月13日", output_dir=tmp_path)
    assert len(pages) == 1
    assert Image.open(pages[0]["path"]).size == (1080, 1920)
    assert len(pages[0]["rendered_room_uids"]) == 20
    assert pages[0]["disclaimer_text"] == (
        "本賃料表の記載内容は2026年07月13日時点の情報です。"
        "今後、諸条件等により変更となる場合がございますので、あらかじめご了承ください。"
    )


def test_disclaimer_uses_date_without_page_number(tmp_path):
    props = load_property_data_from_sheets(make_sheets_data(4, 20))
    pages = generate_image("P001", props, issue_date="2026年08月18日", output_dir=tmp_path)

    assert len(pages) >= 2
    assert {page["disclaimer_text"] for page in pages} == {
        "本賃料表の記載内容は2026年08月18日時点の情報です。"
        "今後、諸条件等により変更となる場合がございますので、あらかじめご了承ください。"
    }


def test_split_for_many_floors(tmp_path):
    data = make_sheets_data(4, 20)
    props = load_property_data_from_sheets(data)
    pages = generate_image("P001", props, issue_date="2026年07月13日", output_dir=tmp_path)
    assert len(pages) >= 2
    assert all(Path(page["path"]).exists() for page in pages)
    rendered = [uid for page in pages for uid in page["rendered_room_uids"]]
    assert len(rendered) == len(data["rooms"]) - 1


def test_split_pages_use_whole_property_status_count(tmp_path):
    data = make_sheets_data(10, 4)
    for row in data["rooms"][1:]:
        row[6] = "満室"
    data["rooms"][1][6] = "空室"
    data["rooms"][2][6] = "空室"
    props = load_property_data_from_sheets(data)
    pages = generate_image("P001", props, issue_date="2026年07月13日", output_dir=tmp_path)
    assert len(pages) == 1
    assert pages[0]["layout"]["template"] == "ONE_PAGE_SPLIT"
    assert {page["status_text"] for page in pages} == {"空室状況   2 / 40 戸"}
    assert len(pages[0]["rendered_room_uids"]) == 40
    assert Image.open(pages[0]["path"]).size == (1080, 1920)


def test_two_split_tables_are_combined_without_missing_rooms(tmp_path):
    data = make_sheets_data(14, 5)
    props = load_property_data_from_sheets(data)
    pages = generate_image("P001", props, issue_date="2026年07月13日", output_dir=tmp_path)

    assert len(pages) == 1
    assert pages[0]["layout"]["template"] == "ONE_PAGE_SPLIT"
    assert len(pages[0]["rendered_room_uids"]) == 70
    assert pages[0]["final_y"] < 1920


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


def test_display_rent_excludes_common_service_fee():
    assert display_rent_excluding_fee(200000, 10000) == 190000


def test_second_phase_room_is_read_and_rendered(tmp_path):
    data = make_sheets_data(4, 5, second_phase_rooms={"501"})
    # 実運用で既存列の途中へ追加されても、ヘッダー名で正しく読み取る。
    for row in data["rooms"]:
        second_phase_value = row.pop()
        row.insert(6, second_phase_value)
    props = load_property_data_from_sheets(data)
    second_phase_room = next(room for room in props["P001"]["rooms"] if room[1] == "501")
    assert second_phase_room[4] == "2期募集"
    assert second_phase_room[6] is True

    pages = generate_image("P001", props, issue_date="2026年08月03日", output_dir=tmp_path)
    assert len(pages) == 1
    assert len(pages[0]["rendered_room_uids"]) == 20
    assert pages[0]["min_font_used"] >= pages[0]["layout"]["min_font"]


def test_second_phase_status_is_excluded_from_current_vacancies(tmp_path):
    data = make_sheets_data(4, 5)
    target_row = next(row for row in data["rooms"][1:] if row[2] == "502")
    target_row[6] = "２期募集"
    props = load_property_data_from_sheets(data)
    second_phase_room = next(room for room in props["P001"]["rooms"] if room[1] == "502")

    assert second_phase_room[4] == "2期募集"
    assert second_phase_room[6] is True

    pages = generate_image("P001", props, issue_date="2026年08月05日", output_dir=tmp_path)
    assert len(pages) == 1
    assert "P001:502" in pages[0]["rendered_room_uids"]
    assert pages[0]["status_text"] == "空室状況   5 / 12 戸"


def test_property_master_reads_footnote3():
    props = load_property_data_from_sheets(make_sheets_data(4, 5))
    assert props["P001"]["footnote3"] == "※ 楽器利用不可"
    assert props["P001"]["subtitle"] == "募 集 賃 料 表"
    assert props["P001"]["notes"] == "ペット可"
