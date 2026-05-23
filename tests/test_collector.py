"""Unit tests for src/collector/."""

from __future__ import annotations

import pandas as pd
import pytest

from src.collector.repository import DataRepository
from src.collector.tradegate import tradegate_deviation


class TestDataRepository:
    def test_normalise_lowercase_columns(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.collector.repository.raw_parquet", lambda s: tmp_path / f"{s}.parquet")
        repo = DataRepository("TEST")
        df = pd.DataFrame(
            {"Open": [1.0], "High": [2.0], "Low": [0.5], "Close": [1.5], "Volume": [100.0]},
            index=pd.date_range("2025-01-01", periods=1, freq="h", tz="UTC"),
        )
        written = repo.append(df)
        assert written == 1
        stored = repo.load()
        assert list(stored.columns) == ["open", "high", "low", "close", "volume"]

    def test_append_deduplicates(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.collector.repository.raw_parquet", lambda s: tmp_path / f"{s}.parquet")
        repo = DataRepository("DUP")
        idx = pd.date_range("2025-01-01", periods=3, freq="h", tz="UTC")
        df = pd.DataFrame({"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 10.0}, index=idx)
        repo.append(df)
        written2 = repo.append(df)   # same data — should append 0 rows
        assert written2 == 0
        assert len(repo.load()) == 3

    def test_load_empty_returns_empty_df(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.collector.repository.raw_parquet", lambda s: tmp_path / "missing.parquet")
        repo = DataRepository("MISSING")
        df = repo.load()
        assert df.empty

    def test_latest_timestamp_none_when_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.collector.repository.raw_parquet", lambda s: tmp_path / "empty.parquet")
        repo = DataRepository("EMPTY")
        assert repo.latest_timestamp() is None


class TestTradegateDev:
    def test_positive_deviation(self):
        assert abs(tradegate_deviation(27.0, 26.0) - 1 / 26.0) < 1e-9

    def test_zero_xetra_close(self):
        assert tradegate_deviation(27.0, 0.0) == 0.0
