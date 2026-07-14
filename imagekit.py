#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ImageKit.io アップロード。"""

from __future__ import annotations

import base64
import os

from config import IMAGEKIT_PRICE_TABLE_FOLDER, MAX_FIXED_PAGE_SLOTS, imagekit_endpoint, imagekit_private_key


def upload_to_imagekit(file_path, brand_name=None, folder=None, file_name=None):
    import requests

    private_key = imagekit_private_key()
    delivery_endpoint = (imagekit_endpoint() or "").rstrip("/")
    if not private_key or not delivery_endpoint:
        raise RuntimeError("IMAGEKIT_PRIVATE_KEY と IMAGEKIT_URL_ENDPOINT を設定してください")

    filename = file_name or os.path.basename(file_path)
    folder = folder or f"/lstep/{brand_name}"
    with open(file_path, "rb") as f:
        file_data = base64.b64encode(f.read()).decode("utf-8")

    auth = base64.b64encode(f"{private_key}:".encode()).decode()
    payload = {
        "file": file_data,
        "fileName": filename,
        "folder": folder,
        "useUniqueFileName": "false",
        "overwriteFile": "true",
        "overwriteAITags": "false",
        "overwriteTags": "false",
        "overwriteCustomMetadata": "false",
    }
    response = requests.post(
        "https://upload.imagekit.io/api/v1/files/upload",
        headers={"Authorization": f"Basic {auth}"},
        data=payload,
        timeout=30,
    )
    if response.status_code != 200:
        raise Exception(f"❌ アップロード失敗: {response.status_code}\n{response.text}")

    result = response.json()
    file_id = result["fileId"]
    url = result["url"]

    purge_response = requests.post(
        "https://api.imagekit.io/v1/files/purge",
        headers={"Authorization": f"Basic {auth}"},
        data={"url": url},
        timeout=30,
    )
    if purge_response.status_code not in {200, 201, 202}:
        print(f"⚠️ キャッシュパージ失敗: {purge_response.status_code}")
    return url, file_id


def fixed_page_filename(prop_id, page_number):
    return f"{prop_id}_{page_number:02d}.png"


def upload_fixed_page_set(prop_id, pages, placeholder_paths=None, folder=None, max_slots=None):
    """物件ごとの固定URL枠へページ画像を上書きアップロードする。"""
    folder = folder or f"{IMAGEKIT_PRICE_TABLE_FOLDER}/{prop_id}"
    max_slots = max_slots or MAX_FIXED_PAGE_SLOTS
    if len(pages) > max_slots:
        raise ValueError(f"{prop_id} のページ数 {len(pages)} が最大固定枠 {max_slots} を超えています")

    placeholder_paths = placeholder_paths or []
    results = []
    for slot in range(1, max_slots + 1):
        if slot <= len(pages):
            source_path = pages[slot - 1]["path"]
            active = True
        else:
            if not placeholder_paths:
                continue
            source_path = placeholder_paths[min(slot - len(pages) - 1, len(placeholder_paths) - 1)]
            active = False
        file_name = fixed_page_filename(prop_id, slot)
        url, file_id = upload_to_imagekit(source_path, folder=folder, file_name=file_name)
        results.append(
            {
                "slot": slot,
                "active": active,
                "file_name": file_name,
                "url": url,
                "file_id": file_id,
            }
        )
    return results
