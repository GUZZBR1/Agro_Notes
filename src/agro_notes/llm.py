"""OpenAI Structured Outputs adapter for safe, non-writing interpretation."""

from time import perf_counter
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
from .provider_contracts import (
    InterpretationContext,
    InterpretationResult,
    ProviderMetadata,
    ProviderOutcome,
)
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
        self.client = client or OpenAI(api_key=settings.openai_api_key, timeout=30.0, max_retries=0)
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


class OpenAIInterpretationProvider:
    """Provider-neutral contract adapter around the existing OpenAI Responses client."""

    def __init__(self, settings: Settings, client: OpenAIResponsesClient | None = None) -> None:
        self.client = client or OpenAIResponsesClient(settings)
        self.model = settings.openai_model

    def close(self) -> None:
        self.client.close()

    def interpret(self, text: str, context: InterpretationContext | None = None) -> InterpretationResult:
        del context
        started = perf_counter()
        try:
            proposal = self.client.generate(
                system_prompt=SYSTEM_PROMPT,
                user_text=text,
                response_model=InterpretationProposal,
            )
        except Exception as exc:
            name = type(exc).__name__.casefold()
            outcome = (
                ProviderOutcome.TIMEOUT if "timeout" in name
                else ProviderOutcome.RATE_LIMITED if "rate" in name
                else ProviderOutcome.ERROR
            )
            ProviderMetadata(
                provider="openai", model=self.model,
                latency_ms=max(0.0, (perf_counter() - started) * 1000), outcome=outcome,
            ).emit_log(operation="interpret", failed=True)
            raise RuntimeError(f"OpenAI interpretation failed ({outcome.value}).") from None
        metadata = ProviderMetadata(
            provider="openai",
            model=self.model,
            latency_ms=max(0.0, (perf_counter() - started) * 1000),
            outcome=ProviderOutcome.SUCCESS,
            schema_valid=True,
        )
        metadata.emit_log(operation="interpret")
        return InterpretationResult(proposal=proposal, metadata=metadata)
