"""yfinance-based 1h OHLCV fetcher with incremental append logic."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf

from src.collector.repository import DataRepository
from src.utils.config import load_config

logger = logging.getLogger(__name__)

_INTERVAL = "1h"
_LOOKBACK_PERIOD = "730d"   # yfinance max for 1h
_RETRY_DELAY_S = 5
_MAX_RETRIES = 3


def _fetch_yfinance(symbol: str, start: datetime | None) -> pd.DataFrame:
    """Download 1h bars from yfinance, returning a normalised DataFrame."""
    kwargs: dict = {"interval": _INTERVAL, "auto_adjust": True, "prepost": False}
    if start is not None:
        kwargs["start"] = start.strftime("%Y-%m-%d")
    else:
        kwargs["period"] = _LOOKBACK_PERIOD

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            df = yf.download(symbol, progress=False, **kwargs)
            if df.empty:
                logger.warning("%s: yfinance returned empty DataFrame (attempt %d)", symbol, attempt)
                return pd.DataFrame()
            # yfinance MultiIndex columns when single ticker — flatten
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0].lower() for c in df.columns]
            else:
                df.columns = [c.lower() for c in df.columns]
            return df
        except Exception as exc:
            logger.warning("%s: fetch error (attempt %d): %s", symbol, attempt, exc)
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_DELAY_S)
    return pd.DataFrame()


def collect_symbol(symbol: str) -> int:
    """Incrementally fetch and store 1h data for one symbol. Returns rows written."""
    repo = DataRepository(symbol)
    latest = repo.latest_timestamp()

    start: datetime | None = None
    if latest is not None:
        # fetch from 2h before latest to handle potential last-bar updates
        start = (latest - pd.Timedelta(hours=2)).to_pydatetime().replace(tzinfo=timezone.utc)

    logger.info("%s: fetching from %s", symbol, start or "max lookback")
    df = _fetch_yfinance(symbol, start)
    if df.empty:
        logger.warning("%s: nothing fetched", symbol)
        return 0

    return repo.append(df)


def collect_all() -> dict[str, int]:
    """Fetch all configured symbols. Returns {symbol: rows_written}."""
    cfg = load_config()
    symbols: list[str] = [cfg["etf"]["ticker_xetra"], cfg["etf"]["ticker_lse"]]
    symbols += cfg["features"]["symbols"]
    # deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for s in symbols:
        if s not in seen:
            seen.add(s)
            unique.append(s)

    results: dict[str, int] = {}
    for sym in unique:
        rows = collect_symbol(sym)
        results[sym] = rows
        time.sleep(0.5)   # be polite to yfinance

    total = sum(results.values())
    logger.info("Collection complete: %d symbols, %d new rows total", len(unique), total)
    return results
