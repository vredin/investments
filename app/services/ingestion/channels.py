"""Telegram HTML export parser -> LLM sentiment -> channel_signals table.
IMPORTANT (DA-S01): channel signals are retrospective educational data only.
They must NOT be used as investment truth in recommendations.

Phase 01: implement ingest_channel_export(html_path, channel_name, db).
"""


def ingest_channel_export(_html_path: str, _channel_name: str, _db) -> int:
    raise NotImplementedError("Telegram channel HTML ingestion — Phase 01")
