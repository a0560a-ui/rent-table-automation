#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lステップ配信用の物件別HTMLページ生成。"""

from __future__ import annotations

from html import escape
from pathlib import Path


def _join_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def _with_cache_buster(url: str, cache_buster: str | None) -> str:
    if not cache_buster:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}v={cache_buster}"


def build_property_page(
    property_id: str,
    property_name: str,
    image_urls: list[str],
    site_dir: Path,
    base_url: str | None = None,
    issue_date: str | None = None,
    cache_buster: str | None = None,
) -> dict:
    """1物件1URLで表示するためのHTMLページを生成する。"""
    page_dir = site_dir / "rent-tables" / property_id
    page_dir.mkdir(parents=True, exist_ok=True)
    html_path = page_dir / "index.html"
    title = f"{property_name} 募集賃料表"
    escaped_title = escape(title)
    image_tags = "\n".join(
        f'    <img src="{escape(_with_cache_buster(url, cache_buster), quote=True)}" alt="{escape(property_name)} 募集賃料表 {index}" loading="lazy">'
        for index, url in enumerate(image_urls, start=1)
    )
    html = f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escaped_title}</title>
  <style>
    body {{
      margin: 0;
      background: #f7f3ea;
    }}
    main {{
      width: min(100%, 1080px);
      margin: 0 auto;
      padding: 0;
    }}
    img {{
      display: block;
      width: 100%;
      height: auto;
      margin: 0;
    }}
  </style>
</head>
<body>
  <main>
{image_tags}
  </main>
</body>
</html>
"""
    html_path.write_text(html, encoding="utf-8")
    relative_path = f"rent-tables/{property_id}/"
    return {
        "path": str(html_path),
        "url": _join_url(base_url, relative_path) if base_url else "",
        "image_count": len(image_urls),
    }
