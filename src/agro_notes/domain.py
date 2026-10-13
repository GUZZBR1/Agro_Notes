"""Proposal and validated event contracts for the Agro Notes MVP."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EventType(StrEnum):
    ANIMAL_CREATED = "ANIMAL_CREATED"
    ANIMAL_ENTERED = "ANIMAL_ENTERED"
    CALVING = "CALVING"
    WEIGHING = "WEIGHING"
    LOT_TRANSFER = "LOT_TRANSFER"
    VACCINATION = "VACCINATION"
    HEALTH_OBSERVATION = "HEALTH_OBSERVATION"


class TimeSource(StrEnum):
    EXPLICIT = "EXPLICIT"
    INFERRED_FROM_CAPTURE_DATE = "INFERRED_FROM_CAPTURE_DATE"
    INHERITED_FROM_CORRECTED_EVENT = "INHERITED_FROM_CORRECTED_EVENT"


class CalvingOutcome(Model):
    display_identifier: str | None = None
    live_status: str | None = None
    sex: str | None = None
    outcome: str | None = None
    birth_weight: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    weight_unit: str | None = None
    notes: str | None = None


class AnimalCreatedPayload(Model):
    display_identifier: str | None = None
    species: str | None = None
    sex: str | None = None
    breed: str | None = None
    birth_date: str | None = None
    origin: str | None = None
    group_identifier: str | None = None
    notes: str | None = None


class AnimalEnteredPayload(Model):
    display_identifier: str | None = None
    origin: str | None = None
    group_identifier: str | None = None
    notes: str | None = None


class CalvingPayload(Model):
    mother_identifier: str | None = None
    outcomes: list[CalvingOutcome] = Field(default_factory=list)
    outcome_count: int | None = Field(default=None, ge=1)
    notes: str | None = None


class WeighingPayload(Model):
    animal_identifier: str | None = None
    weight_kg: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    notes: str | None = None


class LotTransferPayload(Model):
    animal_identifier: str | None = None
    from_group_identifier: str | None = None
    to_group_identifier: str | None = None
    notes: str | None = None


class VaccinationPayload(Model):
    animal_identifier: str | None = None
    group_identifier: str | None = None
    vaccine: str | None = None
    dose: str | None = None
    notes: str | None = None
    status: str = "REPORTED"


class HealthObservationPayload(Model):
    animal_identifier: str | None = None
    observation: str | None = None
    observed_sign: str | None = None
    body_region: str | None = None
    status: str = "REPORTED"


PAYLOAD_MODELS: dict[EventType, type[Model]] = {
    EventType.ANIMAL_CREATED: AnimalCreatedPayload,
    EventType.ANIMAL_ENTERED: AnimalEnteredPayload,
    EventType.CALVING: CalvingPayload,
    EventType.WEIGHING: WeighingPayload,
    EventType.LOT_TRANSFER: LotTransferPayload,
    EventType.VACCINATION: VaccinationPayload,
    EventType.HEALTH_OBSERVATION: HealthObservationPayload,
}


class EventProposal(Model):
    # Unknown types remain representable so the deterministic layer can reject them.
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    time_expression: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    ambiguities: list[str] = Field(default_factory=list)
    property_id: str | None = None
    actor_id: str | None = None
    event_id: str | None = None
    correction_of: str | None = None
    correction_requested: bool = False
    _inherited_occurrence_date: date | None = PrivateAttr(default=None)
    _time_expression_captured_at: datetime | None = PrivateAttr(default=None)


class InterpretationProposal(Model):
    events: list[EventProposal] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)
    out_of_scope: bool = False


class TrustedContext(Model):
    property_id: str = Field(min_length=1)
    actor_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    timezone: str = "America/Sao_Paulo"
    now: datetime
    inferred_on: date | None = None
    event_id_factory: Callable[[], str] = Field(default=lambda: str(uuid4()), exclude=True)


class ValidatedEvent(Model):
    event_id: str
    property_id: str
    actor_id: str
    request_id: str
    event_type: EventType
    occurred_on: date
    time_source: TimeSource
    original_time_expression: str = ""
    correction_of: str | None = None
    correction_previous: dict[str, Any] | None = None
    payload: dict[str, Any]


class ValidationStatus(StrEnum):
    READY = "READY"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    NEEDS_CONFIRMATION = "NEEDS_CONFIRMATION"
    REJECTED = "REJECTED"


class ValidationResult(Model):
    status: ValidationStatus
    events: list[ValidatedEvent] = Field(default_factory=list)
    proposal: InterpretationProposal
    missing_fields: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    requires_preview: bool = False
