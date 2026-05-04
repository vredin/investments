"""IBKR Client Portal REST API adapter (httpx).
Also handles Flex Query CSV upload for full transaction history.

Phase 01: implement sync_ibkr_positions(db) and import_flex_csv(file, db).
"""


def sync_ibkr_positions(db) -> int:
    raise NotImplementedError("IBKR positions sync — Phase 01")


def import_flex_csv(file_content: bytes, db) -> int:
    raise NotImplementedError("IBKR Flex CSV import — Phase 01")
