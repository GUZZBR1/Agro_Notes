"""Descriptive MVP metrics; values are reports, not release thresholds."""

from __future__ import annotations

import json
import statistics
from collections import Counter
from datetime import datetime
from typing import Any


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _instant(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else None


def summarize_metrics(
    conversations: list[dict[str, Any]],
    events: list[dict[str, Any]],
    effects: list[dict[str, Any]],
    audit: list[dict[str, Any]],
) -> dict[str, Any]:
    """Summarize operational rows while leaving human-label metrics explicitly unavailable."""
    command_ids = {str(row.get("command_id")) for row in conversations if row.get("command_id")}
    domain_commands = {
        str(row["command_id"])
        for row in conversations
        if row.get("command_id") and not str(row.get("transcript", "")).strip().startswith("/")
    }
    commands_with_clarification = {
        str(row["command_id"])
        for row in conversations
        if row.get("command_id")
        and row.get("state") == "NEEDS_CLARIFICATION"
        and str(row["command_id"]) in domain_commands
    }
    latest_events: dict[str, dict[str, Any]] = {}
    applied_versions: Counter[str] = Counter()
    for row in events:
        event_id = str(row.get("event_id") or "")
        if not event_id:
            continue
        latest_events[event_id] = row
        if row.get("processing_status") == "APPLIED":
            applied_versions[event_id] += 1
    attempted = [
        row for row in latest_events.values() if row.get("processing_status") in {"APPLIED", "PARTIALLY_APPLIED"}
    ]
    corrected = [row for row in latest_events.values() if row.get("correction_of")]
    duplicate_applied = sum(count > 1 for count in applied_versions.values())

    latest_effects: dict[str, dict[str, Any]] = {}
    for row in effects:
        key = str(row.get("idempotency_key") or row.get("effect_id") or "")
        if key:
            latest_effects[key] = row

    duplicate_deliveries = sum(row.get("action") == "DUPLICATE_DELIVERY" for row in audit)
    history_queries = [
        row for row in conversations if str(row.get("transcript", "")).strip().lower().startswith("/historico")
    ]
    answered_history_queries = sum(row.get("state") == "COMPLETED" for row in history_queries)
    history_data_found = sum(str(row.get("response", "")).startswith("Histórico de ") for row in history_queries)

    first_received: dict[str, datetime] = {}
    terminal: dict[str, dict[str, Any]] = {}
    for row in conversations:
        command_id = str(row.get("command_id") or "")
        if not command_id:
            continue
        received = _instant(row.get("received_at"))
        if received and (command_id not in first_received or received < first_received[command_id]):
            first_received[command_id] = received
        if row.get("state") in {"COMPLETED", "PARTIALLY_APPLIED"}:
            try:
                event_ids = json.loads(row.get("event_ids") or "[]")
            except (TypeError, ValueError):
                event_ids = []
            if event_ids:
                terminal[command_id] = row
    durations = []
    for command_id, row in terminal.items():
        received = first_received.get(command_id)
        resolved = _instant(row.get("resolved_at"))
        if received and resolved:
            durations.append(max(0.0, (resolved - received).total_seconds()))

    return {
        "commands_total": len(command_ids),
        "events_total": len(latest_events),
        "events_applied": sum(row.get("processing_status") == "APPLIED" for row in latest_events.values()),
        "clarification_rate": _ratio(len(commands_with_clarification), len(domain_commands)),
        "correction_rate": _ratio(len(corrected), len(latest_events)),
        "duplicate_deliveries": duplicate_deliveries,
        "duplicate_applied_event_rate": _ratio(duplicate_applied, sum(applied_versions.values())),
        "partial_effect_rate": _ratio(
            sum(row.get("processing_status") == "PARTIALLY_APPLIED" for row in attempted), len(attempted)
        ),
        "reversed_effect_rate": _ratio(
            sum(row.get("status") == "REVERSED" for row in latest_effects.values()), len(latest_effects)
        ),
        "history_query_response_rate": _ratio(answered_history_queries, len(history_queries)),
        "history_data_found_rate": _ratio(history_data_found, len(history_queries)),
        "time_to_record_seconds_median": statistics.median(durations) if durations else None,
        "intent_accuracy": None,
        "slot_extraction_accuracy": None,
        "animal_resolution_accuracy": None,
        "useful_clarification_rate": None,
        "human_label_metrics_note": "These metrics require reviewed golden-set annotations.",
    }


def main() -> None:
    from .settings import get_settings
    from .sheets import GoogleSheetsStore

    store = GoogleSheetsStore.from_credentials(get_settings())
    snapshot = summarize_metrics(
        conversations=store.read_rows("18_Conversas"),
        events=store.read_rows("06_Eventos"),
        effects=store.read_rows("20_Event_Effects"),
        audit=store.read_rows("99_Audit_Log"),
    )
    print(json.dumps(snapshot, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
