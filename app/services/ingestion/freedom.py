"""Freedom Finance TraderNet SDK adapter (tradernet Python package).
Auth: TraderNetAPI(public_key, private_key, login, passwd) from .env.

Phase 01: implement sync_freedom_positions(db) and sync_freedom_transactions(db).
"""


def sync_freedom_positions(db) -> int:
    raise NotImplementedError("Freedom Finance positions sync — Phase 01")


def sync_freedom_transactions(db) -> int:
    raise NotImplementedError("Freedom Finance transactions sync — Phase 01")
