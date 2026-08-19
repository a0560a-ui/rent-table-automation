import requests

import imagekit


class FakeResponse:
    def __init__(self, status_code, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


def test_upload_retries_temporary_imagekit_error(monkeypatch, tmp_path):
    image_path = tmp_path / "price.png"
    image_path.write_bytes(b"test-image")
    responses = [
        FakeResponse(503, text="temporarily unavailable"),
        FakeResponse(
            200,
            payload={
                "fileId": "file-1",
                "url": "https://ik.imagekit.io/example/price.png",
            },
        ),
        FakeResponse(202),
    ]
    calls = []
    sleeps = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return responses.pop(0)

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr(imagekit, "imagekit_private_key", lambda: "private-key")
    monkeypatch.setattr(imagekit, "imagekit_endpoint", lambda: "https://ik.imagekit.io/example")
    monkeypatch.setattr(imagekit.time, "sleep", sleeps.append)

    url, file_id = imagekit.upload_to_imagekit(image_path, folder="/test")

    assert url == "https://ik.imagekit.io/example/price.png"
    assert file_id == "file-1"
    assert len(calls) == 3
    assert sleeps == [2]


def test_upload_does_not_retry_authentication_error(monkeypatch, tmp_path):
    image_path = tmp_path / "price.png"
    image_path.write_bytes(b"test-image")
    calls = []
    sleeps = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse(401, text="unauthorized")

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr(imagekit, "imagekit_private_key", lambda: "private-key")
    monkeypatch.setattr(imagekit, "imagekit_endpoint", lambda: "https://ik.imagekit.io/example")
    monkeypatch.setattr(imagekit.time, "sleep", sleeps.append)

    try:
        imagekit.upload_to_imagekit(image_path, folder="/test")
    except Exception as exc:
        assert "アップロード失敗: 401" in str(exc)
    else:
        raise AssertionError("401エラーが送出されませんでした")

    assert len(calls) == 1
    assert sleeps == []
