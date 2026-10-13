"""OpenAI Structured Outputs adapter for safe, non-writing interpretation."""

from typing import Any

from openai import OpenAI

from .domain import (
    AnimalCreatedPayload,
    AnimalEnteredPayload,
    CalvingPayload,
    EventProposal,
    HealthObservationPayload,
    InterpretationProposal,
    LotTransferPayload,
    Model,
    VaccinationPayload,
    WeighingPayload,
)
from .interpreter import SYSTEM_PROMPT
from .settings import Settings


class StrictEventProposal(Model):
    """Closed payload union for the OpenAI strict-schema boundary."""

    event_type: str
    payload: (
        AnimalCreatedPayload
        | AnimalEnteredPayload
        | CalvingPayload
        | WeighingPayload
        | LotTransferPayload
        | VaccinationPayload
        | HealthObservationPayload
    )
    time_expression: str | None = None
    confidence: float | None = None
    ambiguities: list[str] = []
    property_id: str | None = None
    actor_id: str | None = None
    event_id: str | None = None
    correction_of: str | None = None
    correction_requested: bool = False


class StrictInterpretationProposal(Model):
    events: list[StrictEventProposal] = []
    ambiguities: list[str] = []
    out_of_scope: bool = False


class OpenAIResponsesClient:
    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        self.client = client or OpenAI(api_key=settings.openai_api_key, timeout=30.0, max_retries=1)
        self.model = settings.openai_model

    def close(self) -> None:
        self.client.close()

    def generate(self, *, system_prompt: str, user_text: str, response_model: type[InterpretationProposal]) -> Any:
        response = self.client.responses.parse(
            model=self.model,
            instructions=system_prompt or SYSTEM_PROMPT,
            input=user_text,
            text_format=StrictInterpretationProposal,
        )
        parsed = response.output_parsed
        if parsed is None:
            raise ValueError("O modelo não retornou uma interpretação estruturada.")
        return InterpretationProposal(
            events=[
                EventProposal(
                    **event.model_dump(exclude={"payload"}),
                    payload=event.payload.model_dump(mode="json", exclude_none=True),
                )
                for event in parsed.events
            ],
            ambiguities=parsed.ambiguities,
            out_of_scope=parsed.out_of_scope,
        )
