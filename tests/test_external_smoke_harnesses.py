from types import SimpleNamespace

import pytest

from agro_notes.smoke_google_sheets import _round_trip_smoke


def test_sheets_smoke_uses_and_deletes_a_disposable_tab():
    calls = []

    def batch_update(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return SimpleNamespace(execute=lambda: {"replies": [{"addSheet": {"properties": {"sheetId": 41}}}]})
        return SimpleNamespace(execute=lambda: {})

    written = []
    values = SimpleNamespace(
        update=lambda **kwargs: SimpleNamespace(execute=lambda: written.append(kwargs["body"]["values"][0][0])),
        get=lambda **kwargs: SimpleNamespace(execute=lambda: {"values": [[written[0], "timestamp"]]}),
    )
    api = SimpleNamespace(batchUpdate=batch_update, values=lambda: values)
    store = SimpleNamespace(service=SimpleNamespace(spreadsheets=lambda: api), spreadsheet_id="sheet-test")

    result = _round_trip_smoke(store)

    assert result == {"status": "PASS", "spreadsheet": "sheet-test", "temporary_tab_deleted": True}
    assert calls[0]["body"]["requests"][0]["addSheet"]["properties"]["title"].startswith("_SMOKE_")
    assert calls[1]["body"]["requests"] == [{"deleteSheet": {"sheetId": 41}}]


def test_sheets_smoke_deletes_tab_after_failed_value_roundtrip():
    calls = []

    def batch_update(**kwargs):
        calls.append(kwargs)
        response = {"replies": [{"addSheet": {"properties": {"sheetId": 42}}}]} if len(calls) == 1 else {}
        return SimpleNamespace(execute=lambda: response)

    values = SimpleNamespace(
        update=lambda **kwargs: SimpleNamespace(execute=lambda: {}),
        get=lambda **kwargs: SimpleNamespace(execute=lambda: {"values": [["unexpected"]]}),
    )
    api = SimpleNamespace(batchUpdate=batch_update, values=lambda: values)
    store = SimpleNamespace(service=SimpleNamespace(spreadsheets=lambda: api), spreadsheet_id="sheet-test")

    with pytest.raises(RuntimeError, match="did not round-trip"):
        _round_trip_smoke(store)

    assert calls[-1]["body"]["requests"] == [{"deleteSheet": {"sheetId": 42}}]
