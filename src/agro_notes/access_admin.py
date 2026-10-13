"""One-time administrative invitation creation and revocation commands."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta

from .access_control import AccessService, generate_invitation
from .settings import get_settings
from .sheets import GoogleSheetsStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Administrar convites privados do Agro Notes")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create-code")
    create.add_argument("--expires-in-hours", type=int, default=72)
    create.add_argument("--max-uses", type=int, default=1)
    revoke_code = commands.add_parser("revoke-code")
    revoke_code.add_argument("code_id")
    revoke_user = commands.add_parser("revoke-user")
    revoke_user.add_argument("telegram_user_id", type=int)
    args = parser.parse_args()

    settings = get_settings()
    if not settings.google_sheet_id:
        parser.error("GOOGLE_SHEET_ID ausente")
    store = GoogleSheetsStore.from_credentials(settings)
    store.bootstrap()
    access = AccessService(store, settings)
    if args.command == "create-code":
        if args.expires_in_hours < 1:
            parser.error("--expires-in-hours precisa ser positivo")
        code_id, code = generate_invitation(
            store,
            settings,
            expires_at=datetime.now(UTC) + timedelta(hours=args.expires_in_hours),
            max_uses=args.max_uses,
        )
        print("Código exibido uma única vez; compartilhe apenas em canal privado:")
        print(f"ID para revogação: {code_id}")
        print(code)
        print(f"Validade UTC: {(datetime.now(UTC) + timedelta(hours=args.expires_in_hours)).isoformat()}")
    elif args.command == "revoke-code":
        access.revoke_code(args.code_id)
        print("Convite revogado.")
    else:
        access.revoke_user(args.telegram_user_id)
        print("Acesso do usuário revogado.")


if __name__ == "__main__":
    main()
