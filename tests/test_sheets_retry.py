import pytest

import sheets


class FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code


class FakeAPIError(Exception):
    def __init__(self, status_code):
        super().__init__(f"API error {status_code}")
        self.response = FakeResponse(status_code)


class FakeWorksheet:
    def __init__(self, title):
        self.title = title

    def get_all_values(self):
        return [[self.title]]


class FakeSpreadsheet:
    def worksheet(self, title):
        return FakeWorksheet(title)


class FlakyClient:
    def __init__(self, failures):
        self.failures = list(failures)
        self.calls = 0

    def open_by_key(self, _spreadsheet_id):
        self.calls += 1
        if self.failures:
            raise FakeAPIError(self.failures.pop(0))
        return FakeSpreadsheet()


def test_fetch_sheets_retries_temporary_google_errors(monkeypatch):
    client = FlakyClient([503, 429])
    sleeps = []
    monkeypatch.setattr(sheets, "_authorize_gspread", lambda: client)
    monkeypatch.setattr(sheets.time, "sleep", sleeps.append)

    result = sheets.fetch_sheets_data(
        spreadsheet_id="test-sheet",
        max_attempts=5,
        retry_base_seconds=2,
    )

    assert client.calls == 3
    assert sleeps == [2, 4]
    assert set(result) == {"properties", "types", "rooms"}


def test_fetch_sheets_does_not_retry_permission_errors(monkeypatch):
    client = FlakyClient([403])
    sleeps = []
    monkeypatch.setattr(sheets, "_authorize_gspread", lambda: client)
    monkeypatch.setattr(sheets.time, "sleep", sleeps.append)

    with pytest.raises(FakeAPIError):
        sheets.fetch_sheets_data(
            spreadsheet_id="test-sheet",
            max_attempts=5,
            retry_base_seconds=2,
        )

    assert client.calls == 1
    assert sleeps == []


def test_fetch_sheets_stops_after_max_attempts(monkeypatch):
    client = FlakyClient([503, 503, 503])
    sleeps = []
    monkeypatch.setattr(sheets, "_authorize_gspread", lambda: client)
    monkeypatch.setattr(sheets.time, "sleep", sleeps.append)

    with pytest.raises(FakeAPIError):
        sheets.fetch_sheets_data(
            spreadsheet_id="test-sheet",
            max_attempts=3,
            retry_base_seconds=1,
        )

    assert client.calls == 3
    assert sleeps == [1, 2]
