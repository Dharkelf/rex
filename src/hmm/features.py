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

    # ASWM self
    df["aswm_return_1h"] = aswm_df["close"].pct_change()
    df["aswm_return_4h"] = aswm_df["close"].pct_change(4)
    df["aswm_log_return_1h"] = np.log1p(df["aswm_return_1h"])

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
        df[f"{safe}_return_1h"] = close.pct_change()
        df[f"{safe}_return_4h"] = close.pct_change(4)
        if sym == "^VIX":
            df["vix_level"] = close
            df["vix_change_1h"] = close.diff()

    # Holdings composite (crypto miners: MARA, IREN, MSTR)
    miner_cols = [c for c in df.columns if any(s in c for s in ["MARA", "IREN", "MSTR"]) and "return_1h" in c]
    if miner_cols:
        df["holdings_composite_1h"] = df[miner_cols].mean(axis=1)

    # Overnight BTC return
    btc_close = DataRepository("BTC-USD").load()
    if not btc_close.empty:
        btc_aligned = btc_close["close"].reindex(idx, method="ffill")
        df["btc_overnight_return"] = _overnight_return(btc_aligned, close_hour_utc=16)

    # Time features
    df["hour_of_day"] = idx.hour.astype(float)
    df["day_of_week"] = idx.dayofweek.astype(float)
    df["us_open_flag"] = ((idx.hour == 13) | (idx.hour == 14)).astype(float)

    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=["aswm_return_1h"])

    logger.info("Feature matrix: %d rows × %d cols", len(df), len(df.columns))
    return df


def _safe(symbol: str) -> str:
    return symbol.replace("^", "").replace("-", "_").replace(".", "_")


def _overnight_return(series: pd.Series, close_hour_utc: int) -> pd.Series:
    result = pd.Series(index=series.index, dtype=float)
    last_price: float | None = None
    for ts, price in series.items():
        if ts.hour == close_hour_utc:
            last_price = price
            result[ts] = float("nan")
        elif last_price is not None:
            result[ts] = (price - last_price) / last_price
        else:
            result[ts] = float("nan")
    return result
