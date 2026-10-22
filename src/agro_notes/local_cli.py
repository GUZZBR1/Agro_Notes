"""Offline JSON-lines CLI for exercising livestock event workflows."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .application import MVPProcessor
from .local_interpreter import JsonProposalInterpreter
from .local_store import LocalEventStore


@dataclass(frozen=True)
class LocalSettings:
    farm_property_id: str
    farm_timezone: str
    allowed_user_ids: frozenset[int]
    min_interpretation_confidence: float = 0.75
    interpretation_model: str = "explicit-json"
    transcription_model: str = "none"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Exercite o núcleo pecuário localmente, sem serviços externos.")
    parser.add_argument("--property-id", required=True, help="Identificador local da propriedade")
    parser.add_argument("--actor-id", required=True, type=int, help="Identificador local explícito do operador")
    parser.add_argument("--timezone", default="America/Sao_Paulo")
    return parser


def _json_value(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "filename") and hasattr(value, "content"):
        return {"filename": value.filename, "mime_type": value.mime_type, "size_bytes": len(value.content)}
    if isinstance(value, bytes):
        return {"size_bytes": len(value)}
    return value


async def _run_action(
    processor: MVPProcessor,
    store: LocalEventStore,
    actor_id: int,
    action: dict[str, Any],
    seq: int,
    *,
    source: str = "local-json",
):
    operation = action.get("action")
    if operation == "record":
        proposal = action.get("proposal")
        if not isinstance(proposal, dict):
            raise ValueError("record exige um objeto proposal JSON explícito")
        captured_at = str(action.get("captured_at") or datetime.now(UTC).isoformat())
        reply = await processor.receive(
            actor_id,
            json.dumps(proposal, ensure_ascii=False),
            source=source,
            message_id=str(action.get("message_id") or seq),
            captured_at=captured_at,
            device_timezone=None,
            source_reference=None,
        )
        return {"text": reply.text, "pending_id": reply.pending_id, "document": _json_value(reply.document)}
    if operation in {"confirm", "cancel"}:
        pending_id = action.get("pending_id")
        if not isinstance(pending_id, str) or not pending_id.startswith("LOCAL:"):
            raise ValueError(f"{operation} exige pending_id LOCAL")
        reply = await getattr(processor, operation)(actor_id, pending_id)
        return {"text": reply.text, "pending_id": reply.pending_id}
    if operation == "inspect":
        return {"store": store.snapshot()}
    raise ValueError("action deve ser record, confirm, cancel ou inspect")


async def _serve(args: argparse.Namespace) -> int:
    store = LocalEventStore()
    settings = LocalSettings(
        farm_property_id=args.property_id,
        farm_timezone=args.timezone,
        allowed_user_ids=frozenset({args.actor_id}),
    )
    processor = MVPProcessor(settings, store, JsonProposalInterpreter())
    for sequence, line in enumerate(sys.stdin, start=1):
        if not line.strip():
            continue
        try:
            action = json.loads(line)
            if not isinstance(action, dict):
                raise ValueError("cada linha precisa conter um objeto JSON")
            result = await _run_action(processor, store, args.actor_id, action, sequence)
            output = {"ok": True, **result}
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            output = {"ok": False, "error": str(exc)}
        print(json.dumps(output, ensure_ascii=False, default=str), flush=True)
    return 0


def main() -> None:
    args = build_parser().parse_args()
    raise SystemExit(asyncio.run(_serve(args)))


if __name__ == "__main__":
    main()
