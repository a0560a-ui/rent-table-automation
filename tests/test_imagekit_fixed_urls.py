from imagekit import fixed_page_filename, upload_fixed_page_set


def test_fixed_page_filename():
    assert fixed_page_filename("F008", 1) == "F008_01.png"
    assert fixed_page_filename("F008", 12) == "F008_12.png"


def test_upload_fixed_page_set_uses_placeholders(monkeypatch, tmp_path):
    calls = []

    def fake_upload(file_path, brand_name=None, folder=None, file_name=None):
        calls.append({"file_path": file_path, "folder": folder, "file_name": file_name})
        return f"https://example.com/{file_name}", f"id-{file_name}"

    page1 = tmp_path / "page1.png"
    placeholder = tmp_path / "unused.png"
    page1.write_bytes(b"page1")
    placeholder.write_bytes(b"unused")
    monkeypatch.setattr("imagekit.upload_to_imagekit", fake_upload)

    result = upload_fixed_page_set(
        "F008",
        [{"path": str(page1)}],
        placeholder_paths=[str(placeholder)],
        max_slots=3,
    )

    assert [item["file_name"] for item in result] == ["F008_01.png", "F008_02.png", "F008_03.png"]
    assert [item["active"] for item in result] == [True, False, False]
    assert calls[1]["file_path"] == str(placeholder)
