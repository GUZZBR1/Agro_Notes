"""Single-process local web interface for exercising livestock event workflows."""

from __future__ import annotations

import argparse
import asyncio
import base64
import binascii
import json
import mimetypes
import sys
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .application import MVPProcessor
from .local_cli import LocalSettings, _run_action
from .local_interpreter import JsonProposalInterpreter
from .local_store import LocalEventStore
from .provider_factory import build_interpreter
from .settings import Settings

MAX_REQUEST_BYTES = 1_000_000
MAX_CHAT_REQUEST_BYTES = 16_000_000
MAX_CHAT_ATTACHMENT_BYTES = 4_000_000
MAX_CHAT_ATTACHMENTS_TOTAL_BYTES = 10_000_000
MAX_CHAT_SESSION_BYTES = 50_000_000
MAX_CHAT_ATTACHMENTS = 5
MAX_CHAT_TEXT_CHARS = 10_000
MAX_CHAT_MESSAGES = 200
ALLOWED_AUDIO_MIME_TYPES = frozenset(
    {"audio/aac", "audio/mp4", "audio/mpeg", "audio/ogg", "audio/wav", "audio/webm", "audio/x-m4a"}
)
WEB_ROOT = Path(__file__).with_name("web")
STATIC_FILES = {
    "/": "index.html",
    "/index.html": "index.html",
    "/app.css": "app.css",
    "/app.js": "app.js",
}


class LocalWebRuntime:
    """Own the in-memory session and one event loop for serialized HTTP calls."""

    def __init__(
        self,
        property_id: str,
        actor_id: int,
        timezone: str,
        *,
        groq_enabled: bool | None = None,
    ) -> None:
        self.property_id = property_id
        self.actor_id = actor_id
        self.timezone = timezone
        self.store = LocalEventStore()
        provider_settings = Settings()
        configured_for_groq = provider_settings.ai_provider == "groq" and bool(provider_settings.groq_api_key.strip())
        self.groq_enabled = configured_for_groq if groq_enabled is None else groq_enabled
        if self.groq_enabled and not provider_settings.groq_api_key.strip():
            raise ValueError("Groq está habilitado, mas GROQ_API_KEY não está configurada.")
        if self.groq_enabled and provider_settings.ai_provider != "groq":
            raise ValueError("Defina AI_PROVIDER=groq para habilitar a interpretação Groq no chat local.")
        self.settings = LocalSettings(
            farm_property_id=property_id,
            farm_timezone=timezone,
            allowed_user_ids=frozenset({actor_id}),
            min_interpretation_confidence=provider_settings.min_interpretation_confidence,
            interpretation_model=provider_settings.interpretation_model if self.groq_enabled else "explicit-json",
        )
        self.json_processor = MVPProcessor(self.settings, self.store, JsonProposalInterpreter())
        self.processor = MVPProcessor(
            self.settings,
            self.store,
            build_interpreter(provider_settings) if self.groq_enabled else JsonProposalInterpreter(),
        )
        self.loop = asyncio.new_event_loop()
        self.sequence = 0
        self.chat_messages: list[dict[str, Any]] = []
        self.chat_attachment_bytes = 0

    def state(self) -> dict[str, Any]:
        rows = self.store.read_rows("18_Conversas")
        latest = next(
            (
                row
                for row in reversed(rows)
                if row.get("user_id") == str(self.actor_id)
                and row.get("state") not in self.processor._transcription_queue_states
            ),
            None,
        )
        last_interaction = None
        if latest:
            is_pending = latest.get("state") == "WAITING_CONFIRMATION"
            last_interaction = {
                "state": latest.get("state"),
                "text": latest.get("response") or latest.get("confirmation_prompt") or "",
                "pending_id": latest.get("command_id") if is_pending else None,
            }
        return {
            "ok": True,
            "property_id": self.property_id,
            "actor_id": self.actor_id,
            "timezone": self.timezone,
            "groq_enabled": self.groq_enabled,
            "last_interaction": last_interaction,
            "store": self.store.snapshot(),
        }

    def action(self, body: dict[str, Any]) -> dict[str, Any]:
        self.sequence += 1
        if body.get("action") == "record":
            latest = next(
                (
                    row
                    for row in reversed(self.store.read_rows("18_Conversas"))
                    if row.get("user_id") == str(self.actor_id)
                    and row.get("state") not in self.processor._transcription_queue_states
                ),
                None,
            )
            if latest and latest.get("state") == "NEEDS_CLARIFICATION":
                self.loop.run_until_complete(
                    self.processor._append_conversation_state(
                        latest,
                        "CANCELLED",
                        "Proposta substituída por um novo formulário local.",
                    )
                )
        result = self.loop.run_until_complete(
            _run_action(self.json_processor, self.store, self.actor_id, body, self.sequence, source="local-web")
        )
        response = {"ok": True, **result}
        operation = body.get("action")
        if operation == "record":
            command_id = f"LOCAL:{self.actor_id}:{body.get('message_id', self.sequence)}"
        else:
            command_id = body.get("pending_id")
        conversation = next(
            (row for row in reversed(self.store.read_rows("18_Conversas")) if row.get("command_id") == command_id),
            None,
        )
        if conversation:
            response["state"] = conversation.get("state")
        return response

    def interpret_text(self, text: str, message_id: str) -> dict[str, Any]:
        if not self.groq_enabled:
            raise ValueError("A interpretação Groq não está habilitada nesta sessão local.")
        reply = self.loop.run_until_complete(
            self.processor.receive(
                self.actor_id,
                text,
                source="local-web",
                message_id=message_id,
                captured_at=datetime.now(UTC).isoformat(),
                device_timezone=self.timezone,
                source_reference=None,
            )
        )
        command_id = f"LOCAL:{self.actor_id}:{message_id}"
        conversation = next(
            (row for row in reversed(self.store.read_rows("18_Conversas")) if row.get("command_id") == command_id),
            None,
        )
        response: dict[str, Any] = {"text": reply.text, "pending_id": reply.pending_id}
        if conversation:
            response["state"] = conversation.get("state")
        return response

    def close(self) -> None:
        if self.groq_enabled:
            self.processor.interpreter.close()
        self.loop.close()

    def chat(self) -> dict[str, Any]:
        return {"ok": True, "messages": self.chat_messages}

    def chat_post(self, body: dict[str, Any]) -> dict[str, Any]:
        if len(self.chat_messages) + 2 > MAX_CHAT_MESSAGES:
            raise ValueError("Esta conversa local atingiu o limite de 200 mensagens. Reinicie a sessão para continuar.")
        start_index = len(self.chat_messages)
        operation = body.get("action")
        if operation in {"confirm", "cancel"}:
            pending_id = body.get("pending_id")
            if not isinstance(pending_id, str) or not pending_id.startswith("LOCAL:"):
                raise ValueError(f"{operation} exige pending_id LOCAL")
            self.chat_messages.append(
                self._chat_message("user", "Confirmar registro" if operation == "confirm" else "Cancelar registro")
            )
            result = self.action({"action": operation, "pending_id": pending_id})
            self.chat_messages.append(
                self._chat_message(
                    "assistant",
                    result.get("text", "Ação concluída."),
                    state=result.get("state"),
                    pending_id=result.get("pending_id"),
                )
            )
            return {"ok": True, "messages": self.chat_messages[start_index:]}
        if operation is not None:
            raise ValueError("action deve ser confirm ou cancel")

        text = body.get("text", "")
        if not isinstance(text, str):
            raise ValueError("text precisa ser uma mensagem de texto")
        if len(text) > MAX_CHAT_TEXT_CHARS:
            raise ValueError(f"A mensagem pode ter até {MAX_CHAT_TEXT_CHARS} caracteres.")
        attachments = self._validate_attachments(body.get("attachments", []))
        if not text.strip() and not attachments:
            raise ValueError("Envie uma mensagem ou anexe uma foto/áudio.")
        incoming_bytes = sum(len(base64.b64decode(item["data"])) for item in attachments)
        if self.chat_attachment_bytes + incoming_bytes > MAX_CHAT_SESSION_BYTES:
            raise ValueError("Os anexos desta sessão local excedem o limite total de 50 MB.")
        self.chat_attachment_bytes += incoming_bytes

        self.sequence += 1
        message_id = f"CHAT-{self.sequence}"
        user_message = self._chat_message("user", text, attachments=attachments or None)
        self.chat_messages.append(user_message)

        result: dict[str, Any] | None = None
        proposal = self._proposal_from_text(text)
        if proposal is not None:
            result = self.action(
                {
                    "action": "record",
                    "message_id": message_id,
                    "proposal": proposal,
                    "captured_at": datetime.now(UTC).isoformat(),
                }
            )
            answer = result.get("text", "Proposta processada.")
        elif self.groq_enabled and text.strip():
            result = self.interpret_text(text, message_id)
            answer = result.get("text", "Texto processado pelo Groq.")
        else:
            answer = ""
            if text.strip():
                answer = (
                    "Sua mensagem foi recebida, mas não foi interpretada: "
                    "configure GROQ_API_KEY para ativar o Groq."
                )

        if result:
            if any(item["mime_type"].startswith("image/") for item in attachments):
                answer += " A foto foi recebida e exibida, sem análise automática."
            if any(item["mime_type"] in ALLOWED_AUDIO_MIME_TYPES for item in attachments):
                answer += " O áudio foi recebido e exibido, sem transcrição."
        else:
            if any(item["mime_type"].startswith("image/") for item in attachments):
                answer += (" " if answer else "") + "A foto foi recebida e exibida, sem análise automática."
            if any(item["mime_type"] in ALLOWED_AUDIO_MIME_TYPES for item in attachments):
                answer += (" " if answer else "") + "O áudio foi recebido e exibido, sem transcrição."

        extra: dict[str, Any] = {}
        if result:
            extra = {
                key: result[key]
                for key in ("state", "pending_id", "document")
                if key in result and result[key] is not None
            }
            if proposal is not None:
                extra.setdefault("document", proposal)
        self.chat_messages.append(self._chat_message("assistant", answer, **extra))
        return {"ok": True, "messages": self.chat_messages[start_index:]}

    def _validate_attachments(self, value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            raise ValueError("attachments precisa ser uma lista")
        if len(value) > MAX_CHAT_ATTACHMENTS:
            raise ValueError(f"Envie no máximo {MAX_CHAT_ATTACHMENTS} anexos por mensagem.")
        result: list[dict[str, Any]] = []
        total_bytes = 0
        for item in value:
            if not isinstance(item, dict):
                raise ValueError("Cada anexo precisa ser um objeto")
            filename = item.get("filename")
            mime_type = item.get("mime_type")
            encoded = item.get("data")
            if not isinstance(filename, str) or not filename.strip() or len(filename) > 255:
                raise ValueError("Cada anexo precisa ter um nome válido de até 255 caracteres")
            if not isinstance(mime_type, str):
                raise ValueError("Tipo de mídia do anexo inválido")
            mime_type = mime_type.split(";", 1)[0].strip().casefold()
            is_image = mime_type.startswith("image/") and mime_type != "image/svg+xml"
            if not is_image and mime_type not in ALLOWED_AUDIO_MIME_TYPES:
                raise ValueError("Tipo de arquivo não permitido; envie imagem ou áudio compatível.")
            if not isinstance(encoded, str) or len(encoded) > ((MAX_CHAT_ATTACHMENT_BYTES + 2) // 3) * 4:
                raise ValueError("Anexo vazio ou acima do limite de 4 MB")
            try:
                data = base64.b64decode(encoded, validate=True)
            except (binascii.Error, ValueError) as exc:
                raise ValueError("Conteúdo base64 inválido") from exc
            if not data or len(data) > MAX_CHAT_ATTACHMENT_BYTES:
                raise ValueError("Anexo vazio ou acima do limite de 4 MB")
            total_bytes += len(data)
            if total_bytes > MAX_CHAT_ATTACHMENTS_TOTAL_BYTES:
                raise ValueError("Os anexos excedem o limite total de 10 MB por mensagem")
            result.append({"filename": filename.strip(), "mime_type": mime_type, "data": encoded})
        return result

    @staticmethod
    def _proposal_from_text(text: str) -> dict[str, Any] | None:
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            return None
        if isinstance(value, dict) and isinstance(value.get("events"), list):
            return value
        return None

    def _chat_message(self, role: str, text: str, *, attachments: Any = None, **extra: Any) -> dict[str, Any]:
        message: dict[str, Any] = {
            "id": f"CHAT-MSG-{len(self.chat_messages) + 1}",
            "role": role,
            "text": text,
            "created_at": datetime.now(UTC).isoformat(),
        }
        if attachments:
            message["attachments"] = attachments
        message.update({key: value for key, value in extra.items() if value is not None})
        return message


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Abra a bancada web local do Agro Notes, sem serviços externos.")
    parser.add_argument("--property-id", default="FAZENDA-001", help="Identificador local da propriedade")
    parser.add_argument("--actor-id", type=int, default=1, help="Identificador local do operador")
    parser.add_argument("--timezone", default="America/Sao_Paulo")
    parser.add_argument("--port", type=int, default=8765)
    return parser


class LocalWebServer(HTTPServer):
    """HTTP server with an isolated, process-local test session."""

    def __init__(self, address: tuple[str, int], runtime: LocalWebRuntime) -> None:
        self.runtime = runtime
        super().__init__(address, LocalWebHandler)

    def server_close(self) -> None:
        try:
            self.runtime.close()
        finally:
            super().server_close()


class LocalWebHandler(BaseHTTPRequestHandler):
    server: LocalWebServer

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/api/chat":
            self._send_json(self.server.runtime.chat())
            return
        if path == "/api/state":
            self._send_json(self.server.runtime.state())
            return
        filename = STATIC_FILES.get(path)
        if filename is None:
            self._send_json({"ok": False, "error": "Rota não encontrada."}, status=404)
            return
        try:
            data = (WEB_ROOT / filename).read_bytes()
        except OSError:
            self._send_json({"ok": False, "error": "Arquivos da interface não encontrados."}, status=500)
            return
        self._send(
            data,
            mimetypes.guess_type(filename)[0] or "application/octet-stream",
            status=200,
        )

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        if path not in {"/api/action", "/api/chat"}:
            self._send_json({"ok": False, "error": "Rota não encontrada."}, status=404)
            return
        origin = self.headers.get("Origin")
        host = self.headers.get("Host", "")
        if origin and origin != f"http://{host}":
            self._send_json({"ok": False, "error": "Origem da solicitação não permitida."}, status=403)
            return
        if not self.headers.get("Content-Type", "").split(";", 1)[0].strip().casefold() == "application/json":
            self._send_json({"ok": False, "error": "Envie uma solicitação JSON."}, status=415)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json({"ok": False, "error": "Tamanho da solicitação inválido."}, status=400)
            return
        max_size = MAX_CHAT_REQUEST_BYTES if path == "/api/chat" else MAX_REQUEST_BYTES
        if size <= 0 or size > max_size:
            self._send_json({"ok": False, "error": "A solicitação está vazia ou excede o limite local."}, status=413)
            return
        try:
            body = json.loads(self.rfile.read(size))
            if not isinstance(body, dict):
                raise ValueError("A ação precisa ser um objeto JSON.")
            result = (
                self.server.runtime.chat_post(body)
                if path == "/api/chat"
                else self.server.runtime.action(body)
            )
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=400)
            return
        self._send_json(result)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[agro-notes-local-web] {self.address_string()} {format % args}", file=sys.stderr)

    def _send_json(self, value: dict[str, Any], *, status: int = 200) -> None:
        payload = json.dumps(value, ensure_ascii=False, default=str).encode("utf-8")
        self._send(payload, "application/json; charset=utf-8", status=status)

    def _send(self, payload: bytes, content_type: str, *, status: int) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; "
            "img-src 'self' data:; base-uri 'none'; form-action 'self'; frame-ancestors 'none'",
        )
        self.end_headers()
        self.wfile.write(payload)


def main() -> None:
    args = build_parser().parse_args()
    if not args.property_id.strip():
        raise SystemExit("--property-id não pode ficar vazio.")
    if args.actor_id < 1:
        raise SystemExit("--actor-id deve ser um número positivo.")
    if not 1 <= args.port <= 65535:
        raise SystemExit("--port precisa estar entre 1 e 65535.")
    runtime = LocalWebRuntime(args.property_id.strip(), args.actor_id, args.timezone)
    try:
        with LocalWebServer(("127.0.0.1", args.port), runtime) as server:
            print(
                f"Agro Notes local disponível em http://127.0.0.1:{args.port} "
                "(memória temporária; encerre com Ctrl-C).",
                flush=True,
            )
            server.serve_forever()
    except KeyboardInterrupt:
        print("\nSessão local encerrada; os dados em memória foram descartados.", flush=True)


if __name__ == "__main__":
    main()
