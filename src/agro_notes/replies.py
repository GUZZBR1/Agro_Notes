"""Transport-neutral result returned by the application core."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ActionReply:
    text: str
    pending_id: str | None = None
    remove_keyboard: bool = False
    document: Any | None = None
