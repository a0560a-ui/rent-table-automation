from __future__ import annotations

import pytest

from sheets import load_property_data_from_sheets


def make_sheets_data(type_count=4, floor_count=5, duplicate_same_cell=False, long_type=False):
    types = [["物件ID", "タイプ", "間取り", "専有面積(㎡)", "共益費", "表示順序", "表示ラベル"]]
    rooms = [["物件ID", "階", "部屋番号", "タイプ", "間取り(自動)", "賃料(共益費込)", "状態", "備考", "区分"]]
    for i in range(type_count):
        key = chr(ord("A") + i)
        label = f"{key}非常に長いタイプ名" if long_type and i == 0 else key
        types.append(["P001", key, f"{i + 1}K", f"{24.5 + i}", "10000", str(i + 1), label])
    statuses = ["空室", "満室", "非募集"]
    for floor in range(1, floor_count + 1):
        for i in range(type_count):
            key = chr(ord("A") + i)
            rooms.append(["P001", str(floor), f"{floor}{i + 1:02d}", key, "", str(120000 + floor * 1000 + i * 5000), statuses[(floor + i) % 3], "", "住戸"])
    if duplicate_same_cell:
        rooms.append(["P001", "1", "199", "A", "", "188000", "空室", "", "住戸"])
    return {
        "properties": [
            ["物件ID", "物件名（正式）", "略称（カンマ区切り）", "総戸数（自動計算）", "脚注1", "脚注2", "サブタイトル", "備考"],
            ["P001", "デュオメゾン品川戸越", "品川戸越", "", "※ 表示金額は税込・共益費込の月額賃料です。", "※ 別途費用が必要です。", "募 集 賃 料 表", "ペット可"],
        ],
        "types": types,
        "rooms": rooms,
    }


@pytest.fixture
def properties():
    return load_property_data_from_sheets(make_sheets_data())
