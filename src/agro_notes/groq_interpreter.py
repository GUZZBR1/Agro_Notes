"""Groq structured-output adapter with deterministic domain-schema validation."""

from __future__ import annotations

import json
from time import perf_counter
from typing import Any

from openai import OpenAI
from pydantic import ValidationError

from .domain import EventProposal, InterpretationProposal
from .interpreter import SYSTEM_PROMPT
from .llm import StrictInterpretationProposal
from .provider_contracts import (
    InterpretationContext,
    InterpretationResult,
    ProviderMetadata,
    ProviderOutcome,
)
from .settings import Settings

STRICT_SCHEMA_MODELS = frozenset({"openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.8-27b"})


class GroqInterpretationError(ValueError):
    """Provider failure with safe public text and structured operational metadata."""

    def __init__(
        self,
        outcome: ProviderOutcome,
        *,
        retry_count: int = 0,
        latency_ms: float = 0.0,
    ) -> None:
        self.outcome = outcome
        self.retry_count = retry_count
        self.latency_ms = latency_ms
        super().__init__(f"Groq interpretation failed ({outcome.value}).")


class GroqInterpretationProvider:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float = 30.0,
        max_retries: int = 0,
        client: Any | None = None,
    ) -> None:
        self.model = model or (settings.groq_model if settings else "openai/gpt-oss-20b")
        self.client = client or OpenAI(
            api_key=api_key if api_key is not None else settings.groq_api_key,
            base_url=base_url or (settings.groq_base_url if settings else "https://api.groq.com/openai/v1"),
            timeout=timeout_seconds,
            max_retries=max_retries,
        )

    def close(self) -> None:
        self.client.close()

    def interpret(self, text: str, context: InterpretationContext | None = None) -> InterpretationResult:
        del context  # The current app sends trusted context separately through deterministic validation.
        started = perf_counter()
        from openai.lib._pydantic import to_strict_json_schema

        schema = to_strict_json_schema(StrictInterpretationProposal)
        if self.model in STRICT_SCHEMA_MODELS:
            response_format: dict[str, Any] = {
                "type": "json_schema",
                "json_schema": {"name": "agro_notes_interpretation", "strict": True, "schema": schema},
            }
        else:
            response_format = {"type": "json_object"}

        retries = 0
        while True:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                SYSTEM_PROMPT
                                + "\nResponda como JSON conforme este schema:\n"
                                + json.dumps(schema)
                            ),
                        },
                        {"role": "user", "content": text},
                    ],
                    response_format=response_format,
                )
                content = response.choices[0].message.content or " "
                parsed = StrictInterpretationProposal.model_validate_json(content)
                proposal = InterpretationProposal(
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
                request_id = getattr(response, "_request_id", None) or getattr(response, "id", None)
                metadata = ProviderMetadata(
                    provider="groq",
                    model=self.model,
                    latency_ms=max(0.0, (perf_counter() - started) * 1000),
                    outcome=ProviderOutcome.SUCCESS,
                    schema_valid=True,
                    retry_count=retries,
                    request_id=str(request_id) if request_id else None,
                    input_tokens=getattr(getattr(response, "usage", None), "prompt_tokens", None),
                    output_tokens=getattr(getattr(response, "usage", None), "completion_tokens", None),
                )
                metadata.emit_log(operation="interpret")
                return InterpretationResult(
                    proposal=proposal,
                    metadata=metadata,
                )
            except ValidationError:
                if retries < 1:
                    retries += 1
                    continue
                latency_ms = max(0.0, (perf_counter() - started) * 1000)
                failure = GroqInterpretationError(
                    ProviderOutcome.INVALID_SCHEMA, retry_count=retries, latency_ms=latency_ms
                )
                ProviderMetadata(
                    provider="groq", model=self.model,
                    latency_ms=latency_ms,
                    outcome=failure.outcome, schema_valid=False, retry_count=retries,
                ).emit_log(operation="interpret", failed=True)
                raise failure from None
            except Exception as exc:
                name = type(exc).__name__.casefold()
                outcome = (
                    ProviderOutcome.TIMEOUT if "timeout" in name
                    else ProviderOutcome.RATE_LIMITED if "rate" in name
                    else ProviderOutcome.ERROR
                )
                latency_ms = max(0.0, (perf_counter() - started) * 1000)
                failure = GroqInterpretationError(outcome, retry_count=retries, latency_ms=latency_ms)
                ProviderMetadata(
                    provider="groq", model=self.model,
                    latency_ms=latency_ms,
                    outcome=outcome, retry_count=retries,
                ).emit_log(operation="interpret", failed=True)
                raise failure from None
