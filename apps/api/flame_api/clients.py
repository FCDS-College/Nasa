"""Per-client API keys (P2-1, ADR-009 step 2).

    python -m flame_api.clients create NAME --scopes read[,write][,admin] [--owner PERSON]
    python -m flame_api.clients list
    python -m flame_api.clients revoke NAME

`create` prints the key once; only its SHA-256 is stored. To rotate, create a second client
(e.g. `web-2026-11`), deploy its key, then revoke the old one. There is no HTTP endpoint for this
on purpose: issuing credentials needs database access, not a credential.

Scopes are independent; none implies another. `read` covers GET/HEAD and `POST /api/chat`, `write`
every other method outside `/api/admin/`, and `admin` every `/api/admin/` route (reads included).
An `admin` key must name the person who holds it (`--owner`): admin actions are audited under the
client name, and since names are never reused, each audited name maps to one person for good.
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import re
import secrets
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from hmac import compare_digest
from threading import Lock

from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from flame_api.ids import new_ulid
from flame_api.models import ApiClient

logger = logging.getLogger("flame_api.clients")

KEY_PREFIX = "flk_"
SCOPES = ("read", "write", "admin")
# Lower-case, so a name is safe in log lines and in Redis keys. `legacy-*` and `anonymous` are the
# identities the API gives the deprecated env tokens and unauthenticated deployments.
NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
RESERVED_NAMES = re.compile(r"^(legacy-.*|anonymous)$")
# A person's name or e-mail, as the operator writes it: printable, one line, at most 128 characters.
OWNER_PATTERN = re.compile(r"^[^\x00-\x1f\x7f]{1,128}$")
# last_used_at is a hint for operators, not an audit trail: write it at most once a minute per client.
TOUCH_INTERVAL_S = 60.0

_touched: dict[str, float] = {}
_touched_lock = Lock()


class ClientError(ValueError):
    pass


@dataclass(frozen=True)
class Authenticated:
    name: str
    scopes: tuple[str, ...]
    owner: str | None = None


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def looks_like_client_key(token: str) -> bool:
    return token.startswith(KEY_PREFIX)


def create_client(session: Session, name: str, scopes: list[str], owner: str | None = None) -> tuple[ApiClient, str]:
    """Insert a client and return it with its key. The key is not recoverable afterwards."""
    if not NAME_PATTERN.fullmatch(name) or RESERVED_NAMES.fullmatch(name):
        raise ClientError("Client names are 1-64 of a-z 0-9 . _ -, and may not be `anonymous` or start with `legacy-`.")
    wanted = sorted(set(scopes))
    if not wanted or any(scope not in SCOPES for scope in wanted):
        raise ClientError(f"Scopes must be a non-empty subset of {', '.join(SCOPES)}.")
    owner = owner.strip() if owner is not None else None
    if owner is not None and not OWNER_PATTERN.fullmatch(owner):
        raise ClientError("An owner is 1-128 printable characters on one line.")
    if "admin" in wanted and not owner:
        raise ClientError("An admin key needs --owner: the person accountable for its audited actions.")
    if session.scalar(select(ApiClient.client_id).where(ApiClient.name == name)) is not None:
        raise ClientError(f"A client named {name!r} already exists (revoked names are not reused).")
    key = KEY_PREFIX + secrets.token_urlsafe(32)
    record = ApiClient(
        client_id=new_ulid(), name=name, key_hash=hash_key(key), scopes=wanted, owner=owner or None,
        created_at=datetime.now(UTC),
    )
    session.add(record)
    session.commit()
    return record, key


def list_clients(session: Session) -> list[ApiClient]:
    return list(session.scalars(select(ApiClient).order_by(ApiClient.name)))


def revoke_client(session: Session, name: str) -> ApiClient:
    record = session.scalar(select(ApiClient).where(ApiClient.name == name))
    if record is None:
        raise ClientError(f"No client named {name!r}.")
    if record.revoked_at is None:
        record.revoked_at = datetime.now(UTC)
        session.commit()
    return record


def authenticate(session: Session, key: str) -> Authenticated | None:
    """The unrevoked client this key belongs to, or None. Scope checks are the caller's.

    The lookup is by hash, so the stored value is never compared against the raw key; the final
    hash comparison is constant-time anyway.
    """
    digest = hash_key(key)
    record = session.scalar(select(ApiClient).where(ApiClient.key_hash == digest))
    if record is None or record.revoked_at is not None or not compare_digest(record.key_hash, digest):
        return None
    _touch(session, record.client_id)
    return Authenticated(name=record.name, scopes=tuple(record.scopes or ()), owner=record.owner)


def _touch(session: Session, client_id: str) -> None:
    now = time.monotonic()
    with _touched_lock:
        last = _touched.get(client_id)
        if last is not None and now - last < TOUCH_INTERVAL_S:
            return
        _touched[client_id] = now
    try:
        session.execute(update(ApiClient).where(ApiClient.client_id == client_id).values(last_used_at=datetime.now(UTC)))
        session.commit()
    except SQLAlchemyError:
        # A failed hint must not fail the request; the next interval tries again.
        session.rollback()
        logger.warning("api_client_touch_failed client_id=%s", client_id)


def reset() -> None:
    with _touched_lock:
        _touched.clear()


def _iso(value: datetime | None) -> str:
    return value.isoformat().replace("+00:00", "Z") if value else "-"


def main(argv: list[str]) -> int:
    from flame_api.database import SessionLocal

    parser = argparse.ArgumentParser(prog="python -m flame_api.clients", description="Manage Flame API client keys.")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create", help="create a client and print its key once")
    create.add_argument("name")
    create.add_argument("--scopes", default="read", help="comma-separated: read, write, admin (default: read)")
    create.add_argument("--owner", default=None, help="the person who holds the key (required with admin)")
    commands.add_parser("list", help="list clients (never their keys)")
    revoke = commands.add_parser("revoke", help="revoke a client's key immediately")
    revoke.add_argument("name")
    args = parser.parse_args(argv)

    with SessionLocal() as session:
        try:
            if args.command == "create":
                record, key = create_client(session, args.name, [s.strip() for s in args.scopes.split(",") if s.strip()],
                                            owner=args.owner)
                held = f", held by {record.owner}" if record.owner else ""
                print(f"Created client {record.name} ({record.client_id}) with scopes {','.join(record.scopes)}{held}.")
                print("Key (shown once; store it in the caller's secret store):")
                print(key)
            elif args.command == "list":
                print("name\tclient_id\tscopes\towner\tcreated_at\tlast_used_at\trevoked_at")
                for record in list_clients(session):
                    print("\t".join([record.name, record.client_id, ",".join(record.scopes), record.owner or "-",
                                     _iso(record.created_at),
                                     _iso(record.last_used_at), _iso(record.revoked_at)]))
            else:
                record = revoke_client(session, args.name)
                print(f"Revoked client {record.name} at {_iso(record.revoked_at)}.")
        except ClientError as error:
            print(f"error: {error}", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
