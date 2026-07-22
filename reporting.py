#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""自動更新結果を人間がすぐ確認できる形で公開する。"""

from __future__ import annotations

import csv
import json
from datetime import datetime
from html import escape
from pathlib import Path


REPORT_FIELDS = [
    "brand",
    "property_id",
    "property_name",
    "status",
    "page_count",
    "input_room_count",
    "rendered_room_count",
    "split_direction",
    "template",
    "error",
    "urls",
    "page_url",
]


def _join_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def _status_label(status: str) -> str:
    return "成功" if status == "success" else "要確認"


def _status_class(status: str) -> str:
    return "ok" if status == "success" else "ng"


def _csv_value(value):
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return value


def _row_sort_key(row: dict) -> tuple[int, str, str]:
    failed_first = 0 if row.get("status") != "success" else 1
    return failed_first, str(row.get("brand", "")), str(row.get("property_id", ""))


def _room_display_label(row: dict) -> str:
    input_count = int(row.get("input_room_count") or 0)
    rendered_count = int(row.get("rendered_room_count") or 0)
    missing_count = max(0, input_count - rendered_count)
    if input_count == 0:
        return "住戸データなし"
    if missing_count == 0:
        return f"全{input_count}住戸 表示完了"
    return f"住戸表示: {rendered_count} / {input_count}件（{missing_count}件未表示）"


def write_json_csv_reports(report_rows: list[dict], report_dir: Path) -> tuple[Path, Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / "update_result.json"
    csv_path = report_dir / "update_result.csv"
    json_path.write_text(json.dumps(report_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REPORT_FIELDS)
        writer.writeheader()
        for row in report_rows:
            writer.writerow({field: _csv_value(row.get(field, "")) for field in REPORT_FIELDS})
    return json_path, csv_path


def build_public_update_report(
    report_rows: list[dict],
    site_dir: Path,
    base_url: str | None = None,
    generated_at: str | None = None,
) -> dict:
    """GitHub Pagesへ公開する固定URLの更新診断ページを生成する。"""
    generated_at = generated_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    failures = [row for row in report_rows if row.get("status") != "success"]
    report_dir = site_dir / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / "latest.json"
    csv_path = report_dir / "latest.csv"
    html_path = report_dir / "index.html"

    json_path.write_text(json.dumps(report_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REPORT_FIELDS)
        writer.writeheader()
        for row in report_rows:
            writer.writerow({field: _csv_value(row.get(field, "")) for field in REPORT_FIELDS})

    sorted_rows = sorted(report_rows, key=_row_sort_key)
    summary_class = "ng" if failures else "ok"
    table_rows = "\n".join(_html_table_row(row) for row in sorted_rows)
    html = f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>募集賃料表 更新診断レポート</title>
  <style>
    body {{
      margin: 0;
      background: #f7f3ea;
      color: #3d3832;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{
      width: min(1120px, calc(100% - 32px));
      margin: 0 auto;
      padding: 28px 0 48px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 28px;
    }}
    .meta {{
      color: #5c544a;
      margin-bottom: 20px;
    }}
    .summary {{
      border-left: 6px solid #b8932f;
      background: #fff;
      padding: 16px 18px;
      margin-bottom: 22px;
    }}
    .summary.ok {{
      border-left-color: #2f8f57;
    }}
    .summary.ng {{
      border-left-color: #c4493d;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: #fff;
      font-size: 14px;
    }}
    th, td {{
      border: 1px solid #c7bda8;
      padding: 10px;
      vertical-align: top;
      text-align: left;
    }}
    th {{
      background: #ede7dd;
      white-space: nowrap;
    }}
    .badge {{
      display: inline-block;
      min-width: 52px;
      padding: 4px 8px;
      border-radius: 999px;
      text-align: center;
      font-weight: 700;
      font-size: 12px;
    }}
    .badge.ok {{
      background: #dff1e7;
      color: #20643c;
    }}
    .badge.ng {{
      background: #f9dedb;
      color: #8d2920;
    }}
    .error {{
      white-space: pre-wrap;
      color: #8d2920;
      font-weight: 700;
    }}
    a {{
      color: #8a681c;
    }}
  </style>
</head>
<body>
  <main>
    <h1>募集賃料表 更新診断レポート</h1>
    <div class="meta">生成日時: {escape(generated_at)}</div>
    <section class="summary {summary_class}">
      <strong>更新対象 {len(report_rows)}件 / 要確認 {len(failures)}件</strong><br>
      {"問題がある物件だけ確認してください。成功済みの物件は通常通り公開されています。" if failures else "全物件の更新が正常に完了しました。"}
    </section>
    <table>
      <thead>
        <tr>
          <th>状態</th>
          <th>ブランド</th>
          <th>物件ID</th>
          <th>物件名</th>
          <th>ページ</th>
          <th>住戸</th>
          <th>公開URL</th>
          <th>原因</th>
        </tr>
      </thead>
      <tbody>
{table_rows}
      </tbody>
    </table>
  </main>
</body>
</html>
"""
    html_path.write_text(html, encoding="utf-8")
    return {
        "path": str(html_path),
        "url": _join_url(base_url, "reports/") if base_url else "",
        "json": str(json_path),
        "csv": str(csv_path),
        "total": len(report_rows),
        "failed": len(failures),
    }


def _html_table_row(row: dict) -> str:
    status = str(row.get("status", ""))
    page_url = str(row.get("page_url", ""))
    page_link = f'<a href="{escape(page_url, quote=True)}">開く</a>' if page_url else ""
    room_counts = escape(_room_display_label(row))
    return f"""        <tr>
          <td><span class="badge {_status_class(status)}">{escape(_status_label(status))}</span></td>
          <td>{escape(str(row.get("brand", "")))}</td>
          <td>{escape(str(row.get("property_id", "")))}</td>
          <td>{escape(str(row.get("property_name", "")))}</td>
          <td>{escape(str(row.get("page_count", "")))}</td>
          <td>{room_counts}</td>
          <td>{page_link}</td>
          <td class="error">{escape(str(row.get("error", "")))}</td>
        </tr>"""
