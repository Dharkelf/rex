"""Build the feature DataFrame required by all backtest strategies."""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from src.collector.repository import DataRepository
from src.utils.config import load_config

logger = logging.getLogger(__name__)


def _load_close(symbol: str) -> pd.Series:
    repo = DataRepository(symbol)
    df = repo.load()
    if df.empty:
        logger.warning("No data for %s", symbol)
        return pd.Series(dtype=float, name=symbol)
    return df["close"].rename(symbol)


def build_backtest_features() -> pd.DataFrame:
    """
    Assemble all signals needed by S1–S4 strategies, aligned to ASWM.DE index.
    Returns a DataFrame with UTC DatetimeIndex.
    """
    cfg = load_config()
    lag_symbols: list[str] = cfg["backtest"]["s3_holdings_lag"]["lag_symbols"]

    # --- ASWM target ---
    aswm = _load_close(cfg["etf"]["ticker_xetra"]).rename("aswm_close")
    if aswm.empty:
        raise RuntimeError("No ASWM.DE data — run collector first.")

    # --- BTC ---
    btc = _load_close("BTC-USD")

    # --- Crypto-miner holdings composite ---
    holding_series = [_load_close(s) for s in lag_symbols]
    holding_series = [s for s in holding_series if not s.empty]

    # Align everything to ASWM index
    idx = aswm.index
    df = pd.DataFrame(index=idx)
    df["aswm_close"] = aswm

    # ASWM return — log-return for stationarity
    aswm_c = df["aswm_close"]
    df["aswm_return_1h"] = np.log(aswm_c / aswm_c.shift(1))

    # BTC features — log-returns
    btc_aligned = btc.reindex(idx, method="ffill")
    df["btc_return_1h"] = np.log(btc_aligned / btc_aligned.shift(1))
    df["btc_return_4h"] = np.log(btc_aligned / btc_aligned.shift(4))

    # Overnight BTC return: return from last XETRA close (16:30 UTC) to current bar
    df["btc_overnight_return"] = _overnight_return(btc_aligned, close_hour_utc=16)

    # Holdings composite: equal-weighted mean log-return of lag_symbols
    if holding_series:
        combined = pd.concat(holding_series, axis=1).reindex(idx, method="ffill")
        df["holdings_composite_1h"] = np.log(combined / combined.shift(1)).mean(axis=1)
    else:
        df["holdings_composite_1h"] = np.nan

    # Time features
    dti = pd.DatetimeIndex(idx)
    df["hour_of_day"] = dti.hour
    df["day_of_week"] = dti.dayofweek
    df["us_open_flag"] = ((dti.hour == 13) | (dti.hour == 14)).astype(int)

    df = df.dropna(subset=["aswm_close", "aswm_return_1h"])
    logger.info("Backtest feature matrix: %d rows, %d cols", len(df), len(df.columns))
    return df


def _overnight_return(series: pd.Series, close_hour_utc: int) -> pd.Series:
    """For each bar, compute return since the last close_hour bar."""
    result = pd.Series(index=series.index, dtype=float)
    last_close_price: float | None = None
    timestamps = pd.DatetimeIndex(series.index)

    for i, ts in enumerate(timestamps):
        price = float(series.iloc[i])
        if ts.hour == close_hour_utc:
            last_close_price = price
        if last_close_price is not None and ts.hour != close_hour_utc and last_close_price > 0:
            result.iloc[i] = np.log(price / last_close_price)
        else:
            result.iloc[i] = float("nan")

    return result
