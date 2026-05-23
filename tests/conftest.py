"""Shared pytest fixtures for the REX test suite."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


def _make_ohlcv(n: int = 200, freq: str = "h", start: str = "2025-07-02") -> pd.DataFrame:
    idx = pd.date_range(start=start, periods=n, freq=freq, tz="UTC")
    rng = np.random.default_rng(42)
    close = 28.0 + np.cumsum(rng.normal(0, 0.3, n))
    return pd.DataFrame(
        {
            "open": close + rng.normal(0, 0.05, n),
            "high": close + np.abs(rng.normal(0, 0.1, n)),
            "low": close - np.abs(rng.normal(0, 0.1, n)),
            "close": close,
            "volume": rng.integers(1000, 50000, n).astype(float),
        },
        index=idx,
    )


@pytest.fixture
def aswm_ohlcv() -> pd.DataFrame:
    return _make_ohlcv(n=500)


@pytest.fixture
def btc_ohlcv() -> pd.DataFrame:
    rng = np.random.default_rng(7)
    idx = pd.date_range(start="2025-07-02", periods=500, freq="h", tz="UTC")
    close = 60000.0 + np.cumsum(rng.normal(0, 300, 500))
    return pd.DataFrame(
        {
            "open": close,
            "high": close + 100,
            "low": close - 100,
            "close": close,
            "volume": rng.integers(100, 5000, 500).astype(float),
        },
        index=idx,
    )


@pytest.fixture
def feature_matrix(aswm_ohlcv: pd.DataFrame, btc_ohlcv: pd.DataFrame) -> pd.DataFrame:
    idx = aswm_ohlcv.index
    rng = np.random.default_rng(99)
    df = pd.DataFrame(index=idx)
    df["aswm_close"] = aswm_ohlcv["close"]
    df["aswm_return_1h"] = df["aswm_close"].pct_change()
    btc_aligned = btc_ohlcv["close"].reindex(idx, method="ffill")
    df["btc_return_1h"] = btc_aligned.pct_change()
    df["btc_return_4h"] = btc_aligned.pct_change(4)
    df["btc_overnight_return"] = rng.normal(0, 0.01, len(idx))
    df["BITQ_return_1h"] = rng.normal(0, 0.015, len(idx))
    df["SMH_return_1h"] = rng.normal(0, 0.01, len(idx))
    df["QQQ_return_1h"] = rng.normal(0, 0.008, len(idx))
    df["vix_level"] = 20.0 + rng.normal(0, 3, len(idx))
    df["vix_change_1h"] = rng.normal(0, 0.5, len(idx))
    df["MARA_return_1h"] = rng.normal(0, 0.03, len(idx))
    df["IREN_return_1h"] = rng.normal(0, 0.03, len(idx))
    df["MSTR_return_1h"] = rng.normal(0, 0.025, len(idx))
    df["NVDA_return_1h"] = rng.normal(0, 0.015, len(idx))
    df["holdings_composite_1h"] = df[["MARA_return_1h", "IREN_return_1h", "MSTR_return_1h"]].mean(axis=1)
    df["hour_of_day"] = idx.hour.astype(float)
    df["day_of_week"] = idx.dayofweek.astype(float)
    df["us_open_flag"] = ((idx.hour == 13) | (idx.hour == 14)).astype(float)
    return df.dropna()
