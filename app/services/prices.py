"""yfinance price cache. Updates daily via APScheduler job.

Phase 01: implement sync_prices(tickers, db).
"""


def sync_prices(tickers: list[str], db) -> int:
    raise NotImplementedError("Price sync via yfinance — Phase 01")
