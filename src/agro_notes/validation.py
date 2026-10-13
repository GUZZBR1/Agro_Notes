"""Deterministic checks at the boundary between proposals and persistence."""

from datetime import date, timedelta
from zoneinfo import ZoneInfo

from pydantic import ValidationError

from .domain import (
    PAYLOAD_MODELS,
    EventType,
    InterpretationProposal,
    TimeSource,
    TrustedContext,
    ValidatedEvent,
    ValidationResult,
    ValidationStatus,
)

REQUIRED = {
    EventType.ANIMAL_CREATED: ("display_identifier", "species"),
    EventType.ANIMAL_ENTERED: ("display_identifier",),
    EventType.CALVING: ("mother_identifier", "outcomes"),
    EventType.WEIGHING: ("animal_identifier", "weight_kg"),
    EventType.LOT_TRANSFER: ("animal_identifier", "to_group_identifier"),
    EventType.VACCINATION: ("vaccine",),
    EventType.HEALTH_OBSERVATION: ("animal_identifier", "observation"),
}
EXPLICIT_DATE_REQUIRED = {EventType.WEIGHING}


def resolve_date(expression: str | None, context: TrustedContext) -> date | None:
    if not expression or not expression.strip():
        return None
    if context.now.tzinfo is None:
        raise ValueError("TrustedContext.now must be timezone-aware")
    today = context.now.astimezone(ZoneInfo(context.timezone)).date()
    value = expression.strip().lower()
    if value in {"hoje", "today"}:
        return today
    if value in {"ontem", "yesterday"}:
        return today - timedelta(days=1)
    if value in {"amanhã", "amanha", "tomorrow"}:
        return today + timedelta(days=1)
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


class DeterministicValidator:
    def __init__(self, confidence_threshold: float = 0.8):
        if not 0 <= confidence_threshold <= 1:
            raise ValueError("confidence_threshold must be between 0 and 1")
        self.confidence_threshold = confidence_threshold

    def validate(self, proposal: InterpretationProposal, context: TrustedContext) -> ValidationResult:
        proposal = InterpretationProposal.model_validate(proposal).model_copy(deep=True)
        errors: list[str] = []
        missing: list[str] = []
        questions = list(proposal.ambiguities)
        normalized: list[tuple] = []
        preview = bool(questions) or len(proposal.events) > 1
        if proposal.out_of_scope:
            errors.append("A solicitação contém eventos fora do escopo do MVP.")
        if not proposal.events:
            questions.append("Informe o evento a registrar.")
        for index, event in enumerate(proposal.events):
            prefix = f"events[{index}]"
            # Never allow model-supplied tenant or audit identity to reach persistence.
            event.property_id = context.property_id
            event.actor_id = context.actor_id
            event.event_id = None
            try:
                family = EventType(event.event_type)
            except ValueError:
                errors.append(f"{prefix}.event_type: evento fora do escopo: {event.event_type}")
                continue
            preview = preview or family not in {EventType.WEIGHING, EventType.HEALTH_OBSERVATION}
            try:
                payload = PAYLOAD_MODELS[family].model_validate(event.payload).model_dump()
            except ValidationError as exc:
                errors.append(f"{prefix}.payload: {exc}")
                continue
            event.payload = payload
            if family == EventType.ANIMAL_CREATED and payload.get("birth_date"):
                try:
                    date.fromisoformat(payload["birth_date"])
                except ValueError:
                    questions.append("Confirme a data de nascimento no formato AAAA-MM-DD.")
            for field in REQUIRED[family]:
                value = payload.get(field)
                if value is None or value == [] or (isinstance(value, str) and not value.strip()):
                    missing.append(f"{prefix}.payload.{field}")
            if family == EventType.VACCINATION:
                has_animal = bool(payload.get("animal_identifier"))
                has_group = bool(payload.get("group_identifier"))
                if has_animal == has_group:
                    if has_animal:
                        errors.append(f"{prefix}.payload: informe animal ou lote, não ambos.")
                    else:
                        missing.append(f"{prefix}.payload.animal_identifier ou group_identifier")
            if event.confidence is None or event.confidence < self.confidence_threshold:
                questions.append(f"Confirme a interpretação do evento {index + 1}.")
            questions.extend(event.ambiguities)
            preview = preview or bool(event.ambiguities) or bool(event.correction_of) or event.correction_requested
            if family == EventType.CALVING:
                preview = True
                count = payload["outcome_count"]
                if count is not None and count != len(payload["outcomes"]):
                    questions.append("Informe todos os resultados do parto e confirme a quantidade.")
                for outcome_index, outcome in enumerate(payload["outcomes"]):
                    if not outcome["outcome"] or not outcome["outcome"].strip():
                        missing.append(f"{prefix}.payload.outcomes[{outcome_index}].outcome")
            if family in {EventType.VACCINATION, EventType.HEALTH_OBSERVATION}:
                if payload["status"] != "REPORTED":
                    errors.append(f"{prefix}.payload.status: apenas REPORTED é permitido.")
            if (
                family == EventType.LOT_TRANSFER
                and payload["to_group_identifier"]
                and payload["from_group_identifier"] == payload["to_group_identifier"]
            ):
                errors.append(f"{prefix}: o lote de destino deve ser diferente do lote de origem.")
            if event._inherited_occurrence_date is not None:
                occurred_on = event._inherited_occurrence_date
                time_source = TimeSource.INHERITED_FROM_CORRECTED_EVENT
            elif not event.time_expression or not event.time_expression.strip():
                time_source = TimeSource.INFERRED_FROM_CAPTURE_DATE
                if family in EXPLICIT_DATE_REQUIRED:
                    occurred_on = None
                else:
                    if context.now.tzinfo is None:
                        raise ValueError("TrustedContext.now must be timezone-aware")
                    occurred_on = context.inferred_on or context.now.astimezone(ZoneInfo(context.timezone)).date()
            else:
                time_source = TimeSource.EXPLICIT
                time_context = (
                    context.model_copy(update={"now": event._time_expression_captured_at})
                    if event._time_expression_captured_at
                    else context
                )
                occurred_on = resolve_date(event.time_expression, time_context)
            if occurred_on is None:
                missing.append(f"{prefix}.time_expression")
            normalized.append((family, payload, occurred_on, time_source))
        if errors:
            status = ValidationStatus.REJECTED
        elif missing or questions:
            status = ValidationStatus.NEEDS_CLARIFICATION
        elif preview:
            status = ValidationStatus.NEEDS_CONFIRMATION
        else:
            status = ValidationStatus.READY
        events = []
        if status in {ValidationStatus.READY, ValidationStatus.NEEDS_CONFIRMATION}:
            events = [
                ValidatedEvent(
                    event_id=context.event_id_factory(),
                    property_id=context.property_id,
                    actor_id=context.actor_id,
                    request_id=context.request_id,
                    event_type=family,
                    occurred_on=occurred_on,
                    time_source=time_source,
                    original_time_expression=proposal.events[index].time_expression or "",
                    correction_of=proposal.events[index].correction_of,
                    payload=payload,
                )
                for index, (family, payload, occurred_on, time_source) in enumerate(normalized)
                if occurred_on is not None
            ]
        return ValidationResult(
            status=status,
            events=events,
            proposal=proposal,
            missing_fields=missing,
            questions=questions,
            errors=errors,
            requires_preview=preview or bool(questions),
        )
