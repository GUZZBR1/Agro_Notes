import base64
import json
from datetime import UTC, datetime
from http.client import HTTPConnection
from threading import Thread

import pytest

from agro_notes.local_web import LocalWebRuntime, LocalWebServer


class ChatApi:
    def __init__(self):
        self.runtime = LocalWebRuntime("farm", 7, "America/Sao_Paulo")
        self.server = LocalWebServer(("127.0.0.1", 0), self.runtime)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.connection = HTTPConnection("127.0.0.1", self.server.server_port)

    def get(self):
        self.connection.request("GET", "/api/chat")
        response = self.connection.getresponse()
        return response.status, json.loads(response.read())

    def post(self, body):
        payload = json.dumps(body).encode()
        self.connection.request("POST", "/api/chat", payload, {"Content-Type": "application/json"})
        response = self.connection.getresponse()
        return response.status, json.loads(response.read())

    def close(self):
        self.connection.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


@pytest.fixture
def chat_api():
    api = ChatApi()
    try:
        yield api
    finally:
        api.close()


def test_local_web_requires_preview_for_health_observation_and_confirms_once():
    runtime = LocalWebRuntime("farm", 7, "America/Sao_Paulo")
    try:
        animal = runtime.action(
            {
                "action": "record",
                "message_id": "animal-1",
                "captured_at": datetime(2026, 10, 22, tzinfo=UTC).isoformat(),
                "proposal": {
                    "events": [
                        {
                            "event_type": "ANIMAL_CREATED",
                            "payload": {"display_identifier": "42", "species": "CATTLE"},
                            "time_expression": "hoje",
                            "confidence": 0.99,
                        }
                    ]
                },
            }
        )
        assert animal["state"] == "WAITING_CONFIRMATION"
        runtime.action({"action": "confirm", "pending_id": animal["pending_id"]})

        observation = runtime.action(
            {
                "action": "record",
                "message_id": "health-1",
                "captured_at": datetime(2026, 10, 22, tzinfo=UTC).isoformat(),
                "proposal": {
                    "events": [
                        {
                            "event_type": "HEALTH_OBSERVATION",
                            "payload": {"animal_identifier": "42", "observation": "manca"},
                            "time_expression": "hoje",
                            "confidence": 0.99,
                        }
                    ]
                },
            }
        )
        assert observation["pending_id"] == "LOCAL:7:health-1"
        assert observation["state"] == "WAITING_CONFIRMATION"
        before_confirmation = runtime.state()["store"]["06_Eventos"]
        assert {event["event_type"] for event in before_confirmation} == {"ANIMAL_CREATED"}

        confirmed = runtime.action({"action": "confirm", "pending_id": observation["pending_id"]})
        assert confirmed["text"].startswith("✅")
        after_confirmation = runtime.state()["store"]["06_Eventos"]
        assert {event["event_type"] for event in after_confirmation} == {"ANIMAL_CREATED", "HEALTH_OBSERVATION"}
    finally:
        runtime.close()


def test_new_local_web_proposal_replaces_unresolved_clarification():
    runtime = LocalWebRuntime("farm", 7, "America/Sao_Paulo")
    try:
        unclear = runtime.action(
            {
                "action": "record",
                "message_id": "animal-unclear",
                "captured_at": datetime(2026, 10, 22, tzinfo=UTC).isoformat(),
                "proposal": {
                    "events": [
                        {
                            "event_type": "ANIMAL_CREATED",
                            "payload": {
                                "display_identifier": "42",
                                "species": "CATTLE",
                                "group_identifier": "missing-group",
                            },
                            "time_expression": "2026-10-22",
                            "confidence": 0.99,
                        }
                    ]
                },
            }
        )
        assert unclear["state"] == "NEEDS_CLARIFICATION"
        assert unclear["pending_id"] is None

        replacement = runtime.action(
            {
                "action": "record",
                "message_id": "animal-corrected",
                "captured_at": datetime(2026, 10, 22, tzinfo=UTC).isoformat(),
                "proposal": {
                    "events": [
                        {
                            "event_type": "ANIMAL_CREATED",
                            "payload": {"display_identifier": "42", "species": "CATTLE"},
                            "time_expression": "2026-10-22",
                            "confidence": 0.99,
                        }
                    ]
                },
            }
        )
        assert replacement["state"] == "WAITING_CONFIRMATION"
        assert replacement["pending_id"] == "LOCAL:7:animal-corrected"
    finally:
        runtime.close()


def test_local_web_cancel_does_not_write_pending_event():
    runtime = LocalWebRuntime("farm", 7, "America/Sao_Paulo")
    try:
        preview = runtime.action(
            {
                "action": "record",
                "message_id": "animal-cancel",
                "captured_at": datetime(2026, 10, 22, tzinfo=UTC).isoformat(),
                "proposal": {
                    "events": [
                        {
                            "event_type": "ANIMAL_CREATED",
                            "payload": {"display_identifier": "99", "species": "CATTLE"},
                            "time_expression": "hoje",
                            "confidence": 0.99,
                        }
                    ]
                },
            }
        )
        cancelled = runtime.action({"action": "cancel", "pending_id": preview["pending_id"]})
        assert "cancelado" in cancelled["text"].lower()
        assert runtime.state()["store"]["06_Eventos"] == []
        assert runtime.state()["last_interaction"]["state"] == "CANCELLED"
    finally:
        runtime.close()


def test_chat_get_and_post_accept_text_and_media_and_explain_local_limits(chat_api):
    image = base64.b64encode(b"fake-image").decode()
    audio = base64.b64encode(b"fake-audio").decode()
    status, response = chat_api.post(
        {
            "text": "Anotação para depois",
            "attachments": [
                {"filename": "curral.jpg", "mime_type": "image/jpeg", "data": image},
                {"filename": "relato.webm", "mime_type": "audio/webm", "data": audio},
            ],
        }
    )
    assert status == 200
    user, assistant = response["messages"]
    assert user["role"] == "user"
    assert [attachment["mime_type"] for attachment in user["attachments"]] == ["image/jpeg", "audio/webm"]
    assert "não foi interpretada" in assistant["text"]
    assert "sem análise automática" in assistant["text"]
    assert "sem transcrição" in assistant["text"]
    assert chat_api.get() == (200, response)


@pytest.mark.parametrize(
    ("body", "error"),
    [
        ({"text": "   ", "attachments": []}, "Envie uma mensagem"),
        (
            {
                "text": "foto",
                "attachments": [
                    {"filename": "x.svg", "mime_type": "image/svg+xml", "data": "YWJj"}
                ],
            },
            "não permitido",
        ),
        (
            {
                "text": "áudio",
                "attachments": [
                    {"filename": "x.mp3", "mime_type": "audio/x-unknown", "data": "YWJj"}
                ],
            },
            "não permitido",
        ),
        (
            {
                "text": "foto",
                "attachments": [
                    {"filename": "x.jpg", "mime_type": "image/jpeg", "data": "not-base64!"}
                ],
            },
            "base64 inválido",
        ),
        (
            {
                "text": "foto",
                "attachments": [
                    {
                        "filename": "x.jpg",
                        "mime_type": "image/jpeg",
                        "data": base64.b64encode(b"x" * 4_000_001).decode(),
                    }
                ],
            },
            "4 MB",
        ),
        (
            {
                "text": "fotos",
                "attachments": [
                    {"filename": "x.jpg", "mime_type": "image/jpeg", "data": "eA=="}
                ]
                * 6,
            },
            "no máximo 5",
        ),
        (
            {
                "text": "fotos",
                "attachments": [
                    {
                        "filename": f"x{i}.jpg",
                        "mime_type": "image/jpeg",
                        "data": base64.b64encode(b"x" * 3_500_000).decode(),
                    }
                    for i in range(3)
                ],
            },
            "total de 10 MB",
        ),
    ],
)
def test_chat_rejects_empty_or_unsupported_or_oversized_attachments(chat_api, body, error):
    status, response = chat_api.post(body)
    assert status == 400
    assert error.casefold() in response["error"].casefold()


def test_chat_structured_proposal_can_be_confirmed_and_cancelled(chat_api):
    proposal = {
        "events": [
            {
                "event_type": "ANIMAL_CREATED",
                "payload": {"display_identifier": "77", "species": "CATTLE"},
                "time_expression": "hoje",
                "confidence": 0.99,
            }
        ]
    }
    status, response = chat_api.post({"text": json.dumps(proposal)})
    assert status == 200
    assistant = response["messages"][-1]
    assert assistant["role"] == "assistant"
    assert assistant["state"] == "WAITING_CONFIRMATION"
    assert assistant["pending_id"]
    assert assistant["document"] == proposal
    pending_id = assistant["pending_id"]

    status, confirmed = chat_api.post({"action": "confirm", "pending_id": pending_id})
    assert status == 200
    assert confirmed["messages"][-1]["role"] == "assistant"
    assert "✅" in confirmed["messages"][-1]["text"]
    committed_count = len(chat_api.runtime.state()["store"]["06_Eventos"])
    assert committed_count > 0

    proposal["events"][0]["payload"]["display_identifier"] = "88"
    status, response = chat_api.post({"text": json.dumps(proposal)})
    assert status == 200
    pending_id = response["messages"][-1]["pending_id"]
    status, cancelled = chat_api.post({"action": "cancel", "pending_id": pending_id})
    assert status == 200
    assert "cancelado" in cancelled["messages"][-1]["text"].casefold()
    assert len(chat_api.runtime.state()["store"]["06_Eventos"]) == committed_count


def test_chat_limits_total_session_attachment_memory(chat_api):
    chat_api.runtime.chat_attachment_bytes = 50_000_000
    status, response = chat_api.post(
        {
            "text": "anexo",
            "attachments": [
                {"filename": "foto.jpg", "mime_type": "image/jpeg", "data": "eA=="}
            ],
        }
    )
    assert status == 400
    assert "50 MB" in response["error"]


def test_chat_post_returns_only_new_turn_while_get_keeps_full_history(chat_api):
    _, first_turn = chat_api.post({"text": "primeira mensagem"})
    _, second_turn = chat_api.post({"text": "segunda mensagem"})
    _, full_history = chat_api.get()

    assert len(first_turn["messages"]) == 2
    assert len(second_turn["messages"]) == 2
    assert len(full_history["messages"]) == 4


def test_chat_bounds_text_length(chat_api):
    status, response = chat_api.post({"text": "x" * 10_001})

    assert status == 400
    assert "10000 caracteres" in response["error"]


def test_chat_bounds_session_history(chat_api):
    chat_api.runtime.chat_messages = [{}] * 199
    status, response = chat_api.post({"text": "mais uma"})

    assert status == 400
    assert "limite de 200 mensagens" in response["error"]
