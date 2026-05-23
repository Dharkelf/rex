"""Repository pattern — single access point for per-symbol 1h Parquet storage."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.utils.paths import raw_parquet

logger = logging.getLogger(__name__)

_SCHEMA_COLS = ["open", "high", "low", "close", "volume"]


class DataRepository:
    """Append-only Parquet store for one symbol at 1h resolution."""

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        self.path: Path = raw_parquet(symbol)

    def load(self) -> pd.DataFrame:
        """Return stored data sorted by timestamp index, duplicates removed."""
        if not self.path.exists():
            return pd.DataFrame(columns=_SCHEMA_COLS)
        df = pd.read_parquet(self.path)
        df = df[~df.index.duplicated(keep="last")]
        return df.sort_index()

    def latest_timestamp(self) -> pd.Timestamp | None:
        df = self.load()
        if df.empty:
            return None
        return df.index[-1]

    def append(self, df: pd.DataFrame) -> int:
        """Append new rows; skip rows already stored. Returns count written."""
        if df.empty:
            return 0

        df = self._normalise(df)
        existing = self.load()

        if not existing.empty:
            df = df[df.index > existing.index[-1]]

        if df.empty:
            logger.debug("%s: no new rows to append", self.symbol)
            return 0

        if self.path.exists():
            existing_table = pq.read_table(self.path)
            new_table = pa.Table.from_pandas(df, preserve_index=True)
            combined = pa.concat_tables([existing_table, new_table])
            pq.write_table(combined, self.path)
        else:
            table = pa.Table.from_pandas(df, preserve_index=True)
            pq.write_table(table, self.path)

        logger.info("%s: appended %d rows (up to %s)", self.symbol, len(df), df.index[-1])
        return len(df)

    @staticmethod
    def _normalise(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df.columns = pd.Index([str(c).lower() for c in df.columns])
        for col in _SCHEMA_COLS:
            if col not in df.columns:
                df[col] = float("nan")
        df = df[_SCHEMA_COLS]
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index, utc=True)
        elif df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        else:
            df.index = df.index.tz_convert("UTC")
        df.index.name = "timestamp"
        return df
