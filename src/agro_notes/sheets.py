"""Append-only MVP storage backed by Sheets.

Idempotency lookups are advisory: Sheets has no unique constraints and these
operations are not a transaction across tabs. The application must serialize
writers and reconcile partial writes rather than blindly retrying a command.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

TAB_HEADERS: dict[str, tuple[str, ...]] = {
    "00_Config": tuple(
        "config_id property_id domain code label valid_from valid_to source_ref approved_by updated_at".split()
    ),
    "01_Propriedades": tuple(
        "property_id nome municipio UF timezone owner_id operator_id sistema_producao identification_regime created_at".split()  # noqa: E501
    ),
    "02_Animais": tuple(
        "animal_id property_id birth_property_id species sex birth_date birth_date_precision birth_source breed genetic_composition origin_type first_entry_date entry_event_id evidence_status created_at".split()  # noqa: E501
    ),
    "02A_Vinculos_Genealogicos": tuple(
        "relationship_id property_id descendant_animal_id parent_animal_id parent_role certainty source_event_id effective_at evidence_ref correction_of".split()  # noqa: E501
    ),
    "03_Identificadores_Animal": tuple(
        "identifier_id property_id animal_id scheme value issuer valid_from valid_to status source_event_id evidence_ref".split()  # noqa: E501
    ),
    "04_Grupos": tuple(
        "group_id property_id name group_type purpose valid_from valid_to area_id cost_center_id".split()
    ),
    "05_Alocacoes": tuple(
        "allocation_id property_id animal_id group_id location_id effective_from effective_to reason event_id recorded_at".split()  # noqa: E501
    ),
    "06_Eventos": tuple(
        "event_id event_type occurred_from occurred_to time_precision time_source timezone original_time_expression recorded_at actor_id channel target_scope property_id source_message_id evidence_ref interpretation_confirmation evidence_status event_status command_id correction_of processing_status event_payload_json".split()  # noqa: E501
    ),
    "07_Evento_Animais": tuple(
        "event_target_id property_id event_id animal_id group_id target_basis membership_snapshot_id observed_at outcome target_confidence".split()  # noqa: E501
    ),
    "08A_Resultados_Parto": tuple(
        "outcome_id property_id event_id outcome_type live_status animal_id sex birth_weight weight_unit parentage_certainty evidence_ref correction_of".split()  # noqa: E501
    ),
    "09_Casos_Saude": tuple(
        "health_case_id property_id scope animal_id group_id opening_event_id closing_event_id observed_signs suspected_condition confirmed_diagnosis diagnosis_source status opened_at closed_at outcome responsible_id".split()  # noqa: E501
    ),
    "10_Administracoes": tuple(
        "administration_id property_id event_id health_case_id product_id product_lot_id dose dose_unit route administered_at administrator_id instruction_source withdrawal_start withdrawal_end withdrawal_source".split()  # noqa: E501
    ),
    "18_Conversas": tuple(
        "message_id property_id command_id user_id channel received_at captured_at device_timezone resolved_at raw_text_ref audio_ref transcript transcript_confidence interpretation_id intents entity_candidates missing_fields confirmation_prompt response model/version state event_ids pending_command_json callback_chat_id callback_message_id".split()  # noqa: E501
    ),
    "19_Usuarios": tuple(
        "user_id display_name role property_id permissions_profile active valid_from valid_to".split()
    ),
    "20_Event_Effects": tuple(
        "effect_id property_id source_event_id effect_type target_type target_id idempotency_key status attempt_count retryable error before_ref after_ref reversed_by updated_at".split()  # noqa: E501
    ),
    "99_Audit_Log": tuple(
        "audit_id property_id command_id timestamp actor channel raw_message_ref transcript_ref interpretation confirmation event_ids affected_record_ids action prior_state_ref resulting_state_ref error correction_of idempotency_key".split()  # noqa: E501
    ),
}


class SchemaMismatchError(ValueError):
    """An existing tab does not match the supported schema."""


class AmbiguousResolutionError(ValueError):
    """More than one entity matches an identifier within a property."""


def _column(number: int) -> str:
    result = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _cell(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (Mapping, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


class GoogleSheetsStore:
    def __init__(
        self,
        spreadsheet_id: str,
        service_account_path: str | Path | None = None,
        *,
        service: Any = None,
        api_builder: Any = None,
    ):
        if not spreadsheet_id:
            raise ValueError("spreadsheet_id is required")
        self.spreadsheet_id = spreadsheet_id
        if service is None:
            if service_account_path is None:
                raise ValueError("service or service_account_path is required")
            from google.oauth2.service_account import Credentials

            if api_builder is None:
                from googleapiclient.discovery import build

                api_builder = build
            credentials = Credentials.from_service_account_file(
                str(service_account_path), scopes=["https://www.googleapis.com/auth/spreadsheets"]
            )
            service = api_builder("sheets", "v4", credentials=credentials, cache_discovery=False)
        self.service = service

    @classmethod
    def from_credentials(cls, settings: Any, *, api_builder: Any = None) -> GoogleSheetsStore:
        return cls(settings.google_sheet_id, settings.google_credentials_file, api_builder=api_builder)

    def _range(self, tab: str, *, header_only: bool = False) -> str:
        headers = TAB_HEADERS[tab]
        suffix = "1" if header_only else ""
        return f"'{tab}'!A1:{_column(len(headers))}{suffix}"

    def _values(self, tab: str, *, header_only: bool = False) -> list[list[Any]]:
        response = (
            self.service.spreadsheets()
            .values()
            .get(
                spreadsheetId=self.spreadsheet_id,
                range=self._range(tab, header_only=header_only),
                valueRenderOption="UNFORMATTED_VALUE",
            )
            .execute()
        )
        return response.get("values", [])

    def bootstrap(self) -> None:
        sheets = self.service.spreadsheets()
        metadata = sheets.get(spreadsheetId=self.spreadsheet_id, fields="sheets.properties.title").execute()
        existing = {sheet["properties"]["title"] for sheet in metadata.get("sheets", [])}
        requests = [{"addSheet": {"properties": {"title": tab}}} for tab in TAB_HEADERS if tab not in existing]
        if requests:
            sheets.batchUpdate(spreadsheetId=self.spreadsheet_id, body={"requests": requests}).execute()
        updates = []
        for tab, headers in TAB_HEADERS.items():
            values = self._values(tab, header_only=True)
            if values and tuple(values[0]) != headers:
                raise SchemaMismatchError(f"Unexpected headers in {tab}; existing data was not overwritten")
            if not values:
                updates.append({"range": self._range(tab, header_only=True), "values": [list(headers)]})
        if updates:
            sheets.values().batchUpdate(
                spreadsheetId=self.spreadsheet_id, body={"valueInputOption": "RAW", "data": updates}
            ).execute()

    ensure_schema = bootstrap

    def read_rows(self, tab: str) -> list[dict[str, Any]]:
        values = self._values(tab)
        if not values:
            return []
        headers = TAB_HEADERS[tab]
        if tuple(values[0]) != headers:
            raise SchemaMismatchError(f"Unexpected headers in {tab}")
        return [
            dict(zip(headers, row + [""] * (len(headers) - len(row)), strict=False))
            for row in values[1:]
            if any(value != "" for value in row)
        ]

    def append_rows(self, tab: str, rows: Sequence[Mapping[str, Any]]) -> Any:
        headers = TAB_HEADERS[tab]
        if not rows:
            return None
        for row in rows:
            unknown = set(row) - set(headers)
            if unknown:
                raise ValueError(f"Unknown columns in {tab}: {sorted(unknown)}")
        actual = self._values(tab, header_only=True)
        if not actual or tuple(actual[0]) != headers:
            raise SchemaMismatchError(f"Missing or unexpected headers in {tab}; run bootstrap first")
        return (
            self.service.spreadsheets()
            .values()
            .append(
                spreadsheetId=self.spreadsheet_id,
                range=self._range(tab),
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={
                    "majorDimension": "ROWS",
                    "values": [[_cell(row.get(key)) for key in headers] for row in rows],
                },
            )
            .execute()
        )

    def lookup_animals(self, property_id: str, identifier: str) -> list[dict[str, Any]]:
        if not property_id or not identifier:
            return []
        animals = {
            str(row["animal_id"]): row for row in self.read_rows("02_Animais") if row["property_id"] == property_id
        }
        matches = {identifier} if identifier in animals else set()
        for row in self.read_rows("03_Identificadores_Animal"):
            if (
                str(row["value"]) == identifier
                and row["animal_id"] in animals
                and row.get("property_id") in ("", property_id)
                and not row["valid_to"]
                and str(row["status"]).upper() not in {"INACTIVE", "REVOKED", "REPLACED"}
            ):
                matches.add(row["animal_id"])
        return [animals[key] for key in sorted(matches)]

    def resolve_animal(self, property_id: str, identifier: str) -> dict[str, Any] | None:
        matches = self.lookup_animals(property_id, identifier)
        if len(matches) > 1:
            raise AmbiguousResolutionError(f"Animal identifier {identifier!r} is ambiguous in {property_id!r}")
        return matches[0] if matches else None

    def resolve_group(self, property_id: str, group_identifier: str) -> dict[str, Any] | None:
        if not property_id or not group_identifier:
            return None
        matches = [
            row
            for row in self.read_rows("04_Grupos")
            if row["property_id"] == property_id
            and not row["valid_to"]
            and group_identifier in (row["group_id"], row["name"])
        ]
        if len(matches) > 1:
            raise AmbiguousResolutionError(f"Group {group_identifier!r} is ambiguous in {property_id!r}")
        return matches[0] if matches else None

    def find_event(self, event_id: str | None = None, *, command_id: str | None = None) -> dict[str, Any] | None:
        """Return the latest appended version matching all supplied IDs."""
        if not event_id and not command_id:
            raise ValueError("event_id or command_id is required")
        return next(
            (
                row
                for row in reversed(self.read_rows("06_Eventos"))
                if (not event_id or row["event_id"] == event_id) and (not command_id or row["command_id"] == command_id)
            ),
            None,
        )

    def find_event_by_command(self, command_id: str) -> dict[str, Any] | None:
        return self.find_event(command_id=command_id)

    def find_command(self, command_id: str) -> dict[str, Any] | None:
        if not command_id:
            raise ValueError("command_id is required")
        for tab in ("06_Eventos", "99_Audit_Log", "18_Conversas"):
            match = next((row for row in self.read_rows(tab) if row["command_id"] == command_id), None)
            if match:
                return match
        return None

    def find_effect(self, idempotency_key: str) -> dict[str, Any] | None:
        if not idempotency_key:
            raise ValueError("idempotency_key is required")
        matches = [row for row in self.read_rows("20_Event_Effects") if row["idempotency_key"] == idempotency_key]
        return matches[-1] if matches else None

    def append_event(self, row: Mapping[str, Any]) -> Any:
        return self.append_rows("06_Eventos", [row])

    def append_target(self, row: Mapping[str, Any]) -> Any:
        return self.append_rows("07_Evento_Animais", [row])

    def append_calving_outcome(self, row: Mapping[str, Any]) -> Any:
        return self.append_rows("08A_Resultados_Parto", [row])

    def append_animal(self, row: Mapping[str, Any]) -> Any:
        return self.append_rows("02_Animais", [row])

    def append_identifier(self, row: Mapping[str, Any]) -> Any:
        return self.append_rows("03_Identificadores_Animal", [row])

    def append_genealogy(self, row: Mapping[str, Any]) -> Any:
        return self.append_rows("02A_Vinculos_Genealogicos", [row])

    def append_allocation(self, row: Mapping[str, Any]) -> Any:
        return self.append_rows("05_Alocacoes", [row])

    def append_conversation(self, row: Mapping[str, Any]) -> Any:
        return self.append_rows("18_Conversas", [row])

    def append_effect(self, row: Mapping[str, Any]) -> Any:
        return self.append_rows("20_Event_Effects", [row])

    def append_audit(self, row: Mapping[str, Any]) -> Any:
        return self.append_rows("99_Audit_Log", [row])
