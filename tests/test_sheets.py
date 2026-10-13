import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from agro_notes.sheets import (
    TAB_HEADERS,
    AmbiguousResolutionError,
    GoogleSheetsStore,
    SchemaMismatchError,
)


class Request:
    def __init__(self, result):
        self.result = result

    def execute(self):
        return self.result


class FakeSheets:
    """In-memory API shape; no Google dependencies or network credentials."""

    def __init__(self):
        self.tabs = {}
        self.appends = []
        self.header_updates = []

    def spreadsheets(self):
        return self

    def values(self):
        return self

    @staticmethod
    def tab_name(range_name):
        return range_name.split("!")[0].strip("'")

    def get(self, **kwargs):
        if "range" not in kwargs:
            return Request({"sheets": [{"properties": {"title": tab}} for tab in self.tabs]})
        rows = self.tabs.get(self.tab_name(kwargs["range"]), [])
        if kwargs["range"].endswith("1"):
            rows = rows[:1]
        return Request({"values": rows})

    def batchUpdate(self, **kwargs):
        body = kwargs["body"]
        if "requests" in body:
            for request in body["requests"]:
                self.tabs[request["addSheet"]["properties"]["title"]] = []
        else:
            self.header_updates.append(kwargs)
            for update in body["data"]:
                self.tabs[self.tab_name(update["range"])] = update["values"]
        return Request({})

    def append(self, **kwargs):
        self.appends.append(kwargs)
        self.tabs[self.tab_name(kwargs["range"])].extend(kwargs["body"]["values"])
        return Request({"updates": {"updatedRows": len(kwargs["body"]["values"])}})


class SheetsTests(unittest.TestCase):
    def setUp(self):
        self.api = FakeSheets()
        self.store = GoogleSheetsStore("spreadsheet", service=self.api)
        self.store.bootstrap()

    def test_bootstrap_is_repeatable_and_does_not_erase_data(self):
        self.store.append_animal({"animal_id": "animal", "property_id": "farm", "birth_property_id": "farm"})
        self.store.bootstrap()
        self.assertEqual(set(TAB_HEADERS), set(self.api.tabs))
        self.assertEqual(len(self.api.header_updates), 1)
        self.assertEqual(self.store.read_rows("02_Animais")[0]["animal_id"], "animal")

    def test_existing_wrong_headers_fail_without_overwrite(self):
        self.api.tabs["02_Animais"] = [["wrong"], ["preserve"]]
        with self.assertRaises(SchemaMismatchError):
            self.store.bootstrap()
        self.assertEqual(self.api.tabs["02_Animais"], [["wrong"], ["preserve"]])

    def test_append_uses_raw_and_preserves_text_ids_and_formula_text(self):
        self.store.append_identifier({"identifier_id": "id", "value": "00123", "issuer": "=1+1"})
        call = self.api.appends[-1]
        self.assertEqual(call["valueInputOption"], "RAW")
        self.assertEqual(call["insertDataOption"], "INSERT_ROWS")
        row = self.store.read_rows("03_Identificadores_Animal")[0]
        self.assertEqual(row["value"], "00123")
        self.assertEqual(row["issuer"], "=1+1")

    def test_unknown_columns_rejected_before_write(self):
        with self.assertRaises(ValueError):
            self.store.append_animal({"not_a_column": "value"})
        self.assertEqual(self.api.appends, [])

    def test_read_pads_missing_trailing_cells_and_skips_blank_rows(self):
        self.api.tabs["02_Animais"].extend([["animal"], [], [""]])
        rows = self.store.read_rows("02_Animais")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["created_at"], "")

    def test_animal_identifiers_are_property_scoped_and_ambiguity_is_explicit(self):
        for animal_id, property_id in [("a", "farm1"), ("b", "farm2"), ("c", "farm1")]:
            self.store.append_animal(
                {
                    "animal_id": animal_id,
                    "property_id": property_id,
                    "birth_property_id": property_id,
                }
            )
            self.store.append_identifier({"animal_id": animal_id, "value": "42", "status": "ACTIVE"})
        self.assertEqual(self.store.resolve_animal("farm2", "42")["animal_id"], "b")
        self.assertIsNone(self.store.resolve_animal("farm2", "a"))
        with self.assertRaises(AmbiguousResolutionError):
            self.store.resolve_animal("farm1", "42")

    def test_expired_and_wrong_property_identifier_are_ignored(self):
        self.store.append_animal({"animal_id": "a", "property_id": "farm", "birth_property_id": "farm"})
        self.store.append_identifier({"animal_id": "a", "value": "42", "valid_to": "2026-01-01"})
        self.store.append_identifier({"animal_id": "a", "value": "43", "property_id": "other"})
        self.assertIsNone(self.store.resolve_animal("farm", "42"))
        self.assertIsNone(self.store.resolve_animal("farm", "43"))

    def test_group_resolves_within_property(self):
        self.store.append_rows(
            "04_Grupos",
            [
                {"group_id": "g1", "property_id": "p1", "name": "Lote 1"},
                {"group_id": "g2", "property_id": "p2", "name": "Lote 1"},
            ],
        )
        self.assertEqual(self.store.resolve_group("p1", "Lote 1")["group_id"], "g1")
        self.assertIsNone(self.store.resolve_group("p1", "g2"))

    def test_command_event_and_latest_effect_lookups(self):
        self.store.append_event({"event_id": "event", "command_id": "command"})
        self.assertEqual(self.store.find_command("command")["event_id"], "event")
        self.assertEqual(self.store.find_event_by_command("command")["event_id"], "event")
        self.assertEqual(self.store.find_event("event")["command_id"], "command")
        self.assertIsNone(self.store.find_event(command_id="absent"))
        self.store.append_effect({"idempotency_key": "effect", "status": "PENDING"})
        self.store.append_effect({"idempotency_key": "effect", "status": "APPLIED"})
        self.assertEqual(self.store.find_effect("effect")["status"], "APPLIED")

    def test_event_lookup_returns_latest_appended_version(self):
        self.store.append_event({"event_id": "event", "command_id": "command", "processing_status": "PENDING"})
        self.store.append_event({"event_id": "event", "command_id": "command", "processing_status": "APPLIED"})
        self.store.append_event({"event_id": "other", "command_id": "other", "processing_status": "PENDING"})
        self.assertEqual(self.store.find_event("event")["processing_status"], "APPLIED")
        self.assertEqual(self.store.find_event_by_command("command")["processing_status"], "APPLIED")
        self.assertIsNone(self.store.find_event("event", command_id="other"))

    def test_reconstruction_payload_headers_are_bootstrapped_and_preserved(self):
        self.assertIn("event_payload_json", self.api.tabs["06_Eventos"][0])
        self.assertIn("pending_command_json", self.api.tabs["18_Conversas"][0])
        self.store.append_event({"event_id": "e", "event_payload_json": {"product": "UNKNOWN"}})
        self.store.append_conversation({"message_id": "m", "pending_command_json": {"command_id": "c"}})
        self.assertEqual(self.store.read_rows("06_Eventos")[0]["event_payload_json"], '{"product": "UNKNOWN"}')
        self.assertEqual(self.store.read_rows("18_Conversas")[0]["pending_command_json"], '{"command_id": "c"}')

    def test_structured_conversation_fields_are_encoded_as_json(self):
        self.store.append_conversation({"message_id": "m", "event_ids": ["e1", "e2"]})
        self.assertEqual(self.store.read_rows("18_Conversas")[0]["event_ids"], '["e1", "e2"]')

    def test_service_account_factory_accepts_injected_builder(self):
        credentials = Mock()
        credentials.from_service_account_file.return_value = "loaded-credentials"
        module = SimpleNamespace(Credentials=credentials)
        builder = Mock(return_value=self.api)
        settings = SimpleNamespace(google_sheet_id="sheet", google_credentials_file="service.json")
        with patch.dict("sys.modules", {"google.oauth2.service_account": module}):
            store = GoogleSheetsStore.from_credentials(settings, api_builder=builder)
        self.assertEqual(store.spreadsheet_id, "sheet")
        credentials.from_service_account_file.assert_called_once_with(
            "service.json", scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        builder.assert_called_once_with("sheets", "v4", credentials="loaded-credentials", cache_discovery=False)


if __name__ == "__main__":
    unittest.main()
