"""Process-local append-only EventStore implementation for the MVP core."""

from __future__ import annotations

from typing import Any

from .sheets import TAB_HEADERS


class LocalEventStore:
    """Keep the existing EventStore shape while retaining every row in memory."""

    def __init__(self) -> None:
        self.tabs: dict[str, list[dict[str, Any]]] = {name: [] for name in TAB_HEADERS}

    def read_rows(self, tab: str) -> list[dict[str, Any]]:
        return [dict(row) for row in self.tabs[tab]]

    def append_rows(self, tab: str, rows: list[dict[str, Any]]) -> None:
        self.tabs[tab].extend(dict(row) for row in rows)

    def _append(self, tab: str, row: dict[str, Any]) -> None:
        self.tabs[tab].append(dict(row))

    def append_event(self, row: dict[str, Any]) -> None:
        self._append("06_Eventos", row)

    def append_target(self, row: dict[str, Any]) -> None:
        self._append("07_Evento_Animais", row)

    def append_calving_outcome(self, row: dict[str, Any]) -> None:
        self._append("08A_Resultados_Parto", row)

    def append_animal(self, row: dict[str, Any]) -> None:
        self._append("02_Animais", row)

    def append_identifier(self, row: dict[str, Any]) -> None:
        self._append("03_Identificadores_Animal", row)

    def append_genealogy(self, row: dict[str, Any]) -> None:
        self._append("02A_Vinculos_Genealogicos", row)

    def append_allocation(self, row: dict[str, Any]) -> None:
        self._append("05_Alocacoes", row)

    def append_conversation(self, row: dict[str, Any]) -> None:
        self._append("18_Conversas", row)

    def append_effect(self, row: dict[str, Any]) -> None:
        self._append("20_Event_Effects", row)

    def append_audit(self, row: dict[str, Any]) -> None:
        self._append("99_Audit_Log", row)

    def resolve_animal(self, property_id: str, identifier: str) -> dict[str, Any] | None:
        animals = {
            str(row.get("animal_id")): row
            for row in self.tabs["02_Animais"]
            if row.get("property_id") == property_id
        }
        if identifier in animals:
            return dict(animals[identifier])
        matches = {
            str(row.get("animal_id"))
            for row in self.tabs["03_Identificadores_Animal"]
            if row.get("property_id") == property_id
            and row.get("value") == identifier
            and not row.get("valid_to")
            and row.get("status", "ACTIVE") == "ACTIVE"
        }
        if len(matches) > 1:
            from .sheets import AmbiguousResolutionError

            raise AmbiguousResolutionError(identifier)
        animal_id = next(iter(matches), None)
        animal = animals.get(animal_id)
        return dict(animal) if animal else None

    def resolve_group(self, property_id: str, identifier: str) -> dict[str, Any] | None:
        matches = [
            row
            for row in self.tabs["04_Grupos"]
            if row.get("property_id") == property_id
            and identifier in (row.get("name"), row.get("group_id"))
            and not row.get("valid_to")
        ]
        if len(matches) > 1:
            from .sheets import AmbiguousResolutionError

            raise AmbiguousResolutionError(identifier)
        return dict(matches[0]) if matches else None

    def find_event(self, event_id: str) -> dict[str, Any] | None:
        return self._find("06_Eventos", "event_id", event_id)

    def find_event_by_command(self, command_id: str) -> dict[str, Any] | None:
        return self._find("06_Eventos", "command_id", command_id)

    def find_effect(self, idempotency_key: str) -> dict[str, Any] | None:
        return self._find("20_Event_Effects", "idempotency_key", idempotency_key)

    def _find(self, tab: str, field: str, value: str) -> dict[str, Any] | None:
        return next((dict(row) for row in reversed(self.tabs[tab]) if row.get(field) == value), None)

    def snapshot(self) -> dict[str, list[dict[str, Any]]]:
        """Return a detached snapshot suitable for inspection or JSON output."""
        return {tab: self.read_rows(tab) for tab in self.tabs}
