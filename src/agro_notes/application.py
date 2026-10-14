"""Use case orchestration: interpretation never writes before policy approval."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, date, datetime
from typing import Any, Protocol
from uuid import NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo

from .access_control import AccessService
from .domain import (
    EventType,
    InterpretationProposal,
    TrustedContext,
    ValidatedEvent,
    ValidationStatus,
)
from .exports import build_property_export, match_export_intent
from .settings import Settings
from .sheets import AmbiguousResolutionError
from .telegram_bot import BotReply
from .validation import DeterministicValidator

logger = logging.getLogger(__name__)


class Interpreter(Protocol):
    def interpret(self, text: str) -> InterpretationProposal: ...


class EventStore(Protocol):
    def read_rows(self, tab: str) -> list[dict[str, Any]]: ...
    def append_event(self, row: dict[str, Any]) -> Any: ...
    def append_target(self, row: dict[str, Any]) -> Any: ...
    def append_calving_outcome(self, row: dict[str, Any]) -> Any: ...
    def append_animal(self, row: dict[str, Any]) -> Any: ...
    def append_identifier(self, row: dict[str, Any]) -> Any: ...
    def append_genealogy(self, row: dict[str, Any]) -> Any: ...
    def append_allocation(self, row: dict[str, Any]) -> Any: ...
    def append_conversation(self, row: dict[str, Any]) -> Any: ...
    def append_effect(self, row: dict[str, Any]) -> Any: ...
    def append_audit(self, row: dict[str, Any]) -> Any: ...
    def resolve_animal(self, property_id: str, identifier: str) -> dict[str, Any] | None: ...
    def resolve_group(self, property_id: str, identifier: str) -> dict[str, Any] | None: ...
    def find_event(self, event_id: str) -> dict[str, Any] | None: ...
    def find_event_by_command(self, command_id: str) -> dict[str, Any] | None: ...
    def find_effect(self, idempotency_key: str) -> dict[str, Any] | None: ...


class MVPProcessor:
    """Serializes writes for one running process; deploy with one worker only."""

    def __init__(
        self,
        settings: Settings,
        store: EventStore,
        interpreter: Interpreter,
        validator: DeterministicValidator | None = None,
        access: AccessService | None = None,
        drive_export: Any | None = None,
    ) -> None:
        self.settings = settings
        self.store = store
        self.interpreter = interpreter
        self.validator = validator or DeterministicValidator(settings.min_interpretation_confidence)
        self.access = access
        self.drive_export = drive_export
        self._writer_lock = asyncio.Lock()

    async def _authorized(self, user_id: int) -> bool:
        if self.access is not None:
            return await self.access.is_authorized(user_id)
        return user_id in self.settings.allowed_user_ids

    async def _store(self, method: str, *args: Any, **kwargs: Any) -> Any:
        return await asyncio.to_thread(getattr(self.store, method), *args, **kwargs)

    async def receive(
        self,
        user_id: int,
        text: str,
        *,
        source: str,
        message_id: str,
        captured_at: str,
        device_timezone: str | None,
        source_reference: str | None,
        received_at: str | None = None,
    ) -> BotReply:
        if not await self._authorized(user_id):
            return BotReply("Acesso não autorizado.")
        export_intent = match_export_intent(text)
        if export_intent is not None:
            if export_intent.destination == "drive" and (
                self.drive_export is None or not getattr(self.drive_export, "configured", True)
            ):
                return BotReply("A exportação para Google Drive ainda não está configurada.")
            if not self.settings.farm_property_id.strip():
                return BotReply("Não consegui identificar a fazenda autorizada para a exportação.")
            try:
                async with self._writer_lock:
                    document = await asyncio.to_thread(
                        build_property_export, self.store, self.settings.farm_property_id, export_intent.kind
                    )
            except Exception as exc:
                logger.error("Export generation failed (%s)", type(exc).__name__)
                return BotReply("Não foi possível gerar a planilha. Tente novamente.")
            if export_intent.destination == "drive":
                if self.drive_export is None:
                    return BotReply("A exportação para Google Drive ainda não está configurada.")
                try:
                    uploaded = await asyncio.to_thread(self.drive_export.upload_for_user, user_id, document)
                except Exception as exc:
                    from .google_drive import DriveConfigurationError, DriveNotConnectedError, DriveUnavailableError

                    if isinstance(exc, DriveNotConnectedError):
                        return BotReply(
                            "Sua conexão com o Google Drive precisa ser renovada. "
                            "Use /conectar_drive e tente novamente."
                        )
                    if isinstance(exc, DriveUnavailableError):
                        return BotReply(
                            "O Google Drive está temporariamente indisponível. Tente novamente em instantes."
                        )
                    if isinstance(exc, DriveConfigurationError):
                        return BotReply("A exportação para Google Drive ainda não está configurada.")
                    logger.error("Google Drive export failed (%s)", type(exc).__name__)
                    return BotReply("Não foi possível salvar a planilha no Google Drive. Tente novamente.")
                link = uploaded.get("web_view_link")
                suffix = f"\n{link}" if link else ""
                return BotReply(f"Planilha salva no Google Drive em Agro Notes/Exportações.{suffix}")
            return BotReply("Aqui está a planilha da fazenda.", document=document)
        received_at = received_at or datetime.now(UTC).isoformat()
        async with self._writer_lock:
            command_id = f"tg:{user_id}:{message_id}"
            previous = await self._store("find_event_by_command", command_id)
            if previous:
                await self._record_duplicate(user_id, command_id, message_id, source, previous["event_id"])
                return BotReply(self._duplicate_reply(previous))
            duplicate_message = await self._conversation_by_message(message_id)
            if duplicate_message:
                await self._record_duplicate(
                    user_id, command_id, message_id, source, duplicate_message.get("event_ids", "")
                )
                pending_id = (
                    str(duplicate_message["command_id"])
                    if duplicate_message.get("state") == "WAITING_CONFIRMATION"
                    else None
                )
                return BotReply(str(duplicate_message.get("response") or "Comando já processado."), pending_id)
            if text.strip().lower().startswith("/historico"):
                response = await self._history(user_id, text)
                await self._record_conversation(
                    user_id,
                    command_id,
                    message_id,
                    source,
                    captured_at,
                    device_timezone,
                    source_reference,
                    text,
                    InterpretationProposal(),
                    "COMPLETED",
                    response.text,
                    received_at=received_at,
                )
                return response
            if text.strip().lower() == "/cancel":
                response = await self._cancel_latest(user_id)
                await self._record_conversation(
                    user_id,
                    command_id,
                    message_id,
                    source,
                    captured_at,
                    device_timezone,
                    source_reference,
                    text,
                    InterpretationProposal(),
                    "CANCELLED",
                    response.text,
                    received_at=received_at,
                )
                return response

            prior = await self._latest_open_conversation(user_id)
            context_text = text
            clarification_context: dict[str, Any] = {
                "original_transcript": text,
                "original_captured_at": captured_at,
                "original_source": source,
                "voice_involved": source.casefold() == "voice",
                "turns": [],
            }
            if prior and prior.get("state") == "NEEDS_CLARIFICATION":
                command_id = str(prior["command_id"])
                try:
                    previous_pending = json.loads(prior.get("pending_command_json") or "{}")
                except (TypeError, json.JSONDecodeError):
                    previous_pending = {}
                clarification_context = previous_pending.get(
                    "clarification_context",
                    {"original_transcript": prior.get("transcript", ""), "turns": []},
                )
                clarification_context = {
                    "original_transcript": str(clarification_context.get("original_transcript") or ""),
                    "original_captured_at": str(
                        clarification_context.get("original_captured_at") or prior.get("captured_at") or captured_at
                    ),
                    "original_source": str(
                        clarification_context.get("original_source") or prior.get("source") or source
                    ),
                    "voice_involved": bool(clarification_context.get("voice_involved"))
                    or source.casefold() == "voice"
                    or str(clarification_context.get("original_source") or prior.get("source") or "").casefold()
                    == "voice",
                    "turns": list(clarification_context.get("turns") or []),
                }
                clarification_context["turns"].append(
                    {"question": str(prior.get("confirmation_prompt", "")), "answer": text}
                )
                exchange_text = "\n".join(
                    f"Pergunta do sistema: {turn['question']}\nResposta do produtor: {turn['answer']}"
                    for turn in clarification_context["turns"]
                )
                context_text = (
                    f"Pedido original do produtor: {clarification_context['original_transcript']}\n"
                    f"Esclarecimentos anteriores:\n{exchange_text}\n"
                    "Use as respostas apenas para preencher os campos perguntados; preserve os demais dados originais."
                )

            await self._ensure_trusted_rows(user_id)
            try:
                proposal = await asyncio.to_thread(self.interpreter.interpret, context_text)
                proposal = await self._resolve_correction_requests(proposal, user_id)
                if prior and prior.get("state") == "NEEDS_CLARIFICATION":
                    original_text = clarification_context["original_transcript"].casefold()
                    original_capture = datetime.fromisoformat(
                        clarification_context["original_captured_at"].replace("Z", "+00:00")
                    )
                    for event in proposal.events:
                        expression = (event.time_expression or "").strip().casefold()
                        if expression and expression in original_text:
                            event._time_expression_captured_at = original_capture
                trusted = self._trusted_context(
                    user_id,
                    command_id,
                    captured_at,
                    inferred_captured_at=clarification_context["original_captured_at"],
                )
                result = self.validator.validate(proposal, trusted)
                if (
                    clarification_context["voice_involved"]
                    and result.status == ValidationStatus.READY
                    and any(event.event_type == EventType.WEIGHING for event in result.events)
                ):
                    result = result.model_copy(
                        update={"status": ValidationStatus.NEEDS_CONFIRMATION, "requires_preview": True}
                    )
                proposal = result.proposal
                if result.status == ValidationStatus.REJECTED:
                    answer = "Não posso registrar essa solicitação no MVP: " + "; ".join(result.errors)
                    await self._record_conversation(
                        user_id,
                        command_id,
                        message_id,
                        source,
                        captured_at,
                        device_timezone,
                        source_reference,
                        text,
                        proposal,
                        "REJECTED",
                        answer,
                        received_at=received_at,
                    )
                    return BotReply(answer)

                if result.status == ValidationStatus.NEEDS_CLARIFICATION:
                    manual_review = any("revisão manual" in question.lower() for question in result.questions)
                    answer = (
                        "⚠️ Esta solicitação exige revisão manual e não foi gravada. " + " ".join(result.questions)
                        if manual_review
                        else self._clarification(result.questions, result.missing_fields)
                    )
                    await self._record_conversation(
                        user_id,
                        command_id,
                        message_id,
                        source,
                        captured_at,
                        device_timezone,
                        source_reference,
                        text,
                        proposal,
                        "MANUAL_REVIEW" if manual_review else "NEEDS_CLARIFICATION",
                        answer,
                        pending={
                            "proposal": proposal.model_dump(mode="json"),
                            "clarification_context": clarification_context,
                        },
                        missing_fields=result.missing_fields,
                        received_at=received_at,
                    )
                    return BotReply(answer)

                events, resolution_questions = await self._resolve_entities(result.events)
                if resolution_questions:
                    manual_review = any("revisão manual" in question.lower() for question in resolution_questions)
                    answer = (
                        "⚠️ Esta solicitação exige revisão manual e não foi gravada. " + " ".join(resolution_questions)
                        if manual_review
                        else "Preciso esclarecer antes de registrar: " + " ".join(resolution_questions)
                    )
                    await self._record_conversation(
                        user_id,
                        command_id,
                        message_id,
                        source,
                        captured_at,
                        device_timezone,
                        source_reference,
                        text,
                        proposal,
                        "MANUAL_REVIEW" if manual_review else "NEEDS_CLARIFICATION",
                        answer,
                        pending={
                            "proposal": proposal.model_dump(mode="json"),
                            "clarification_context": clarification_context,
                        },
                        missing_fields=resolution_questions,
                        received_at=received_at,
                    )
                    return BotReply(answer)

                if result.status == ValidationStatus.NEEDS_CONFIRMATION:
                    preview = self._preview(events)
                    await self._record_conversation(
                        user_id,
                        command_id,
                        message_id,
                        source,
                        captured_at,
                        device_timezone,
                        source_reference,
                        text,
                        proposal,
                        "WAITING_CONFIRMATION",
                        preview,
                        pending={"events": [event.model_dump(mode="json") for event in events]},
                        received_at=received_at,
                    )
                    return BotReply(preview, pending_id=command_id)

                response = await self._commit(
                    user_id,
                    command_id,
                    message_id,
                    source,
                    captured_at,
                    device_timezone,
                    source_reference,
                    events,
                    confirmed=False,
                )
                await self._record_conversation(
                    user_id,
                    command_id,
                    message_id,
                    source,
                    captured_at,
                    device_timezone,
                    source_reference,
                    text,
                    proposal,
                    "COMPLETED" if response.startswith("✅") else "PARTIALLY_APPLIED",
                    response,
                    events=events,
                    received_at=received_at,
                )
                return BotReply(response)
            except Exception as exc:
                logger.error("MVP command processing failed command=%s (%s)", command_id, type(exc).__name__)
                await self._safe_error_audit(user_id, command_id, message_id, source, text)
                return BotReply(
                    "Não consegui concluir o registro. Nenhum sucesso foi confirmado; tente novamente ou use /cancel."
                )

    async def record_ingress_failure(
        self,
        user_id: int,
        *,
        message_id: str,
        captured_at: str,
        received_at: str,
        source_reference: str | None,
        failure_code: str,
        response: str,
    ) -> None:
        if not await self._authorized(user_id):
            return
        async with self._writer_lock:
            command_id = f"tg:{user_id}:{message_id}"
            if await self._conversation_by_message(message_id):
                return
            row = {
                "message_id": f"{message_id}:failed",
                "property_id": self.settings.farm_property_id,
                "command_id": command_id,
                "user_id": str(user_id),
                "channel": "VOICE",
                "received_at": received_at,
                "captured_at": captured_at,
                "device_timezone": "UNKNOWN",
                "resolved_at": datetime.now(UTC).isoformat(),
                "raw_text_ref": message_id,
                "audio_ref": source_reference or "",
                "transcript": "",
                "transcript_confidence": "",
                "interpretation_id": "",
                "intents": "[]",
                "entity_candidates": "[]",
                "missing_fields": "[]",
                "confirmation_prompt": "",
                "response": response,
                "model/version": self.settings.transcription_model,
                "state": "FAILED",
                "event_ids": "[]",
                "pending_command_json": "{}",
                "callback_chat_id": "",
                "callback_message_id": "",
            }
            await self._store("append_conversation", row)
            await self._store(
                "append_audit",
                {
                    "audit_id": self._stable_id(f"{command_id}:{failure_code}"),
                    "property_id": self.settings.farm_property_id,
                    "command_id": command_id,
                    "timestamp": row["resolved_at"],
                    "actor": str(user_id),
                    "channel": "VOICE",
                    "raw_message_ref": message_id,
                    "transcript_ref": source_reference or "",
                    "interpretation": "",
                    "confirmation": "",
                    "event_ids": "",
                    "affected_record_ids": "",
                    "action": failure_code,
                    "prior_state_ref": "RECEIVED",
                    "resulting_state_ref": "FAILED",
                    "error": failure_code,
                    "correction_of": "",
                    "idempotency_key": f"{command_id}:{failure_code}",
                },
            )

    async def bind_confirmation(self, user_id: int, pending_id: str, *, chat_id: int, message_id: int) -> None:
        if not await self._authorized(user_id):
            raise ValueError("User is not authorized.")
        async with self._writer_lock:
            row = await self._latest_conversation(pending_id)
            if not row or int(row.get("user_id", -1)) != user_id or row.get("state") != "WAITING_CONFIRMATION":
                raise ValueError("No confirmation is waiting for this user.")
            latest_open = await self._latest_open_conversation_any_state(user_id)
            if not latest_open or latest_open.get("command_id") != pending_id:
                raise ValueError("This confirmation is no longer current.")
            updated = dict(row)
            updated["message_id"] = f"{row['message_id']}:bound:{message_id}"
            updated["callback_chat_id"] = str(chat_id)
            updated["callback_message_id"] = str(message_id)
            await self._store("append_conversation", updated)
            await self._audit_conversation_state(updated, "CONFIRMATION_BOUND", "")

    async def confirm(
        self, user_id: int, pending_id: str, *, source_chat_id: int | None = None, source_message_id: int | None = None
    ) -> BotReply:
        if not await self._authorized(user_id):
            return BotReply("Acesso não autorizado.")
        async with self._writer_lock:
            row = await self._latest_conversation(pending_id)
            if not row or int(row.get("user_id", -1)) != user_id:
                return BotReply("Confirmação expirada ou não encontrada.")
            if source_chat_id is not None and str(row.get("callback_chat_id")) != str(source_chat_id):
                return BotReply("Esta confirmação não pertence a esta conversa.")
            if source_message_id is not None and str(row.get("callback_message_id")) != str(source_message_id):
                return BotReply("Esta confirmação não pertence a esta mensagem.")
            latest_open = await self._latest_open_conversation_any_state(user_id)
            if not latest_open or latest_open.get("command_id") != pending_id:
                return BotReply("Esta confirmação expirou; envie o comando novamente.")
            if row.get("state") == "COMPLETED":
                return BotReply("Esse comando já foi registrado.", remove_keyboard=True)
            if row.get("state") != "WAITING_CONFIRMATION":
                return BotReply("Esse comando não está aguardando confirmação.", remove_keyboard=True)
            try:
                payload = json.loads(row.get("pending_command_json") or "{}")
                events = [ValidatedEvent.model_validate(event) for event in payload.get("events", [])]
                if not events:
                    return BotReply(
                        "A prévia não contém eventos válidos. Envie a informação novamente.", remove_keyboard=True
                    )
                response = await self._commit(
                    user_id,
                    pending_id,
                    row.get("raw_text_ref") or row["message_id"],
                    row.get("channel", "text"),
                    row.get("captured_at") or datetime.now(UTC).isoformat(),
                    row.get("device_timezone") or None,
                    row.get("audio_ref") or None,
                    events,
                    confirmed=True,
                )
                final_state = "COMPLETED" if response.startswith("✅") else "PARTIALLY_APPLIED"
                await self._append_conversation_state(row, final_state, response)
                return BotReply(response, remove_keyboard=True)
            except Exception:
                logger.error("Confirmation failed command=%s", pending_id)
                return BotReply(
                    "⚠️ O comando pode ter sido aplicado parcialmente. Não vou repetir automaticamente; "
                    "reconcilie o evento e seus efeitos na planilha antes de continuar.",
                    remove_keyboard=True,
                )

    async def cancel(
        self, user_id: int, pending_id: str, *, source_chat_id: int | None = None, source_message_id: int | None = None
    ) -> BotReply:
        if not await self._authorized(user_id):
            return BotReply("Acesso não autorizado.")
        async with self._writer_lock:
            row = await self._latest_conversation(pending_id)
            if not row or int(row.get("user_id", -1)) != user_id:
                return BotReply("Comando pendente não encontrado.")
            if source_chat_id is not None and str(row.get("callback_chat_id")) != str(source_chat_id):
                return BotReply("Esta confirmação não pertence a esta conversa.")
            if source_message_id is not None and str(row.get("callback_message_id")) != str(source_message_id):
                return BotReply("Esta confirmação não pertence a esta mensagem.")
            latest_open = await self._latest_open_conversation_any_state(user_id)
            if not latest_open or latest_open.get("command_id") != pending_id:
                return BotReply("Esta confirmação expirou; envie o comando novamente.")
            if row.get("state") != "WAITING_CONFIRMATION":
                return BotReply("Esse comando não está aguardando confirmação.")
            answer = "Registro cancelado. Nenhum evento foi gravado."
            await self._append_conversation_state(row, "CANCELLED", answer)
            return BotReply(answer, remove_keyboard=True)

    async def _try_resolve_animal(self, property_id: str, identifier: str) -> tuple[dict[str, Any] | None, bool]:
        try:
            return await self._store("resolve_animal", property_id, identifier), False
        except AmbiguousResolutionError:
            return None, True

    async def _try_resolve_group(self, property_id: str, identifier: str) -> tuple[dict[str, Any] | None, bool]:
        try:
            return await self._store("resolve_group", property_id, identifier), False
        except AmbiguousResolutionError:
            return None, True

    async def _resolve_correction_requests(
        self, proposal: InterpretationProposal, user_id: int
    ) -> InterpretationProposal:
        supported = {EventType.WEIGHING, EventType.VACCINATION, EventType.HEALTH_OBSERVATION}
        for candidate in proposal.events:
            if not candidate.correction_requested or candidate.correction_of:
                continue
            try:
                family = EventType(candidate.event_type)
            except ValueError:
                continue
            if family not in supported:
                candidate.ambiguities.append(
                    "Esta correção exige revisão manual; não vou alterar identidade, parto ou alocação automaticamente."
                )
                continue

            rows = await self._store("read_rows", "06_Eventos")
            latest: dict[str, dict[str, Any]] = {}
            for row in rows:
                if row.get("event_id"):
                    latest[str(row["event_id"])] = row
            already_corrected = {
                str(row.get("correction_of"))
                for row in latest.values()
                if row.get("processing_status") == "APPLIED" and row.get("correction_of")
            }
            possible = [
                row
                for row in reversed(rows)
                if row.get("event_id")
                and latest.get(str(row["event_id"])) is row
                and row.get("property_id") == self.settings.farm_property_id
                and row.get("actor_id") == str(user_id)
                and row.get("event_type") == family.value
                and row.get("processing_status") == "APPLIED"
                and row.get("event_id") not in already_corrected
            ]

            target_key = (
                "group_id"
                if family == EventType.VACCINATION and candidate.payload.get("group_identifier")
                else "animal_id"
            )
            identifier_key = "group_identifier" if target_key == "group_id" else "animal_identifier"
            target_identifier = candidate.payload.get(identifier_key)
            target_id: str | None = None
            if target_identifier:
                if target_key == "group_id":
                    target, ambiguous = await self._try_resolve_group(
                        self.settings.farm_property_id, str(target_identifier)
                    )
                else:
                    target, ambiguous = await self._try_resolve_animal(
                        self.settings.farm_property_id, str(target_identifier)
                    )
                if ambiguous:
                    candidate.ambiguities.append(
                        f"O alvo {target_identifier} é ambíguo; informe o identificador único do registro a corrigir."
                    )
                    continue
                if not target:
                    candidate.ambiguities.append(
                        f"Não encontrei o alvo {target_identifier} para localizar o evento que você quer corrigir."
                    )
                    continue
                target_id = str(target[target_key])
                possible = [row for row in possible if self._event_payload(row).get(target_key) == target_id]

            if not possible:
                candidate.ambiguities.append(
                    "Não encontrei um registro anterior compatível para corrigir. "
                    "Informe o animal e confira o histórico."
                )
                continue
            original = possible[0]
            original_payload = self._event_payload(original)
            candidate.correction_of = str(original["event_id"])
            if not target_identifier:
                inherited_key = (
                    "group_identifier"
                    if family == EventType.VACCINATION and original_payload.get("group_id")
                    else identifier_key
                )
                inherited_identifier = original_payload.get(inherited_key)
                if inherited_identifier:
                    candidate.payload[inherited_key] = inherited_identifier
            original_date = str(original.get("occurred_from") or "")[:10]
            if not (candidate.time_expression or "").strip() and original_date:
                candidate._inherited_occurrence_date = date.fromisoformat(original_date)
        return proposal

    @staticmethod
    def _event_payload(row: dict[str, Any]) -> dict[str, Any]:
        try:
            payload = json.loads(row.get("event_payload_json") or "{}")
        except (TypeError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    async def _resolve_entities(self, events: list[ValidatedEvent]) -> tuple[list[ValidatedEvent], list[str]]:
        questions: list[str] = []
        resolved: list[ValidatedEvent] = []
        for event in events:
            payload = dict(event.payload)
            correction_previous: dict[str, Any] | None = None
            kind = event.event_type
            animal_field = {
                EventType.ANIMAL_ENTERED: "display_identifier",
                EventType.WEIGHING: "animal_identifier",
                EventType.LOT_TRANSFER: "animal_identifier",
                EventType.VACCINATION: "animal_identifier",
                EventType.HEALTH_OBSERVATION: "animal_identifier",
            }.get(kind)
            if kind == EventType.VACCINATION and not payload.get("animal_identifier"):
                animal_field = None
            if kind == EventType.ANIMAL_CREATED:
                identifier = str(payload["display_identifier"])
                match, ambiguous = await self._try_resolve_animal(event.property_id, identifier)
                if ambiguous:
                    questions.append(
                        f"O identificador {identifier} corresponde a mais de um animal. "
                        "Revise o cadastro antes de continuar."
                    )
                elif match:
                    questions.append(
                        f"O identificador {identifier} já está cadastrado. "
                        "Confirme se é o mesmo animal ou use outro número."
                    )
                else:
                    payload["new_animal_id"] = self._stable_id(f"{event.event_id}:animal")
            elif kind == EventType.CALVING:
                identifier = str(payload["mother_identifier"])
                mother, ambiguous = await self._try_resolve_animal(event.property_id, identifier)
                if ambiguous:
                    questions.append(f"O identificador da matriz {identifier} é ambíguo nesta fazenda.")
                elif not mother:
                    questions.append(
                        f"Não encontrei a matriz {identifier} nesta fazenda. "
                        "Confirme o identificador ou cadastre o animal."
                    )
                else:
                    payload["mother_id"] = mother["animal_id"]
                for index, outcome in enumerate(payload.get("outcomes", [])):
                    display_id = outcome.get("display_identifier")
                    if self._liveness_conflicts(outcome):
                        questions.append(
                            f"O status de vida da cria {display_id or index + 1} contradiz o resultado; confirme."
                        )
                    if self._is_live(outcome):
                        match, ambiguous = (
                            await self._try_resolve_animal(event.property_id, str(display_id))
                            if display_id
                            else (None, False)
                        )
                        if ambiguous:
                            questions.append(f"O identificador de cria {display_id} é ambíguo; revise o cadastro.")
                        elif match:
                            questions.append(
                                f"O identificador de cria {display_id} já está cadastrado; revise o parto."
                            )
                        else:
                            outcome["animal_id"] = self._stable_id(f"{event.event_id}:outcome:{index}:animal")
            elif animal_field:
                identifier = str(payload[animal_field])
                animal, ambiguous = await self._try_resolve_animal(event.property_id, identifier)
                if ambiguous:
                    questions.append(f"O identificador {identifier} corresponde a mais de um animal nesta fazenda.")
                elif not animal:
                    questions.append(
                        f"Não encontrei o animal {identifier} nesta fazenda. Confirme o número ou cadastre-o primeiro."
                    )
                else:
                    payload["animal_id"] = animal["animal_id"]
            if kind in {EventType.ANIMAL_CREATED, EventType.ANIMAL_ENTERED, EventType.VACCINATION} and payload.get(
                "group_identifier"
            ):
                group_identifier = str(payload["group_identifier"])
                group, ambiguous = await self._try_resolve_group(event.property_id, group_identifier)
                if ambiguous:
                    questions.append(f"O nome do lote {group_identifier} não é único nesta fazenda.")
                elif not group:
                    questions.append(f"Não encontrei o lote {group_identifier} nesta fazenda.")
                else:
                    payload["group_id"] = group["group_id"]
            if kind == EventType.LOT_TRANSFER:
                group_id = str(payload.get("to_group_identifier", ""))
                group, ambiguous = await self._try_resolve_group(event.property_id, group_id)
                if ambiguous:
                    questions.append(f"O lote de destino {group_id} é ambíguo nesta fazenda.")
                elif not group:
                    questions.append(
                        f"Não encontrei o lote {group_id} nesta fazenda. Confirme o nome ou número do destino."
                    )
                else:
                    payload["to_group_id"] = group["group_id"]
                from_group = payload.get("from_group_identifier")
                source_group = None
                if from_group:
                    source_group, ambiguous = await self._try_resolve_group(event.property_id, str(from_group))
                    if ambiguous:
                        questions.append(f"O lote de origem {from_group} é ambíguo nesta fazenda.")
                    elif not source_group:
                        questions.append(f"Não encontrei o lote de origem {from_group}.")
                    else:
                        payload["from_group_id"] = source_group["group_id"]
                if payload.get("animal_id"):
                    allocations = await self._store("read_rows", "05_Alocacoes")
                    latest_allocations = {
                        str(row["allocation_id"]): row for row in allocations if row.get("allocation_id")
                    }
                    current = [
                        row
                        for row in latest_allocations.values()
                        if row.get("property_id") == event.property_id
                        and row.get("animal_id") == payload["animal_id"]
                        and not row.get("effective_to")
                    ]
                    if len(current) != 1:
                        questions.append(
                            "Não consegui identificar um único lote atual para este animal. "
                            "Confirme o lote de origem antes de transferir."
                        )
                    else:
                        active = current[0]
                        if source_group and source_group.get("group_id") != active.get("group_id"):
                            questions.append("O lote de origem informado não corresponde à alocação atual do animal.")
                        payload["from_group_id"] = active["group_id"]
                        if not from_group:
                            payload["from_group_identifier"] = active.get("group_id")
                        try:
                            active_from = date.fromisoformat(str(active.get("effective_from", "")))
                        except ValueError:
                            active_from = None
                        if active_from and event.occurred_on < active_from:
                            questions.append(
                                "A data da transferência é anterior ao início da alocação atual. Confirme a data."
                            )
            if event.correction_of:
                original = await self._store("find_event", event.correction_of)
                if (
                    not original
                    or original.get("property_id") != event.property_id
                    or original.get("event_type") != event.event_type.value
                    or original.get("processing_status") != "APPLIED"
                ):
                    questions.append(
                        "Não encontrei um evento anterior concluído e compatível para corrigir. "
                        "Consulte /historico e informe o ID do evento."
                    )
                elif event.event_type not in {
                    EventType.WEIGHING,
                    EventType.VACCINATION,
                    EventType.HEALTH_OBSERVATION,
                }:
                    questions.append(
                        "Essa correção altera identidade, parto ou alocação e exige revisão manual; "
                        "não vou aplicar efeitos compensatórios automaticamente."
                    )
                else:
                    correction_previous = self._event_payload(original)
                    all_events = await self._store("read_rows", "06_Eventos")
                    if any(
                        row.get("property_id") == event.property_id and row.get("correction_of") == event.correction_of
                        for row in all_events
                    ):
                        questions.append(
                            "Esse evento já foi corrigido. Consulte o histórico e use o ID da versão mais recente."
                        )
                    old_targets = await self._store("read_rows", "07_Evento_Animais")
                    old_animal_ids = {
                        str(row.get("animal_id"))
                        for row in old_targets
                        if row.get("property_id") == event.property_id
                        and row.get("event_id") == event.correction_of
                        and row.get("animal_id")
                    }
                    new_animal_ids = set(self._target_animal_ids(event.model_copy(update={"payload": payload})))
                    if event.event_type == EventType.VACCINATION:
                        try:
                            original_payload = json.loads(original.get("event_payload_json") or "{}")
                        except (TypeError, json.JSONDecodeError):
                            original_payload = {}
                        old_group_id = original_payload.get("group_id")
                        new_group_id = payload.get("group_id")
                        if old_group_id != new_group_id and (old_group_id or new_group_id):
                            questions.append("A correção mudaria o lote-alvo da vacinação e exige revisão manual.")
                    if old_animal_ids and not old_animal_ids.intersection(new_animal_ids):
                        questions.append(
                            "O evento anterior pertence a outro animal. Confira o histórico antes de corrigir."
                        )
            resolved.append(
                event.model_copy(update={"payload": payload, "correction_previous": correction_previous}, deep=True)
            )
        return resolved, questions

    async def _commit(
        self,
        user_id: int,
        command_id: str,
        message_id: str,
        source: str,
        captured_at: str,
        device_timezone: str | None,
        source_reference: str | None,
        events: list[ValidatedEvent],
        *,
        confirmed: bool,
    ) -> str:
        existing = await self._store("find_event_by_command", command_id)
        if existing:
            if existing.get("processing_status") == "APPLIED":
                return "Esse comando já foi registrado."
            return "⚠️ O evento foi iniciado e precisa de reconciliação manual; não vou duplicar a escrita."
        completed_ids: list[str] = []
        try:
            for event in events:
                row = self._event_row(
                    event,
                    user_id,
                    command_id,
                    message_id,
                    source,
                    captured_at,
                    source_reference,
                    confirmed,
                    "APPLYING",
                )
                await self._store("append_event", row)
                completed_ids.append(event.event_id)
                await self._apply_event(event, command_id, user_id, captured_at)
                row["processing_status"] = "APPLIED"
                await self._store("append_event", row)
                await self._store(
                    "append_audit",
                    self._audit_row(
                        event,
                        command_id,
                        user_id,
                        source,
                        message_id,
                        source_reference,
                        "EVENT_APPLIED",
                        None,
                        event.event_id,
                    ),
                )
            return "✅ " + "\n".join(self._success_line(event) for event in events)
        except Exception:
            logger.error("Partial application command=%s", command_id)
            for event_id in completed_ids:
                await self._safe_event_failure(event_id, command_id, "PARTIAL_APPLICATION_FAILED")
            return (
                "⚠️ O evento pode ter sido registrado parcialmente. "
                "Não vou repetir os efeitos automaticamente. Reconcile a planilha antes de tentar novamente."
            )

    async def _apply_event(self, event: ValidatedEvent, command_id: str, user_id: int, captured_at: str) -> None:
        p = event.payload
        kind = event.event_type
        if kind == EventType.ANIMAL_CREATED:
            animal_id = p["new_animal_id"]
            await self._effect(
                event,
                f"animal:{animal_id}",
                "ANIMAL_CREATED",
                "animal",
                animal_id,
                "append_animal",
                {
                    "animal_id": animal_id,
                    "property_id": event.property_id,
                    "birth_property_id": event.property_id,
                    "species": p["species"],
                    "sex": p.get("sex"),
                    "birth_date": p.get("birth_date") or "",
                    "birth_date_precision": "DAY" if p.get("birth_date") else "UNKNOWN",
                    "birth_source": event.event_id if p.get("birth_date") else "",
                    "breed": p.get("breed"),
                    "genetic_composition": "",
                    "origin_type": p.get("origin") or "UNKNOWN",
                    "first_entry_date": "",
                    "entry_event_id": "",
                    "evidence_status": "REPORTED",
                    "created_at": datetime.now(UTC).isoformat(),
                },
                "02_Animais",
                "animal_id",
            )
            await self._append_identifier(event, animal_id, p["display_identifier"], "created")
            if p.get("group_id"):
                await self._append_allocation(event, animal_id, p["group_id"], "created", captured_at)
        elif kind == EventType.ANIMAL_ENTERED:
            animal_id = p["animal_id"]
            animals = await self._store("read_rows", "02_Animais")
            animal = next(
                (
                    row
                    for row in reversed(animals)
                    if row.get("property_id") == event.property_id and row.get("animal_id") == animal_id
                ),
                None,
            )
            if animal:
                await self._effect(
                    event,
                    f"animal-entry:{animal_id}",
                    "ANIMAL_ENTERED",
                    "animal",
                    animal_id,
                    "append_animal",
                    {
                        **animal,
                        "first_entry_date": animal.get("first_entry_date") or event.occurred_on.isoformat(),
                        "entry_event_id": animal.get("entry_event_id") or event.event_id,
                    },
                    "02_Animais",
                    "entry_event_id",
                )
            if p.get("group_id"):
                await self._append_allocation(event, animal_id, p["group_id"], "entered", captured_at)
        elif kind == EventType.CALVING:
            for index, outcome in enumerate(p.get("outcomes", [])):
                outcome_id = self._stable_id(f"{event.event_id}:outcome:{index}")
                await self._effect(
                    event,
                    f"outcome:{outcome_id}",
                    "CALVING_OUTCOME",
                    "outcome",
                    outcome_id,
                    "append_calving_outcome",
                    {
                        "outcome_id": outcome_id,
                        "property_id": event.property_id,
                        "event_id": event.event_id,
                        "outcome_type": outcome.get("outcome"),
                        "live_status": outcome.get("live_status"),
                        "animal_id": outcome.get("animal_id"),
                        "sex": outcome.get("sex"),
                        "birth_weight": outcome.get("birth_weight"),
                        "weight_unit": outcome.get("weight_unit"),
                        "parentage_certainty": "REPORTED",
                        "evidence_ref": "",
                        "correction_of": "",
                    },
                    "08A_Resultados_Parto",
                    "outcome_id",
                )
                animal_id = outcome.get("animal_id")
                if animal_id:
                    await self._effect(
                        event,
                        f"animal:{animal_id}",
                        "CALF_CREATED",
                        "animal",
                        animal_id,
                        "append_animal",
                        {
                            "animal_id": animal_id,
                            "property_id": event.property_id,
                            "birth_property_id": event.property_id,
                            "species": "BOVINE",
                            "sex": outcome.get("sex"),
                            "birth_date": event.occurred_on.isoformat(),
                            "birth_date_precision": "DAY",
                            "birth_source": event.event_id,
                            "breed": "",
                            "genetic_composition": "",
                            "origin_type": "BIRTH",
                            "first_entry_date": event.occurred_on.isoformat(),
                            "entry_event_id": event.event_id,
                            "evidence_status": "REPORTED",
                            "created_at": datetime.now(UTC).isoformat(),
                        },
                        "02_Animais",
                        "animal_id",
                    )
                    if outcome.get("display_identifier"):
                        await self._append_identifier(
                            event, animal_id, outcome["display_identifier"], f"outcome:{index}"
                        )
                    await self._effect(
                        event,
                        f"genealogy:{animal_id}",
                        "DAM_RELATIONSHIP",
                        "relationship",
                        animal_id,
                        "append_genealogy",
                        {
                            "relationship_id": self._stable_id(f"{event.event_id}:dam:{animal_id}"),
                            "property_id": event.property_id,
                            "descendant_animal_id": animal_id,
                            "parent_animal_id": p["mother_id"],
                            "parent_role": "DAM",
                            "certainty": "REPORTED",
                            "source_event_id": event.event_id,
                            "effective_at": event.occurred_on.isoformat(),
                            "evidence_ref": "",
                            "correction_of": "",
                        },
                        "02A_Vinculos_Genealogicos",
                        "relationship_id",
                    )
        elif kind == EventType.LOT_TRANSFER:
            animal_id = p["animal_id"]
            source_group_id = p.get("from_group_id") or await self._current_group(event.property_id, animal_id)
            if not source_group_id:
                raise ValueError("Não foi possível identificar o lote atual para fechar a alocação.")
            await self._close_allocation(event, animal_id, source_group_id)
            await self._append_allocation(event, animal_id, p["to_group_id"], "transfer", captured_at)
        targets = self._target_animal_ids(event)
        for animal_id in targets:
            await self._effect(
                event,
                f"target:{animal_id}",
                "EVENT_TARGET",
                "animal",
                animal_id,
                "append_target",
                {
                    "event_target_id": self._stable_id(f"{event.event_id}:target:{animal_id}"),
                    "property_id": event.property_id,
                    "event_id": event.event_id,
                    "animal_id": animal_id,
                    "group_id": "",
                    "target_basis": "INDIVIDUAL",
                    "membership_snapshot_id": "",
                    "observed_at": captured_at,
                    "outcome": "",
                    "target_confidence": "CONFIRMED",
                },
                "07_Evento_Animais",
                "event_target_id",
            )
        if kind == EventType.VACCINATION and p.get("group_id"):
            group_id = str(p["group_id"])
            await self._effect(
                event,
                f"target:group:{group_id}",
                "EVENT_TARGET",
                "group",
                group_id,
                "append_target",
                {
                    "event_target_id": self._stable_id(f"{event.event_id}:target:group:{group_id}"),
                    "property_id": event.property_id,
                    "event_id": event.event_id,
                    "animal_id": "",
                    "group_id": group_id,
                    "target_basis": "GROUP_MEMBERSHIP",
                    "membership_snapshot_id": "",
                    "observed_at": captured_at,
                    "outcome": "",
                    "target_confidence": "CONFIRMED",
                },
                "07_Evento_Animais",
                "event_target_id",
            )

    async def _effect(
        self,
        event: ValidatedEvent,
        suffix: str,
        effect_type: str,
        target_type: str,
        target_id: str,
        append_method: str,
        row: dict[str, Any],
        tab: str,
        pk: str,
    ) -> None:
        key = f"{event.event_id}:{suffix}"
        current = await self._store("find_effect", key)
        if current and current.get("status") == "APPLIED":
            return
        effect_id = self._stable_id(key)
        if not current:
            await self._store(
                "append_effect",
                self._effect_row(event, effect_id, key, effect_type, target_type, target_id, "PENDING", 0, ""),
            )
        previous_attempts = int(current.get("attempt_count", 0)) if current else 0
        try:
            exists = any(
                str(item.get(pk, "")) == str(row.get(pk, ""))
                and (tab != "05_Alocacoes" or item.get("event_id") == row.get("event_id"))
                for item in await self._store("read_rows", tab)
            )
            if not exists:
                await self._store(append_method, row)
        except Exception:
            await self._store(
                "append_effect",
                self._effect_row(
                    event,
                    effect_id,
                    key,
                    effect_type,
                    target_type,
                    target_id,
                    "FAILED",
                    previous_attempts + 1,
                    "EFFECT_FAILED",
                ),
            )
            raise
        await self._store(
            "append_effect",
            self._effect_row(
                event,
                effect_id,
                key,
                effect_type,
                target_type,
                target_id,
                "APPLIED",
                previous_attempts + 1,
                "",
            ),
        )

    async def _append_identifier(
        self, event: ValidatedEvent, animal_id: str, display_identifier: str, suffix: str
    ) -> None:
        identifier_id = self._stable_id(f"{event.event_id}:identifier:{animal_id}:{display_identifier}")
        await self._effect(
            event,
            f"identifier:{suffix}:{display_identifier}",
            "IDENTIFIER_ASSIGNED",
            "identifier",
            identifier_id,
            "append_identifier",
            {
                "identifier_id": identifier_id,
                "property_id": event.property_id,
                "animal_id": animal_id,
                "scheme": "DISPLAY_IDENTIFIER",
                "value": display_identifier,
                "issuer": "FARM",
                "valid_from": event.occurred_on.isoformat(),
                "valid_to": "",
                "status": "ACTIVE",
                "source_event_id": event.event_id,
                "evidence_ref": "",
            },
            "03_Identificadores_Animal",
            "identifier_id",
        )

    async def _append_allocation(
        self, event: ValidatedEvent, animal_id: str, group_id: str, suffix: str, captured_at: str
    ) -> None:
        allocation_id = self._stable_id(f"{event.event_id}:allocation:{animal_id}:{group_id}")
        await self._effect(
            event,
            f"allocation:{suffix}:{animal_id}:{group_id}",
            "GROUP_ALLOCATION",
            "allocation",
            allocation_id,
            "append_allocation",
            {
                "allocation_id": allocation_id,
                "property_id": event.property_id,
                "animal_id": animal_id,
                "group_id": group_id,
                "location_id": "",
                "effective_from": event.occurred_on.isoformat(),
                "effective_to": "",
                "reason": event.event_type.value,
                "event_id": event.event_id,
                "recorded_at": captured_at,
            },
            "05_Alocacoes",
            "allocation_id",
        )

    async def _close_allocation(self, event: ValidatedEvent, animal_id: str, group_id: str) -> None:
        rows = await self._store("read_rows", "05_Alocacoes")
        latest = {str(row["allocation_id"]): row for row in rows if row.get("allocation_id")}
        active = [
            row
            for row in latest.values()
            if row.get("property_id") == event.property_id
            and row.get("animal_id") == animal_id
            and row.get("group_id") == group_id
            and not row.get("effective_to")
        ]
        if len(active) != 1:
            raise ValueError("Alocação de origem ausente ou ambígua; revisão manual necessária.")
        old = active[0]
        closed = dict(old)
        closed["effective_to"] = event.occurred_on.isoformat()
        closed["event_id"] = event.event_id
        closed["recorded_at"] = datetime.now(UTC).isoformat()
        await self._effect(
            event,
            f"close-allocation:{old['allocation_id']}",
            "CLOSE_GROUP_ALLOCATION",
            "allocation",
            str(old["allocation_id"]),
            "append_allocation",
            closed,
            "05_Alocacoes",
            "event_id",
        )

    async def _current_group(self, property_id: str, animal_id: str) -> str | None:
        rows = await self._store("read_rows", "05_Alocacoes")
        latest = {str(row["allocation_id"]): row for row in rows if row.get("allocation_id")}
        active = [
            row
            for row in latest.values()
            if row.get("property_id") == property_id
            and row.get("animal_id") == animal_id
            and not row.get("effective_to")
        ]
        if len(active) == 1:
            return str(active[0]["group_id"])
        return None

    def _event_row(
        self,
        event: ValidatedEvent,
        user_id: int,
        command_id: str,
        message_id: str,
        source: str,
        captured_at: str,
        source_reference: str | None,
        confirmed: bool,
        processing_status: str,
    ) -> dict[str, Any]:
        return {
            "event_id": event.event_id,
            "event_type": event.event_type.value,
            "occurred_from": event.occurred_on.isoformat(),
            "occurred_to": "",
            "time_precision": "DAY",
            "time_source": event.time_source.value,
            "timezone": self.settings.farm_timezone,
            "original_time_expression": event.original_time_expression,
            "recorded_at": datetime.now(UTC).isoformat(),
            "actor_id": str(user_id),
            "channel": "TELEGRAM",
            "target_scope": (
                "GROUP" if event.event_type == EventType.VACCINATION and event.payload.get("group_id") else "INDIVIDUAL"
            ),
            "property_id": event.property_id,
            "source_message_id": message_id,
            "evidence_ref": source_reference or "",
            "interpretation_confirmation": "USER_CONFIRMED" if confirmed else "NOT_REQUIRED",
            "evidence_status": event.payload.get("status", "REPORTED"),
            "event_status": "CONFIRMED" if confirmed else "RECORDED",
            "command_id": command_id,
            "correction_of": event.correction_of or "",
            "processing_status": processing_status,
            "event_payload_json": json.dumps(event.payload, ensure_ascii=False, sort_keys=True),
        }

    async def _record_conversation(
        self,
        user_id: int,
        command_id: str,
        message_id: str,
        source: str,
        captured_at: str,
        device_timezone: str | None,
        source_reference: str | None,
        text: str,
        proposal: InterpretationProposal,
        state: str,
        response: str,
        *,
        pending: dict[str, Any] | None = None,
        events: list[ValidatedEvent] | None = None,
        missing_fields: list[str] | None = None,
        received_at: str | None = None,
    ) -> None:
        conversation = {
            "message_id": f"{message_id}:{state.lower()}",
            "property_id": self.settings.farm_property_id,
            "command_id": command_id,
            "user_id": str(user_id),
            "channel": source.upper(),
            "received_at": received_at or datetime.now(UTC).isoformat(),
            "captured_at": captured_at,
            "device_timezone": device_timezone or "UNKNOWN",
            "resolved_at": datetime.now(UTC).isoformat(),
            "raw_text_ref": message_id,
            "audio_ref": source_reference or "",
            "transcript": text,
            "transcript_confidence": "",
            "interpretation_id": command_id,
            "intents": json.dumps([event.event_type for event in proposal.events]),
            "entity_candidates": json.dumps(
                [event.model_dump(mode="json") for event in proposal.events], ensure_ascii=False
            ),
            "missing_fields": json.dumps(missing_fields or [], ensure_ascii=False),
            "confirmation_prompt": response,
            "response": response,
            "model/version": self.settings.interpretation_model,
            "state": state,
            "event_ids": json.dumps([event.event_id for event in events or []]),
            "pending_command_json": json.dumps(pending or {}, ensure_ascii=False, sort_keys=True),
            "callback_chat_id": "",
            "callback_message_id": "",
        }
        await self._store("append_conversation", conversation)
        await self._audit_conversation_state(conversation, state, response)

    async def _append_conversation_state(self, row: dict[str, Any], state: str, response: str) -> None:
        updated = dict(row)
        updated["message_id"] = f"{row['message_id']}:{state.lower()}"
        updated["state"] = state
        updated["response"] = response
        updated["confirmation_prompt"] = response
        updated["resolved_at"] = datetime.now(UTC).isoformat()
        await self._store("append_conversation", updated)
        await self._audit_conversation_state(updated, state, response)

    async def _audit_conversation_state(self, row: dict[str, Any], state: str, response: str) -> None:
        command_id = str(row.get("command_id", ""))
        message_id = str(row.get("message_id", ""))
        key = f"{command_id}:conversation:{message_id}:{state}"
        try:
            event_ids = json.loads(row.get("event_ids") or "[]")
            await self._store(
                "append_audit",
                {
                    "audit_id": self._stable_id(key),
                    "property_id": row.get("property_id", self.settings.farm_property_id),
                    "command_id": command_id,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "actor": str(row.get("user_id", "")),
                    "channel": row.get("channel", "TELEGRAM"),
                    "raw_message_ref": row.get("raw_text_ref", ""),
                    "transcript_ref": row.get("audio_ref", ""),
                    "interpretation": row.get("entity_candidates", ""),
                    "confirmation": response if state in {"WAITING_CONFIRMATION", "CONFIRMED"} else state,
                    "event_ids": ",".join(map(str, event_ids)),
                    "affected_record_ids": ",".join(map(str, event_ids)),
                    "action": "CONVERSATION_STATE",
                    "prior_state_ref": "",
                    "resulting_state_ref": state,
                    "error": response if state in {"REJECTED", "MANUAL_REVIEW", "PARTIALLY_APPLIED"} else "",
                    "correction_of": "",
                    "idempotency_key": key,
                },
            )
        except Exception:
            logger.error("Could not append conversation audit command=%s state=%s", command_id, state)

    async def _record_duplicate(
        self, user_id: int, command_id: str, message_id: str, source: str, affected: Any
    ) -> None:
        key = f"{command_id}:duplicate:{message_id}"
        try:
            if isinstance(affected, str):
                try:
                    event_ids = json.loads(affected)
                except (TypeError, ValueError):
                    event_ids = [affected] if affected else []
            elif isinstance(affected, list):
                event_ids = affected
            else:
                event_ids = [affected] if affected else []
            await self._store(
                "append_audit",
                {
                    "audit_id": self._stable_id(key),
                    "property_id": self.settings.farm_property_id,
                    "command_id": command_id,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "actor": str(user_id),
                    "channel": source.upper(),
                    "raw_message_ref": message_id,
                    "transcript_ref": "",
                    "interpretation": "",
                    "confirmation": "DUPLICATE",
                    "event_ids": ",".join(map(str, event_ids)),
                    "affected_record_ids": ",".join(map(str, event_ids)),
                    "action": "DUPLICATE_DELIVERY",
                    "prior_state_ref": "",
                    "resulting_state_ref": "UNCHANGED",
                    "error": "",
                    "correction_of": "",
                    "idempotency_key": key,
                },
            )
        except Exception:
            logger.error("Could not record duplicate delivery command=%s", command_id)

    async def _conversation_by_message(self, message_id: str) -> dict[str, Any] | None:
        rows = await self._store("read_rows", "18_Conversas")
        return next((row for row in reversed(rows) if row.get("raw_text_ref") == message_id), None)

    async def _latest_conversation(self, command_id: str) -> dict[str, Any] | None:
        rows = await self._store("read_rows", "18_Conversas")
        return next((row for row in reversed(rows) if row.get("command_id") == command_id), None)

    async def _latest_open_conversation(self, user_id: int) -> dict[str, Any] | None:
        row = await self._latest_open_conversation_any_state(user_id)
        return row if row and row.get("state") == "NEEDS_CLARIFICATION" else None

    async def _ensure_trusted_rows(self, user_id: int) -> None:
        properties = await self._store("read_rows", "01_Propriedades")
        configured = [row for row in properties if row.get("property_id") == self.settings.farm_property_id]
        if configured and any(row.get("timezone") != self.settings.farm_timezone for row in configured):
            raise ValueError("O timezone da propriedade na planilha diverge de FARM_TIMEZONE.")
        if not configured:
            await self._store(
                "append_rows",
                "01_Propriedades",
                [
                    {
                        "property_id": self.settings.farm_property_id,
                        "nome": self.settings.farm_property_id,
                        "municipio": "",
                        "UF": "",
                        "timezone": self.settings.farm_timezone,
                        "owner_id": "",
                        "operator_id": "",
                        "sistema_producao": "UNKNOWN",
                        "identification_regime": "UNKNOWN",
                        "created_at": datetime.now(UTC).isoformat(),
                    }
                ],
            )
        # Telegram_Access is the authority. Do not auto-create a trusted
        # 19_Usuarios row here: an old active projection could revive revocation.

    def _trusted_context(
        self, user_id: int, command_id: str, captured_at: str, *, inferred_captured_at: str | None = None
    ) -> TrustedContext:
        try:
            instant = datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
        except (TypeError, ValueError):
            raise ValueError(
                "captured_at inválido; não vou resolver datas relativas usando o relógio do servidor."
            ) from None
        if instant.tzinfo is None:
            raise ValueError("captured_at precisa incluir fuso horário; não vou assumir um fuso silenciosamente.")
        return TrustedContext(
            property_id=self.settings.farm_property_id,
            actor_id=str(user_id),
            request_id=command_id,
            timezone=self.settings.farm_timezone,
            now=instant,
            inferred_on=(
                datetime.fromisoformat(inferred_captured_at.replace("Z", "+00:00"))
                .astimezone(ZoneInfo(self.settings.farm_timezone))
                .date()
                if inferred_captured_at
                else instant.astimezone(ZoneInfo(self.settings.farm_timezone)).date()
            ),
        )

    @classmethod
    def _string_values(cls, value: Any) -> set[str]:
        if isinstance(value, dict):
            return set().union(*(cls._string_values(item) for item in value.values())) if value else set()
        if isinstance(value, list):
            return set().union(*(cls._string_values(item) for item in value)) if value else set()
        return {value} if isinstance(value, str) else set()

    async def _history(self, user_id: int, text: str) -> BotReply:
        parts = text.strip().split(maxsplit=1)
        if len(parts) != 2 or not parts[1].strip():
            return BotReply("Use /historico <número do brinco>.")
        identifier = parts[1].strip()
        animal, ambiguous = await self._try_resolve_animal(self.settings.farm_property_id, identifier)
        if ambiguous:
            return BotReply(
                f"O identificador {identifier} corresponde a mais de um animal nesta fazenda. "
                "Informe um identificador único."
            )
        if not animal:
            return BotReply("Não encontrei esse animal nesta fazenda.")
        event_rows = await self._store("read_rows", "06_Eventos")
        target_rows = await self._store("read_rows", "07_Evento_Animais")
        event_ids = {
            str(row["event_id"])
            for row in target_rows
            if row.get("property_id") == self.settings.farm_property_id and row.get("animal_id") == animal["animal_id"]
        }
        group_targets = [
            row
            for row in target_rows
            if row.get("property_id") == self.settings.farm_property_id
            and row.get("group_id")
            and row.get("target_basis") == "GROUP_MEMBERSHIP"
        ]
        allocations = await self._store("read_rows", "05_Alocacoes")
        latest_allocations = {str(row["allocation_id"]): row for row in allocations if row.get("allocation_id")}
        latest_events = {str(row["event_id"]): row for row in event_rows if row.get("event_id")}
        for target in group_targets:
            event = latest_events.get(str(target.get("event_id")))
            if not event:
                continue
            event_date = str(event.get("occurred_from") or "")[:10]
            if not event_date:
                continue
            belongs_to_group = any(
                allocation.get("property_id") == self.settings.farm_property_id
                and allocation.get("animal_id") == animal["animal_id"]
                and allocation.get("group_id") == target["group_id"]
                and str(allocation.get("effective_from") or "")[:10] <= event_date
                and (not allocation.get("effective_to") or event_date < str(allocation.get("effective_to") or "")[:10])
                for allocation in latest_allocations.values()
            )
            if belongs_to_group:
                event_ids.add(str(target["event_id"]))
        relevant = [row for row in event_rows if row.get("event_id") in event_ids]
        for row in event_rows:
            if row.get("property_id") != self.settings.farm_property_id:
                continue
            if row.get("processing_status") != "PARTIALLY_APPLIED":
                continue
            try:
                payload = json.loads(row.get("event_payload_json") or "{}")
            except (TypeError, json.JSONDecodeError):
                continue
            if identifier in self._string_values(payload):
                relevant.append(row)
        for row in latest_events.values():
            if row.get("property_id") != self.settings.farm_property_id:
                continue
            if row.get("processing_status") != "PARTIALLY_APPLIED":
                continue
            try:
                payload = json.loads(row.get("event_payload_json") or "{}")
            except (TypeError, json.JSONDecodeError):
                continue
            group_id = payload.get("group_id")
            if not group_id:
                continue
            event_date = str(row.get("occurred_from") or "")[:10]
            if any(
                allocation.get("property_id") == self.settings.farm_property_id
                and allocation.get("animal_id") == animal["animal_id"]
                and allocation.get("group_id") == group_id
                and str(allocation.get("effective_from") or "")[:10] <= event_date
                and (not allocation.get("effective_to") or event_date < str(allocation.get("effective_to") or "")[:10])
                for allocation in latest_allocations.values()
            ):
                relevant.append(row)
        latest_by_event: dict[str, dict[str, Any]] = {}
        for row in relevant:
            latest_by_event[str(row["event_id"])] = row
        corrected_ids = {
            str(row.get("correction_of"))
            for row in event_rows
            if row.get("property_id") == self.settings.farm_property_id
            and row.get("correction_of")
            and row.get("processing_status") == "APPLIED"
        }
        active = [row for event_id, row in latest_by_event.items() if event_id not in corrected_ids]
        events = sorted(active, key=lambda row: row.get("occurred_from", ""), reverse=True)[:10]
        if not events:
            return BotReply(f"Ainda não há eventos registrados para {parts[1].strip()}.")
        lines = [f"Histórico de {parts[1].strip()}:"]
        for event in events:
            fields = json.loads(event.get("event_payload_json") or "{}")
            description = self._describe_event(event["event_type"], fields)
            correction = f" (corrige {event['correction_of']})" if event.get("correction_of") else ""
            partial = (
                " [registro parcial; precisa de reconciliação]"
                if event.get("processing_status") == "PARTIALLY_APPLIED"
                else ""
            )
            lines.append(
                f"• {MVPProcessor._format_date(event.get('occurred_from'))} "
                f"[{event.get('event_id', 'sem ID')}]{correction}: {description}{partial}"
            )
        return BotReply("\n".join(lines))

    async def _cancel_latest(self, user_id: int) -> BotReply:
        row = await self._latest_open_conversation_any_state(user_id)
        if not row:
            return BotReply("Você não tem nenhum comando aguardando esclarecimento ou confirmação.")
        await self._append_conversation_state(row, "CANCELLED", "Registro cancelado pelo usuário.")
        return BotReply("Registro cancelado. Nenhum evento será gravado.")

    async def _safe_error_audit(self, user_id: int, command_id: str, message_id: str, source: str, text: str) -> None:
        try:
            await self._store(
                "append_audit",
                {
                    "audit_id": self._stable_id(f"{command_id}:receive-error"),
                    "property_id": self.settings.farm_property_id,
                    "command_id": command_id,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "actor": str(user_id),
                    "channel": source,
                    "raw_message_ref": message_id,
                    "transcript_ref": "",
                    "interpretation": "",
                    "confirmation": "",
                    "event_ids": "",
                    "affected_record_ids": "",
                    "action": "PROCESSING_FAILED",
                    "prior_state_ref": "",
                    "resulting_state_ref": "",
                    "error": "processing failed; details are in restricted application logs",
                    "correction_of": "",
                    "idempotency_key": f"{command_id}:receive-error",
                },
            )
        except Exception:
            logger.error("Could not append failure audit for command=%s", command_id)

    async def _safe_event_failure(self, event_id: str, command_id: str, error: str) -> None:
        try:
            event = await self._store("find_event", event_id)
            if event:
                row = dict(event)
                row["processing_status"] = "PARTIALLY_APPLIED"
                await self._store("append_event", row)
                await self._store(
                    "append_audit",
                    {
                        "audit_id": self._stable_id(f"{command_id}:partial:{event_id}"),
                        "property_id": row.get("property_id", ""),
                        "command_id": command_id,
                        "timestamp": datetime.now(UTC).isoformat(),
                        "actor": row.get("actor_id", ""),
                        "channel": row.get("channel", "TELEGRAM"),
                        "raw_message_ref": row.get("source_message_id", ""),
                        "transcript_ref": "",
                        "interpretation": row.get("event_type", ""),
                        "confirmation": "PARTIAL",
                        "event_ids": event_id,
                        "affected_record_ids": event_id,
                        "action": "PARTIAL_APPLICATION",
                        "prior_state_ref": "",
                        "resulting_state_ref": "PARTIALLY_APPLIED",
                        "error": error[:300],
                        "correction_of": "",
                        "idempotency_key": f"{command_id}:partial:{event_id}",
                    },
                )
        except Exception:
            logger.error("Could not record partial event=%s command=%s", event_id, command_id)

    def _effect_row(
        self,
        event: ValidatedEvent,
        effect_id: str,
        key: str,
        effect_type: str,
        target_type: str,
        target_id: str,
        status: str,
        attempts: int,
        error: str,
    ) -> dict[str, Any]:
        return {
            "effect_id": effect_id,
            "property_id": event.property_id,
            "source_event_id": event.event_id,
            "effect_type": effect_type,
            "target_type": target_type,
            "target_id": target_id,
            "idempotency_key": key,
            "status": status,
            "attempt_count": attempts,
            "retryable": False,
            "error": error[:300],
            "before_ref": "",
            "after_ref": "",
            "reversed_by": "",
            "updated_at": datetime.now(UTC).isoformat(),
        }

    def _audit_row(
        self,
        event: ValidatedEvent,
        command_id: str,
        user_id: int,
        source: str,
        message_id: str,
        source_reference: str | None,
        action: str,
        error: str | None,
        event_id: str,
    ) -> dict[str, Any]:
        key = f"{command_id}:{action}:{event.event_id}"
        return {
            "audit_id": self._stable_id(key),
            "property_id": event.property_id,
            "command_id": command_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "actor": str(user_id),
            "channel": source,
            "raw_message_ref": message_id,
            "transcript_ref": source_reference or "",
            "interpretation": event.event_type.value,
            "confirmation": action,
            "event_ids": event.event_id,
            "affected_record_ids": event.event_id,
            "action": action,
            "prior_state_ref": event.correction_of or "",
            "resulting_state_ref": event.event_id,
            "error": error or "",
            "correction_of": "",
            "idempotency_key": key,
        }

    async def _latest_open_conversation_any_state(self, user_id: int) -> dict[str, Any] | None:
        rows = await self._store("read_rows", "18_Conversas")
        latest = next((row for row in reversed(rows) if row.get("user_id") == str(user_id)), None)
        if latest and latest.get("state") in {"NEEDS_CLARIFICATION", "WAITING_CONFIRMATION"}:
            return latest
        return None

    def _target_animal_ids(self, event: ValidatedEvent) -> list[str]:
        payload = event.payload
        if event.event_type == EventType.CALVING:
            animals = [str(payload["mother_id"])] if payload.get("mother_id") else []
            animals.extend(str(item["animal_id"]) for item in payload.get("outcomes", []) if item.get("animal_id"))
            return animals
        if event.event_type == EventType.ANIMAL_CREATED and payload.get("new_animal_id"):
            return [str(payload["new_animal_id"])]
        animal_id = payload.get("animal_id")
        return [str(animal_id)] if animal_id else []

    @staticmethod
    def _is_live(outcome: dict[str, Any]) -> bool:
        status = str(outcome.get("live_status") or "").strip().upper().replace(" ", "_").replace("-", "_")
        result = str(outcome.get("outcome") or "").strip().upper().replace(" ", "_").replace("-", "_")
        positive_statuses = {"LIVE", "VIVO", "VIVA", "ALIVE", "NASCIDO_VIVO", "LIVE_BIRTH"}
        positive_outcomes = {"LIVE_CALF", "BEZERRO_VIVO", "BEZERRA_VIVA"}
        negative_statuses = {"NOT_LIVE", "STILLBORN", "NATIMORTO", "MORTO", "MORTA", "DEAD"}
        negative_outcomes = {"STILLBORN", "STILL_BORN", "NATIMORTO", "MORTO", "MORTA", "DEAD"}
        if status in negative_statuses or result in negative_outcomes:
            return False
        return status in positive_statuses or result in positive_outcomes

    @staticmethod
    def _liveness_conflicts(outcome: dict[str, Any]) -> bool:
        status = str(outcome.get("live_status") or "").strip().upper().replace(" ", "_").replace("-", "_")
        result = str(outcome.get("outcome") or "").strip().upper().replace(" ", "_").replace("-", "_")
        positive_statuses = {"LIVE", "VIVO", "VIVA", "ALIVE", "NASCIDO_VIVO", "LIVE_BIRTH"}
        positive_outcomes = {"LIVE_CALF", "BEZERRO_VIVO", "BEZERRA_VIVA"}
        negative_statuses = {"NOT_LIVE", "STILLBORN", "NATIMORTO", "MORTO", "MORTA", "DEAD"}
        negative_outcomes = {"STILLBORN", "STILL_BORN", "NATIMORTO", "MORTO", "MORTA", "DEAD"}
        return (status in positive_statuses and result in negative_outcomes) or (
            status in negative_statuses and result in positive_outcomes
        )

    @staticmethod
    def _stable_id(key: str) -> str:
        return uuid5(NAMESPACE_URL, f"agro-notes:{key}").hex

    @staticmethod
    def _clarification(questions: list[str], missing: list[str]) -> str:
        items = questions or ["Informe: " + ", ".join(missing)]
        return "Preciso esclarecer antes de registrar:\n" + "\n".join(f"• {item}" for item in items[:3])

    @staticmethod
    def _preview(events: list[ValidatedEvent]) -> str:
        labels = {
            EventType.ANIMAL_CREATED: ("Cadastro", "display_identifier", "Identificador"),
            EventType.ANIMAL_ENTERED: ("Entrada", "display_identifier", "Identificador"),
            EventType.CALVING: ("Parto", "mother_identifier", "Matriz"),
            EventType.WEIGHING: ("Pesagem", "animal_identifier", "Animal"),
            EventType.LOT_TRANSFER: ("Transferência de lote", "animal_identifier", "Animal"),
            EventType.VACCINATION: ("Vacinação reportada", "animal_identifier", "Animal"),
            EventType.HEALTH_OBSERVATION: ("Observação de saúde", "animal_identifier", "Animal"),
        }
        lines = ["Confira a prévia antes de registrar:"]
        for event in events:
            title, identifier_key, identifier_label = labels[event.event_type]
            payload = event.payload
            lines.append(f"• {title} — {MVPProcessor._format_date(event.occurred_on)}")
            if payload.get(identifier_key):
                lines.append(f"  {identifier_label}: {payload[identifier_key]}")
            if event.correction_of:
                lines.append(f"  Corrige o evento {event.correction_of}")
                previous = event.correction_previous or {}
                previous_field = {
                    EventType.WEIGHING: ("weight_kg", "Peso"),
                    EventType.VACCINATION: ("vaccine", "Produto"),
                    EventType.HEALTH_OBSERVATION: ("observation", "Relato"),
                }.get(event.event_type)
                if previous_field:
                    field, label = previous_field
                    previous_value = previous.get(field, "não informado")
                    if field == "weight_kg" and isinstance(previous_value, (int, float)):
                        previous_value = f"{previous_value:g} kg"
                    lines.append(f"  {label} anterior: {previous_value}")
            if event.event_type == EventType.WEIGHING:
                weight = payload.get("weight_kg")
                rendered_weight = f"{weight:g}" if isinstance(weight, (int, float)) else weight
                lines.append(f"  Peso: {rendered_weight} kg")
            elif event.event_type == EventType.ANIMAL_CREATED:
                for key, label in (
                    ("species", "Espécie"),
                    ("sex", "Sexo"),
                    ("breed", "Raça"),
                    ("origin", "Origem"),
                    ("notes", "Observação"),
                ):
                    if payload.get(key):
                        lines.append(f"  {label}: {payload[key]}")
                if payload.get("birth_date"):
                    lines.append(f"  Nascimento: {MVPProcessor._format_date(payload['birth_date'])}")
            elif event.event_type == EventType.ANIMAL_ENTERED and payload.get("origin"):
                lines.append(f"  Origem: {payload['origin']}")
            elif event.event_type == EventType.LOT_TRANSFER:
                if payload.get("from_group_identifier"):
                    lines.append(f"  Lote de origem: {payload['from_group_identifier']}")
                lines.append(f"  Lote destino: {payload.get('to_group_identifier')}")
            elif event.event_type == EventType.VACCINATION:
                target_label = (
                    f"Lote: {payload['group_identifier']}"
                    if payload.get("group_identifier")
                    else f"Animal: {payload.get('animal_identifier')}"
                )
                lines.append(f"  {target_label}")
                lines.append(f"  Produto: {payload.get('vaccine')}")
                if payload.get("dose"):
                    lines.append(f"  Dose informada: {payload['dose']}")
            elif event.event_type == EventType.HEALTH_OBSERVATION:
                details = payload.get("observation") or payload.get("observed_sign")
                if payload.get("body_region") and payload["body_region"] not in str(details):
                    details = f"{details}; região: {payload['body_region']}"
                lines.append(f"  Relato: {details}")
            elif event.event_type == EventType.CALVING:
                outcomes = payload.get("outcomes", [])
                lines.append(f"  Resultados: {len(outcomes)}")
                for outcome in outcomes:
                    details = [outcome.get("outcome") or "resultado não informado"]
                    if outcome.get("sex"):
                        details.append(str(outcome["sex"]))
                    if outcome.get("display_identifier"):
                        details.append(f"número {outcome['display_identifier']}")
                    if outcome.get("live_status"):
                        details.append(str(outcome["live_status"]))
                    if outcome.get("birth_weight"):
                        unit = outcome.get("weight_unit") or "kg"
                        details.append(f"{outcome['birth_weight']} {unit}")
                    lines.append("  - " + ", ".join(details))
                    if outcome.get("animal_id"):
                        lines.append("    Será criado o cadastro da cria e o vínculo com a matriz.")
            if payload.get("group_identifier"):
                lines.append(f"  Lote: {payload['group_identifier']}")
        lines.append("Confirme para gravar, ou cancele para descartar.")
        return "\n".join(lines)

    @staticmethod
    def _format_date(value: Any) -> str:
        try:
            date_value = value if isinstance(value, date) else date.fromisoformat(str(value)[:10])
            return date_value.strftime("%d/%m/%Y")
        except (TypeError, ValueError):
            return "data desconhecida"

    @staticmethod
    def _success_line(event: ValidatedEvent) -> str:
        payload = event.payload
        date_label = MVPProcessor._format_date(event.occurred_on)
        if event.event_type == EventType.WEIGHING:
            weight = payload.get("weight_kg")
            value = f"{weight:g}" if isinstance(weight, (int, float)) else "não informado"
            label = f"Peso registrado: animal {payload.get('animal_identifier')}, {value} kg"
        elif event.event_type == EventType.HEALTH_OBSERVATION:
            label = (
                f"Observação reportada: animal {payload.get('animal_identifier')}, "
                f"{payload.get('observation')} (sem diagnóstico)"
            )
        elif event.event_type == EventType.VACCINATION:
            target = (
                f"lote {payload.get('group_identifier')}"
                if payload.get("group_identifier")
                else f"animal {payload.get('animal_identifier')}"
            )
            label = f"Vacinação relatada: {target}, {payload.get('vaccine')}"
        elif event.event_type == EventType.LOT_TRANSFER:
            label = (
                f"Transferência registrada: animal {payload.get('animal_identifier')} "
                f"para o lote {payload.get('to_group_identifier')}"
            )
        elif event.event_type == EventType.CALVING:
            label = (
                f"Parto registrado: matriz {payload.get('mother_identifier')}, "
                f"{len(payload.get('outcomes', []))} resultado(s)"
            )
        elif event.event_type == EventType.ANIMAL_CREATED:
            label = f"Animal cadastrado: {payload.get('display_identifier')}"
        else:
            label = f"Entrada registrada: animal {payload.get('display_identifier')}"
        if event.correction_of:
            label += f"; corrige o evento {event.correction_of}"
        return f"{label} ({date_label})."

    @staticmethod
    def _duplicate_reply(row: dict[str, Any]) -> str:
        if row.get("processing_status") == "APPLIED":
            return "✅ Esse comando já foi registrado; não criei outro evento."
        return "⚠️ Esse comando já foi iniciado e precisa de reconciliação; não repeti a escrita."

    @staticmethod
    def _describe_event(event_type: str, payload: dict[str, Any]) -> str:
        if event_type == EventType.WEIGHING.value:
            weight = payload.get("weight_kg")
            rendered_weight = f"{weight:g}" if isinstance(weight, (int, float)) else "não informado"
            return f"Pesagem: {rendered_weight} kg"
        if event_type == EventType.VACCINATION.value:
            target = (
                f"no lote {payload['group_identifier']}"
                if payload.get("group_identifier")
                else f"no animal {payload.get('animal_identifier')}"
            )
            return f"Vacinação reportada {target}: {payload.get('vaccine', 'produto não informado')}"
        if event_type == EventType.HEALTH_OBSERVATION.value:
            details = payload.get("observation", "")
            if payload.get("observed_sign") or payload.get("body_region"):
                details = ", ".join(
                    str(value) for value in (payload.get("observed_sign"), payload.get("body_region")) if value
                )
            return f"Observação reportada: {details} (sem diagnóstico)"
        if event_type == EventType.LOT_TRANSFER.value:
            return (
                f"Transferência de lote: {payload.get('from_group_identifier', '?')} → "
                f"{payload.get('to_group_identifier', '?')}"
            )
        return event_type
