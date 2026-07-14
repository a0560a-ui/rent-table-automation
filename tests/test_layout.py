from layout import calculate_layout


def test_template_selection():
    assert calculate_layout(4, 8)["template"] == "STANDARD"
    assert calculate_layout(4, 10)["template"] == "COMPACT"
    assert calculate_layout(6, 8)["template"] == "WIDE"
    assert calculate_layout(7, 12)["template"] == "COMPACT"
    assert calculate_layout(4, 13)["template"] == "SPLIT"
    assert calculate_layout(8, 8)["template"] == "SPLIT"
