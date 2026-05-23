"""Feature engineering for HMM regime detection."""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from src.collector.repository import DataRepository
from src.utils.config import load_config

logger = logging.getLogger(__name__)


def build_feature_matrix() -> pd.DataFrame:
    """
    Build aligned 1h feature matrix from raw Parquet files.
    Index: UTC DatetimeIndex matching ASWM.DE trading hours.
    """
    cfg = load_config()
    aswm_ticker = cfg["etf"]["ticker_xetra"]

    # Load ASWM as the alignment index
    aswm_repo = DataRepository(aswm_ticker)
    aswm_df = aswm_repo.load()
    if aswm_df.empty:
        raise RuntimeError("No ASWM.DE data — run collector first.")

    idx = aswm_df.index
    df = pd.DataFrame(index=idx)

    # ASWM self — log-returns for stationarity
    aswm_c = aswm_df["close"]
    df["aswm_return_1h"] = np.log(aswm_c / aswm_c.shift(1))
    df["aswm_return_4h"] = np.log(aswm_c / aswm_c.shift(4))

    # Load and align each feature symbol
    for sym in cfg["features"]["symbols"]:
        repo = DataRepository(sym)
        raw = repo.load()
        if raw.empty:
            logger.warning("Feature %s missing — filled with NaN", sym)
            df[f"{_safe(sym)}_close"] = np.nan
            continue
        close = raw["close"].reindex(idx, method="ffill")
        safe = _safe(sym)
        df[f"{safe}_return_1h"] = np.log(close / close.shift(1))
        df[f"{safe}_return_4h"] = np.log(close / close.shift(4))
        if sym == "^VIX":
            df["vix_level"] = close
            df["vix_change_1h"] = close.diff()

    # Weight-adjusted holdings composite (all 10 fund holdings × actual fund weights)
    weights: dict[str, float] = {h["symbol"]: float(h["weight"]) for h in cfg["holdings"]}
    weight_sum = sum(weights.values())
    holding_cols = []
    for sym, w in weights.items():
        col = f"{_safe(sym)}_return_1h"
        if col in df.columns:
            holding_cols.append((col, w / weight_sum))
    if holding_cols:
        df["holdings_composite_1h"] = sum(df[col] * w for col, w in holding_cols)
        # ETF-lag: how much holdings moved vs ASWM in the same bar (positive = ASWM lagging)
        df["holdings_etf_lag_1h"] = df["holdings_composite_1h"] - df["aswm_return_1h"]

    df["aswm_close"] = aswm_c

    # Overnight BTC return
    btc_close = DataRepository("BTC-USD").load()
    if not btc_close.empty:
        btc_aligned = btc_close["close"].reindex(idx, method="ffill")
        df["btc_overnight_return"] = _overnight_return(btc_aligned, close_hour_utc=16)

    # Time features
    dti = pd.DatetimeIndex(idx)
    df["hour_of_day"] = dti.hour.astype(float)
    df["day_of_week"] = dti.dayofweek.astype(float)
    df["us_open_flag"] = ((dti.hour == 13) | (dti.hour == 14)).astype(float)

    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=["aswm_return_1h"])

    logger.info("Feature matrix: %d rows × %d cols", len(df), len(df.columns))
    return df


def _safe(symbol: str) -> str:
    return symbol.replace("^", "").replace("-", "_").replace(".", "_")


def _overnight_return(series: pd.Series, close_hour_utc: int) -> pd.Series:
    result = pd.Series(index=series.index, dtype=float)
    last_price: float | None = None
    timestamps = pd.DatetimeIndex(series.index)
    for i, ts in enumerate(timestamps):
        price = float(series.iloc[i])
        if ts.hour == close_hour_utc:
            last_price = price
            result.iloc[i] = float("nan")
        elif last_price is not None and last_price > 0:
            result.iloc[i] = np.log(price / last_price)
        else:
            result.iloc[i] = float("nan")
    return result
