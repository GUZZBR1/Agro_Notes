from agro_notes.metrics import summarize_metrics


def test_operational_metrics_derive_rates_and_preserve_unlabeled_fields():
    conversations = [
        {"command_id": "c1", "state": "NEEDS_CLARIFICATION", "received_at": "2026-01-01T00:00:00+00:00"},
        {
            "command_id": "c1",
            "state": "COMPLETED",
            "received_at": "2026-01-01T00:00:05+00:00",
            "resolved_at": "2026-01-01T00:00:15+00:00",
            "event_ids": '["e1"]',
        },
        {"command_id": "c2", "state": "COMPLETED", "transcript": "/historico 184", "response": "Histórico de 184:"},
    ]
    events = [
        {"event_id": "e1", "processing_status": "APPLYING"},
        {"event_id": "e1", "processing_status": "APPLIED"},
        {"event_id": "e2", "processing_status": "PARTIALLY_APPLIED"},
        {"event_id": "e3", "processing_status": "APPLIED", "correction_of": "e1"},
    ]
    effects = [{"idempotency_key": "effect-1", "status": "REVERSED"}]
    audit = [{"action": "DUPLICATE_DELIVERY"}]

    result = summarize_metrics(conversations, events, effects, audit)

    assert result["commands_total"] == 2
    assert result["clarification_rate"] == 1
    assert result["correction_rate"] == 1 / 3
    assert result["partial_effect_rate"] == 1 / 3
    assert result["duplicate_deliveries"] == 1
    assert result["history_query_response_rate"] == 1
    assert result["history_data_found_rate"] == 1
    assert result["time_to_record_seconds_median"] == 15
    assert result["intent_accuracy"] is None
    assert result["useful_clarification_rate"] is None
