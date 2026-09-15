#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""リーシング進捗の集計、履歴比較、公開ダッシュボード生成。"""

from __future__ import annotations

import csv
import json
from datetime import date, datetime, timedelta
from html import escape
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from validator import housing_rooms, is_second_phase_room


LEASING_FIELDS = [
    "brand",
    "property_id",
    "property_name",
    "priority",
    "priority_reason",
    "vacant_count",
    "leasing_target_count",
    "vacancy_rate",
    "occupied_count",
    "non_recruit_count",
    "second_phase_count",
    "previous_change",
    "seven_day_change",
    "page_url",
]

PRIORITY_ORDER = {"要確認": 0, "注意": 1, "順調": 2, "満室": 3}


def _join_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def build_leasing_metrics(brand: str, property_id: str, prop: dict) -> dict:
    """1物件の募集状況を、価格表と同じ住戸判定で集計する。"""
    rooms = housing_rooms(prop)
    vacant = sum(1 for room in rooms if room[4] == "空室")
    occupied = sum(1 for room in rooms if room[4] == "満室")
    non_recruit = sum(1 for room in rooms if room[4] == "非募集")
    second_phase = sum(1 for room in rooms if is_second_phase_room(room))
    leasing_target = vacant + occupied
    vacancy_rate = round(vacant / leasing_target * 100, 1) if leasing_target else 0.0
    return {
        "brand": brand,
        "property_id": property_id,
        "property_name": prop.get("name", ""),
        "vacant_count": vacant,
        "leasing_target_count": leasing_target,
        "vacancy_rate": vacancy_rate,
        "occupied_count": occupied,
        "non_recruit_count": non_recruit,
        "second_phase_count": second_phase,
    }


def fetch_previous_leasing_data(base_url: str | None, timeout: float = 10.0) -> dict:
    """公開中の前回データを取得する。初回や通信失敗時は空データで継続する。"""
    if not base_url:
        return {}
    url = _join_url(base_url, "leasing/latest.json")
    request = Request(url, headers={"Cache-Control": "no-cache", "User-Agent": "rent-table-automation"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError):
        return {}


def _snapshot_rows(rows: list[dict]) -> list[dict]:
    keys = (
        "brand",
        "property_id",
        "property_name",
        "vacant_count",
        "leasing_target_count",
        "vacancy_rate",
        "occupied_count",
        "non_recruit_count",
        "second_phase_count",
    )
    return [{key: row.get(key) for key in keys} for row in rows]


def _snapshot_map(snapshot: dict | None) -> dict[str, dict]:
    if not snapshot:
        return {}
    return {str(row.get("property_id", "")): row for row in snapshot.get("properties", [])}


def _parse_snapshot_date(snapshot: dict) -> date | None:
    try:
        return date.fromisoformat(str(snapshot.get("date", "")))
    except ValueError:
        return None


def _comparison_snapshots(history: list[dict], current_date: date) -> tuple[dict | None, dict | None]:
    dated = sorted(
        ((parsed, item) for item in history if (parsed := _parse_snapshot_date(item)) and parsed < current_date),
        key=lambda pair: pair[0],
    )
    previous = dated[-1][1] if dated else None
    seven_day_candidates = [item for parsed, item in dated if parsed <= current_date - timedelta(days=7)]
    seven_days = seven_day_candidates[-1] if seven_day_candidates else None
    return previous, seven_days


def _priority(row: dict) -> tuple[str, str]:
    vacant = int(row.get("vacant_count") or 0)
    target = int(row.get("leasing_target_count") or 0)
    rate = float(row.get("vacancy_rate") or 0)
    seven_day_change = row.get("seven_day_change")
    if target and vacant == 0:
        return "満室", "空室なし"

    urgent_reasons = []
    if vacant >= 10:
        urgent_reasons.append("空室10戸以上")
    if rate >= 30:
        urgent_reasons.append("空室率30%以上")
    if seven_day_change is not None and seven_day_change >= 0 and vacant >= 5:
        urgent_reasons.append("7日間減少なし")
    if urgent_reasons:
        return "要確認", "・".join(urgent_reasons)

    warning_reasons = []
    if vacant >= 5:
        warning_reasons.append("空室5戸以上")
    if rate >= 20:
        warning_reasons.append("空室率20%以上")
    if warning_reasons:
        return "注意", "・".join(warning_reasons)
    return "順調", "基準内"


def prepare_leasing_data(
    report_rows: list[dict],
    previous_data: dict | None = None,
    snapshot_date: str | None = None,
    generated_at: str | None = None,
    history_limit: int = 35,
) -> dict:
    """当日集計へ前回比・7日前比を付与し、公開用履歴を作る。"""
    current_date = date.fromisoformat(snapshot_date) if snapshot_date else date.today()
    history = list((previous_data or {}).get("history", []))
    previous, seven_days = _comparison_snapshots(history, current_date)
    previous_map = _snapshot_map(previous)
    seven_day_map = _snapshot_map(seven_days)

    current_rows = []
    for source in report_rows:
        row = {key: source.get(key) for key in LEASING_FIELDS if key not in {"priority", "priority_reason", "previous_change", "seven_day_change"}}
        property_id = str(row.get("property_id", ""))
        current_vacant = int(row.get("vacant_count") or 0)
        previous_row = previous_map.get(property_id)
        seven_day_row = seven_day_map.get(property_id)
        row["previous_change"] = (
            current_vacant - int(previous_row.get("vacant_count") or 0) if previous_row else None
        )
        row["seven_day_change"] = (
            current_vacant - int(seven_day_row.get("vacant_count") or 0) if seven_day_row else None
        )
        row["priority"], row["priority_reason"] = _priority(row)
        current_rows.append(row)

    current_rows.sort(
        key=lambda row: (
            PRIORITY_ORDER.get(str(row.get("priority")), 9),
            -int(row.get("vacant_count") or 0),
            -float(row.get("vacancy_rate") or 0),
            str(row.get("property_id", "")),
        )
    )

    current_snapshot = {
        "date": current_date.isoformat(),
        "properties": _snapshot_rows(current_rows),
    }
    history = [item for item in history if item.get("date") != current_date.isoformat()]
    history.append(current_snapshot)
    history = sorted(history, key=lambda item: str(item.get("date", "")))[-history_limit:]
    return {
        "generated_at": generated_at or datetime.now().strftime("%Y年%m月%d日 %H:%M"),
        "snapshot_date": current_date.isoformat(),
        "properties": current_rows,
        "history": history,
    }


def _change_label(value) -> str:
    if value is None:
        return "-"
    value = int(value)
    if value > 0:
        return f"+{value}戸"
    if value < 0:
        return f"{value}戸"
    return "変化なし"


def _change_class(value) -> str:
    if value is None or int(value) == 0:
        return "neutral"
    return "worse" if int(value) > 0 else "better"


def _dashboard_row(row: dict) -> str:
    page_url = str(row.get("page_url") or "")
    link = f'<a href="{escape(page_url, quote=True)}">価格表</a>' if page_url else "-"
    rate = float(row.get("vacancy_rate") or 0)
    safe_width = max(0.0, min(100.0, rate))
    previous_change = row.get("previous_change")
    seven_day_change = row.get("seven_day_change")
    priority = str(row.get("priority") or "")
    return f"""        <tr>
          <td><span class="badge priority-{escape(priority)}">{escape(priority)}</span></td>
          <td><strong>{escape(str(row.get("property_name", "")))}</strong><small>{escape(str(row.get("brand", "")))} / {escape(str(row.get("property_id", "")))}</small></td>
          <td class="number vacant">{int(row.get("vacant_count") or 0)}戸</td>
          <td class="number">{int(row.get("leasing_target_count") or 0)}戸</td>
          <td class="rate-cell"><strong>{rate:.1f}%</strong><span class="bar"><i style="width:{safe_width:.1f}%"></i></span></td>
          <td class="number change {_change_class(previous_change)}">{_change_label(previous_change)}</td>
          <td class="number change {_change_class(seven_day_change)}">{_change_label(seven_day_change)}</td>
          <td class="number">{int(row.get("second_phase_count") or 0)}戸</td>
          <td>{escape(str(row.get("priority_reason") or ""))}</td>
          <td>{link}</td>
        </tr>"""


def build_leasing_dashboard(
    report_rows: list[dict],
    site_dir: Path,
    base_url: str | None = None,
    previous_data: dict | None = None,
    snapshot_date: str | None = None,
    generated_at: str | None = None,
) -> dict:
    """リーシング進捗を固定URL向けHTML、JSON、CSVへ出力する。"""
    data = prepare_leasing_data(
        report_rows,
        previous_data=previous_data,
        snapshot_date=snapshot_date,
        generated_at=generated_at,
    )
    output_dir = site_dir / "leasing"
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "latest.json"
    csv_path = output_dir / "latest.csv"
    html_path = output_dir / "index.html"
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=LEASING_FIELDS)
        writer.writeheader()
        writer.writerows([{field: row.get(field, "") for field in LEASING_FIELDS} for row in data["properties"]])

    rows = data["properties"]
    total_vacant = sum(int(row.get("vacant_count") or 0) for row in rows)
    total_target = sum(int(row.get("leasing_target_count") or 0) for row in rows)
    total_rate = round(total_vacant / total_target * 100, 1) if total_target else 0.0
    urgent_count = sum(1 for row in rows if row.get("priority") == "要確認")
    table_rows = "\n".join(_dashboard_row(row) for row in rows)
    html = f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>リーシング進捗一覧</title>
  <style>
    :root {{ color-scheme: light; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: #f7f3ea; color: #3d3832; font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    header {{ background: #fff; border-bottom: 1px solid #c7bda8; }}
    header div, main {{ width: min(1240px, calc(100% - 32px)); margin: 0 auto; }}
    header div {{ padding: 24px 0 20px; }}
    h1 {{ margin: 0 0 6px; font-size: 28px; letter-spacing: 0; }}
    .meta {{ color: #6d6459; font-size: 14px; }}
    main {{ padding: 24px 0 48px; }}
    .summary {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); border-top: 3px solid #b8932f; border-bottom: 1px solid #c7bda8; background: #fff; margin-bottom: 20px; }}
    .metric {{ padding: 16px 18px; border-right: 1px solid #ddd5c5; }}
    .metric:last-child {{ border-right: 0; }}
    .metric span {{ display: block; color: #6d6459; font-size: 13px; margin-bottom: 3px; }}
    .metric strong {{ font-size: 25px; }}
    .table-wrap {{ overflow-x: auto; border: 1px solid #c7bda8; background: #fff; }}
    table {{ width: 100%; min-width: 1050px; border-collapse: collapse; font-size: 14px; }}
    th, td {{ padding: 11px 10px; border-bottom: 1px solid #ddd5c5; text-align: left; vertical-align: middle; }}
    th {{ position: sticky; top: 0; background: #ede7dd; color: #554d43; white-space: nowrap; }}
    tbody tr:last-child td {{ border-bottom: 0; }}
    tbody tr:hover {{ background: #fbf8f1; }}
    td small {{ display: block; color: #83796d; margin-top: 3px; }}
    .number {{ text-align: right; white-space: nowrap; }}
    .vacant {{ color: #9a7015; font-size: 17px; font-weight: 750; }}
    .rate-cell {{ min-width: 120px; }}
    .rate-cell strong {{ display: block; margin-bottom: 5px; }}
    .bar {{ display: block; width: 100%; height: 6px; background: #e5dfd4; overflow: hidden; }}
    .bar i {{ display: block; height: 100%; background: #b8932f; }}
    .badge {{ display: inline-block; min-width: 58px; padding: 4px 8px; text-align: center; font-size: 12px; font-weight: 750; border: 1px solid transparent; }}
    .priority-要確認 {{ color: #922f28; background: #f8e1de; border-color: #dcaaa5; }}
    .priority-注意 {{ color: #7a5812; background: #f7edce; border-color: #d9c57f; }}
    .priority-順調 {{ color: #28633f; background: #e0f0e6; border-color: #a9cfb7; }}
    .priority-満室 {{ color: #4f5960; background: #e8ecee; border-color: #c2cbd0; }}
    .change.worse {{ color: #a23830; font-weight: 700; }}
    .change.better {{ color: #26704a; font-weight: 700; }}
    a {{ color: #765714; font-weight: 700; }}
    .notes {{ margin: 16px 0 0; color: #6d6459; font-size: 13px; line-height: 1.7; }}
    @media (max-width: 720px) {{
      header div, main {{ width: min(100% - 20px, 1240px); }}
      h1 {{ font-size: 23px; }}
      .summary {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .metric {{ padding: 13px 12px; }}
      .metric:nth-child(2) {{ border-right: 0; }}
      .metric:nth-child(-n+2) {{ border-bottom: 1px solid #ddd5c5; }}
      .metric strong {{ font-size: 21px; }}
    }}
  </style>
</head>
<body>
  <header><div><h1>リーシング進捗一覧</h1><div class="meta">更新日時: {escape(str(data["generated_at"]))}</div></div></header>
  <main>
    <section class="summary" aria-label="全体集計">
      <div class="metric"><span>対象物件</span><strong>{len(rows)}件</strong></div>
      <div class="metric"><span>要確認</span><strong>{urgent_count}件</strong></div>
      <div class="metric"><span>空室合計</span><strong>{total_vacant}戸</strong></div>
      <div class="metric"><span>全体空室率</span><strong>{total_rate:.1f}%</strong></div>
    </section>
    <div class="table-wrap">
      <table>
        <thead><tr><th>優先度</th><th>物件</th><th>空室</th><th>募集対象</th><th>空室率</th><th>前回比</th><th>7日前比</th><th>2期募集</th><th>判定理由</th><th>確認</th></tr></thead>
        <tbody>
{table_rows}
        </tbody>
      </table>
    </div>
    <p class="notes">募集対象は「空室＋満室」です。非募集と2期募集は空室率から除外しています。要確認は「空室10戸以上」「空室率30%以上」「空室5戸以上かつ7日間減少なし」のいずれか、注意は「空室5戸以上」または「空室率20%以上」です。</p>
  </main>
</body>
</html>
"""
    html_path.write_text(html, encoding="utf-8")
    return {
        "path": str(html_path),
        "url": _join_url(base_url, "leasing/") if base_url else "",
        "json": str(json_path),
        "csv": str(csv_path),
        "total": len(rows),
        "urgent": urgent_count,
        "vacant": total_vacant,
    }
