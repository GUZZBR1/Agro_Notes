"""Verify canonical Sheets schema and a disposable write/read/delete cycle."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from .settings import get_settings
from .sheets import GoogleSheetsStore


def smoke() -> dict[str, object]:
    settings = get_settings()
    if not settings.google_sheet_id.strip():
        return {"status": "WAITING_FOR_EXTERNAL_CREDENTIALS", "required": "GOOGLE_SHEET_ID"}
    store = GoogleSheetsStore.from_credentials(settings)
    store.bootstrap()
    return _round_trip_smoke(store)


def _round_trip_smoke(store: GoogleSheetsStore) -> dict[str, object]:
    service = store.service.spreadsheets()
    title = f"_SMOKE_{uuid4().hex[:12]}"
    sheet_id = None
    try:
        created = service.batchUpdate(
            spreadsheetId=store.spreadsheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": title}}}]},
        ).execute()
        sheet_id = created["replies"][0]["addSheet"]["properties"]["sheetId"]
        marker = uuid4().hex
        service.values().update(
            spreadsheetId=store.spreadsheet_id,
            range=f"'{title}'!A1:B1",
            valueInputOption="RAW",
            body={"values": [[marker, datetime.now(UTC).isoformat()]]},
        ).execute()
        read_back = service.values().get(
            spreadsheetId=store.spreadsheet_id,
            range=f"'{title}'!A1:B1",
            valueRenderOption="UNFORMATTED_VALUE",
        ).execute().get("values", [])
        if not read_back or read_back[0][0] != marker:
            raise RuntimeError("Temporary Sheets smoke value did not round-trip.")
        return {"status": "PASS", "spreadsheet": store.spreadsheet_id, "temporary_tab_deleted": True}
    finally:
        if sheet_id is not None:
            service.batchUpdate(
                spreadsheetId=store.spreadsheet_id,
                body={"requests": [{"deleteSheet": {"sheetId": sheet_id}}]},
            ).execute()


def main() -> None:
    try:
        result = smoke()
    except Exception as exc:
        result = {"status": "FAILED", "reason": type(exc).__name__}
    print(json.dumps(result, ensure_ascii=False))
    if result["status"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
