"""Concrete BacktestStrategy implementations (S1–S4)."""

from __future__ import annotations

import pandas as pd

from src.backtest.engine import BacktestStrategy
from src.utils.config import load_config

# US market open in UTC (summer: 13:30, winter: 14:30)
_US_OPEN_UTC_SUMMER = 13
_US_OPEN_UTC_WINTER = 14
_XETRA_CLOSE_UTC = 16


class S1BtcLag(BacktestStrategy):
    """S1 — Enter ASWM when BTC 1h return exceeds threshold."""

    strategy_id = "S1_btc_lag"

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        cfg = load_config()["backtest"]["s1_btc_lag"]
        threshold: float = cfg["btc_return_threshold"]
        sig = data["btc_return_1h"] > threshold
        # Only enter during XETRA hours (08:00–16:00 UTC)
        hours = pd.DatetimeIndex(data.index).hour
        xetra_mask = (hours >= 8) & (hours < 16)
        return sig & xetra_mask

    def _hold_bars(self) -> int:
        return load_config()["backtest"]["s1_btc_lag"]["hold_bars"]


class S2OvernightGap(BacktestStrategy):
    """S2 — Enter at XETRA open when BTC moved significantly overnight."""

    strategy_id = "S2_overnight_gap"

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        cfg = load_config()["backtest"]["s2_overnight_gap"]
        threshold: float = cfg["btc_overnight_threshold"]
        # Only trigger on the first XETRA bar (09:00 CET = 07:00 UTC summer / 08:00 winter)
        # Use hour == 8 UTC as proxy for XETRA open bar
        open_bar = pd.DatetimeIndex(data.index).hour == 8
        strong_overnight = data["btc_overnight_return"].abs() > threshold
        return pd.Series(open_bar & strong_overnight, index=data.index)

    def _hold_bars(self) -> int:
        return load_config()["backtest"]["s2_overnight_gap"]["hold_bars"]


class S3HoldingsLag(BacktestStrategy):
    """S3 — Enter when crypto-miner holdings spike but ASWM hasn't moved yet."""

    strategy_id = "S3_holdings_lag"

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        cfg = load_config()["backtest"]["s3_holdings_lag"]
        hold_threshold: float = cfg["holdings_return_threshold"]
        aswm_max: float = cfg["aswm_max_move"]

        holdings_strong = data["holdings_composite_1h"] > hold_threshold
        aswm_quiet = data["aswm_return_1h"].abs() < aswm_max
        # Only during XETRA hours
        hours = pd.DatetimeIndex(data.index).hour
        xetra_mask = (hours >= 8) & (hours < 16)
        return holdings_strong & aswm_quiet & xetra_mask

    def _hold_bars(self) -> int:
        return load_config()["backtest"]["s3_holdings_lag"]["hold_bars"]


class S4UsOpenLag(BacktestStrategy):
    """S4 — Enter at US open (15:30 CET) when holdings open strongly but ASWM lags."""

    strategy_id = "S4_us_open_lag"

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        cfg = load_config()["backtest"]["s4_us_open_lag"]
        threshold: float = cfg["holdings_open_threshold"]
        aswm_max: float = cfg["aswm_max_move"]

        # US open bar: 13:30–14:30 UTC (summer) — use hour == 13 as proxy
        dti = pd.DatetimeIndex(data.index)
        us_open_bar = (dti.hour == 13) | (dti.hour == 14)
        holdings_strong = data["holdings_composite_1h"] > threshold
        aswm_quiet = data["aswm_return_1h"].abs() < aswm_max
        return pd.Series(us_open_bar & holdings_strong & aswm_quiet, index=data.index)

    def _hold_bars(self) -> int:
        return load_config()["backtest"]["s4_us_open_lag"]["hold_bars"]


class S5MeanReversion(BacktestStrategy):
    """S5 — Mean-reversion after oversold drop; VIX + own-vol filter (Kriegsindikator).

    Entry: ASWM is >drawdown_threshold% below its 24h rolling high,
    AND VIX < vix_max (not in panic), AND realized_vol_24h < vol_max.
    """

    strategy_id = "S5_mean_reversion"

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        cfg = load_config()["backtest"]["s5_mean_reversion"]
        dd_thresh: float = cfg["drawdown_threshold"]  # negative, e.g. -0.02
        vix_max: float = cfg["vix_max"]
        vol_max: float = cfg["vol_max"]

        oversold = data["aswm_drawdown_24h"] < dd_thresh
        calm_market = data["vix_level"].fillna(0) < vix_max
        low_vol = data["aswm_realized_vol_24h"].fillna(1) < vol_max
        # Only during XETRA hours
        hours = pd.DatetimeIndex(data.index).hour
        xetra_mask = (hours >= 8) & (hours < 16)
        return pd.Series(oversold & calm_market & low_vol & xetra_mask, index=data.index)

    def _hold_bars(self) -> int:
        return load_config()["backtest"]["s5_mean_reversion"]["hold_bars"]


ALL_STRATEGIES: list[type[BacktestStrategy]] = [
    S1BtcLag,
    S2OvernightGap,
    S3HoldingsLag,
    S4UsOpenLag,
    S5MeanReversion,
]
