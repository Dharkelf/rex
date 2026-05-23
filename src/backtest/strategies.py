"""Concrete BacktestStrategy implementations (S1–S6) with time-window variants.

Class-level attributes `tw_start`, `tw_end`, `dow_filter`, `take_profit_pct` on
S3HoldingsLag and S4UsOpenLag allow subclasses to parameterise time windows and
exit behaviour without duplicating generate_signals logic.

dow_filter: (start_dow, end_dow) inclusive, 0=Mon … 4=Fri. None = all days.
"""

from __future__ import annotations

import pandas as pd

from src.backtest.engine import BacktestStrategy
from src.utils.config import load_config

_XETRA_OPEN_UTC = 8
_XETRA_CLOSE_UTC = 16


# ---------------------------------------------------------------------------
# S1 — BTC lag
# ---------------------------------------------------------------------------


class S1BtcLag(BacktestStrategy):
    """S1 — Enter ASWM when BTC 1h log-return exceeds threshold."""

    strategy_id = "S1_btc_lag"

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        cfg = load_config()["backtest"]["s1_btc_lag"]
        threshold: float = cfg["btc_return_threshold"]
        sig = data["btc_return_1h"] > threshold
        hours = pd.DatetimeIndex(data.index).hour
        xetra_mask = (hours >= _XETRA_OPEN_UTC) & (hours < _XETRA_CLOSE_UTC)
        return sig & xetra_mask

    def _hold_bars(self) -> int:
        return load_config()["backtest"]["s1_btc_lag"]["hold_bars"]


# ---------------------------------------------------------------------------
# S2 — Overnight gap
# ---------------------------------------------------------------------------


class S2OvernightGap(BacktestStrategy):
    """S2 — Enter at XETRA open when BTC moved significantly overnight."""

    strategy_id = "S2_overnight_gap"

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        cfg = load_config()["backtest"]["s2_overnight_gap"]
        threshold: float = cfg["btc_overnight_threshold"]
        open_bar = pd.DatetimeIndex(data.index).hour == 8
        strong_overnight = data["btc_overnight_return"].abs() > threshold
        return pd.Series(open_bar & strong_overnight, index=data.index)

    def _hold_bars(self) -> int:
        return load_config()["backtest"]["s2_overnight_gap"]["hold_bars"]


# ---------------------------------------------------------------------------
# S3 — Holdings lag (time-window variants)
# ---------------------------------------------------------------------------


class S3HoldingsLag(BacktestStrategy):
    """S3 base — holdings spike + ASWM actively falling + BTC confirms.

    Covered-call lag: MARA/IREN/MSTR move first; ASWM follows 1-2h later.
    ASWM condition: any negative return (>0.5% divergence in same bar is rare
    given covered-call overlay).
    """

    strategy_id = "S3_holdings_lag"
    tw_start: int = 13
    tw_end: int = 16
    dow_filter: tuple[int, int] | None = None

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        cfg = load_config()["backtest"]["s3_holdings_lag"]
        hold_threshold: float = cfg["holdings_return_threshold"]

        holdings_strong = data["holdings_composite_1h"] > hold_threshold
        aswm_falling = data["aswm_return_1h"] < 0
        btc_rising = data["btc_return_1h"] > 0

        dti = pd.DatetimeIndex(data.index)
        time_mask = (dti.hour >= self.tw_start) & (dti.hour <= self.tw_end)
        if self.dow_filter is not None:
            dow = dti.dayofweek
            dow_mask = (dow >= self.dow_filter[0]) & (dow <= self.dow_filter[1])
            time_mask = time_mask & dow_mask

        return pd.Series(holdings_strong & aswm_falling & btc_rising & time_mask, index=data.index)

    def _hold_bars(self) -> int:
        return load_config()["backtest"]["s3_holdings_lag"]["hold_bars"]


class S3EarlyXetra(S3HoldingsLag):
    """S3 — XETRA opening window 08-10 UTC (overnight gap carry)."""

    strategy_id = "S3_early_08_10"
    tw_start = 8
    tw_end = 10


class S3PreUsOpen(S3HoldingsLag):
    """S3 — European closing / pre-US open 11-13 UTC."""

    strategy_id = "S3_preusopen_11_13"
    tw_start = 11
    tw_end = 13


class S3UsOpen(S3HoldingsLag):
    """S3 — US open window 13-16 UTC."""

    strategy_id = "S3_usopen_13_16"
    tw_start = 13
    tw_end = 16


class S3MonWed(S3HoldingsLag):
    """S3 — Full XETRA session, Monday–Wednesday only."""

    strategy_id = "S3_mon_wed"
    tw_start = 8
    tw_end = 16
    dow_filter = (0, 2)


class S3ThuFri(S3HoldingsLag):
    """S3 — Full XETRA session, Thursday–Friday only."""

    strategy_id = "S3_thu_fri"
    tw_start = 8
    tw_end = 16
    dow_filter = (3, 4)


# ---------------------------------------------------------------------------
# S4 — US open lag (time-window variants + take-profit)
# ---------------------------------------------------------------------------


class S4UsOpenLag(BacktestStrategy):
    """S4 base — holdings strong during flexible window + ASWM lags (quiet).

    Subclasses override tw_start / tw_end / dow_filter / take_profit_pct.
    """

    strategy_id = "S4_us_open_lag"
    tw_start: int = 13  # original winning: US open proper (13:30 UTC summer)
    tw_end: int = 14  # 13-14 UTC → 88% win rate at 16h hold (5 trades total)
    dow_filter: tuple[int, int] | None = None
    take_profit_pct: float | None = None

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        cfg = load_config()["backtest"]["s4_us_open_lag"]
        threshold: float = cfg["holdings_open_threshold"]
        aswm_max: float = cfg["aswm_max_move"]

        dti = pd.DatetimeIndex(data.index)
        time_mask = (dti.hour >= self.tw_start) & (dti.hour <= self.tw_end)
        if self.dow_filter is not None:
            dow = dti.dayofweek
            dow_mask = (dow >= self.dow_filter[0]) & (dow <= self.dow_filter[1])
            time_mask = time_mask & dow_mask

        holdings_strong = data["holdings_composite_1h"] > threshold
        aswm_quiet = data["aswm_return_1h"].abs() < aswm_max
        return pd.Series(time_mask & holdings_strong & aswm_quiet, index=data.index)

    def _hold_bars(self) -> int:
        return load_config()["backtest"]["s4_us_open_lag"]["hold_bars"]


class S4MorningEu(S4UsOpenLag):
    """S4 — European XETRA morning 08-12 UTC."""

    strategy_id = "S4_morning_08_12"
    tw_start = 8
    tw_end = 12


class S4PreUsOpen(S4UsOpenLag):
    """S4 — Pre-US open 10-13 UTC (European close, pre-US momentum)."""

    strategy_id = "S4_preusopen_10_13"
    tw_start = 10
    tw_end = 13


class S4UsOpen(S4UsOpenLag):
    """S4 — Core US open window 13-16 UTC."""

    strategy_id = "S4_usopen_13_16"
    tw_start = 13
    tw_end = 16


class S4UsOpenTp(S4UsOpenLag):
    """S4 — US open 13-16 UTC with 1.5% take-profit (Verkauf im Plus)."""

    strategy_id = "S4_usopen_tp15"
    tw_start = 13
    tw_end = 16
    take_profit_pct = 0.015


class S4MonWed(S4UsOpenLag):
    """S4 — US open window 12-15 UTC, Monday–Wednesday only."""

    strategy_id = "S4_mon_wed_12_15"
    tw_start = 12
    tw_end = 15
    dow_filter = (0, 2)


class S4ThuFri(S4UsOpenLag):
    """S4 — US open window 12-15 UTC, Thursday–Friday only."""

    strategy_id = "S4_thu_fri_12_15"
    tw_start = 12
    tw_end = 15
    dow_filter = (3, 4)


# ---------------------------------------------------------------------------
# S5 — Mean reversion (VIX premium zone)
# ---------------------------------------------------------------------------


class S5MeanReversion(BacktestStrategy):
    """S5 — Mean-reversion after oversold drop; VIX premium zone + own-vol filter.

    Entry: ASWM >5% below 24h rolling high,
    VIX in vix_min..vix_max (optimal covered-call premium zone),
    AND realized_vol_24h < vol_max.

    vix_min: low VIX → covered-call premiums thin → skip.
    vix_max (Kriegsindikator): VIX >= 35 → panic, no bounce expected.
    """

    strategy_id = "S5_mean_reversion"

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        cfg = load_config()["backtest"]["s5_mean_reversion"]
        dd_thresh: float = cfg["drawdown_threshold"]
        vix_min: float = cfg.get("vix_min", 0.0)
        vix_max: float = cfg["vix_max"]
        vol_max: float = cfg["vol_max"]

        oversold = data["aswm_drawdown_24h"] < dd_thresh
        vix = data["vix_level"].fillna(0)
        vix_premium_zone = (vix >= vix_min) & (vix < vix_max)
        low_vol = data["aswm_realized_vol_24h"].fillna(1) < vol_max
        hours = pd.DatetimeIndex(data.index).hour
        xetra_mask = (hours >= _XETRA_OPEN_UTC) & (hours < _XETRA_CLOSE_UTC)
        return pd.Series(oversold & vix_premium_zone & low_vol & xetra_mask, index=data.index)

    def _hold_bars(self) -> int:
        return load_config()["backtest"]["s5_mean_reversion"]["hold_bars"]


# ---------------------------------------------------------------------------
# S6 — IV Premium Harvest
# ---------------------------------------------------------------------------


class S6IvPremiumHarvest(BacktestStrategy):
    """S6 — Enter after holdings pullback when VIX is in the premium harvest zone.

    Covered-call overlay re-writes calls at elevated IV after a correction →
    enhanced premium income → expected relative outperformance vs. uncovered.
    Take-profit at config take_profit_pct: bounce is capped by covered calls.

    Entry conditions:
    - holdings_composite_1h < holdings_pullback_threshold (e.g. -1.5%/h)
    - vix_min <= VIX <= vix_max (optimal: IV elevated, not panic)
    - XETRA trading hours
    """

    strategy_id = "S6_iv_premium_harvest"

    def __init__(self, cfg: dict | None = None) -> None:
        super().__init__(cfg)
        s6_cfg = self.cfg["backtest"]["s6_iv_premium_harvest"]
        raw_tp = s6_cfg.get("take_profit_pct")
        self.take_profit_pct: float | None = float(raw_tp) if raw_tp is not None else None

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        cfg = load_config()["backtest"]["s6_iv_premium_harvest"]
        pullback_thresh: float = cfg["holdings_pullback_threshold"]
        vix_min: float = cfg["vix_min"]
        vix_max: float = cfg["vix_max"]

        holdings_weak = data["holdings_composite_1h"] < pullback_thresh
        vix = data["vix_level"].fillna(0)
        vix_premium_zone = (vix >= vix_min) & (vix <= vix_max)
        hours = pd.DatetimeIndex(data.index).hour
        xetra_mask = (hours >= _XETRA_OPEN_UTC) & (hours < _XETRA_CLOSE_UTC)
        return pd.Series(holdings_weak & vix_premium_zone & xetra_mask, index=data.index)

    def _hold_bars(self) -> int:
        return load_config()["backtest"]["s6_iv_premium_harvest"]["hold_bars"]


# ---------------------------------------------------------------------------
# Strategy registry
# ---------------------------------------------------------------------------

ALL_STRATEGIES: list[type[BacktestStrategy]] = [
    S1BtcLag,
    S2OvernightGap,
    # S3 time-window experiments
    S3EarlyXetra,
    S3PreUsOpen,
    S3UsOpen,
    S3MonWed,
    S3ThuFri,
    # S4 time-window experiments (incl. take-profit variant)
    S4UsOpenLag,
    S4MorningEu,
    S4PreUsOpen,
    S4UsOpen,
    S4UsOpenTp,
    S4MonWed,
    S4ThuFri,
    # Mean reversion and IV harvest
    S5MeanReversion,
    S6IvPremiumHarvest,
]
