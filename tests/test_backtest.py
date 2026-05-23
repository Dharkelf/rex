"""Unit tests for src/backtest/."""

from __future__ import annotations

import pandas as pd
import pytest

from src.backtest.engine import BacktestResult, Trade, WalkForwardEvaluator
from src.backtest.strategies import S1BtcLag, S2OvernightGap, S3HoldingsLag, S4UsOpenLag


def _make_trade(entry: float = 27.0, exit_: float = 28.0, pos: float = 500.0) -> Trade:
    return Trade(
        entry_ts=pd.Timestamp("2025-07-02 09:00", tz="UTC"),
        exit_ts=pd.Timestamp("2025-07-02 12:00", tz="UTC"),
        entry_price=entry,
        exit_price=exit_,
        position_eur=pos,
        fee_per_side_eur=10.0,
    )


class TestTrade:
    def test_gross_return(self):
        t = _make_trade(27.0, 28.0)
        assert abs(t.gross_return - 1 / 27.0) < 1e-9

    def test_net_pnl_deducts_fees(self):
        t = _make_trade(27.0, 28.0, pos=500.0)
        assert abs(t.net_pnl_eur - (500 * (1 / 27.0) - 20)) < 1e-6

    def test_breakeven_at_zero_net(self):
        # net_pnl == 0 when gross_pnl == 2*fee
        fee = 10.0
        pos = 500.0
        required_exit = 27.0 * (1 + 2 * fee / pos)
        t = _make_trade(27.0, required_exit, pos=pos)
        assert abs(t.net_pnl_eur) < 1e-4


class TestBacktestResult:
    def test_win_rate(self):
        # exit=30 → gross_pnl ≈ €55.6 > €20 fees → net win
        # exit=26 → net loss
        result = BacktestResult("test", 500.0)
        result.trades = [_make_trade(27, 30), _make_trade(27, 26), _make_trade(27, 30)]
        assert abs(result.win_rate - 2 / 3) < 1e-9

    def test_empty_result(self):
        result = BacktestResult("test", 500.0)
        assert result.n_trades == 0
        assert pd.isna(result.win_rate)
        assert pd.isna(result.sharpe)

    def test_break_even_pct(self):
        result = BacktestResult("test", 500.0)
        result.trades = [_make_trade(27, 28, pos=500.0)]
        assert abs(result.break_even_pct - 0.04) < 1e-9


class TestStrategies:
    def test_s1_signals_only_during_xetra(self, feature_matrix):
        strat = S1BtcLag()
        sigs = strat.generate_signals(feature_matrix)
        # All signals should be during XETRA hours (hour 8–15 UTC)
        triggered = sigs[sigs]
        if len(triggered) > 0:
            assert triggered.index.hour.min() >= 8
            assert triggered.index.hour.max() <= 15

    def test_s4_signals_at_us_open(self, feature_matrix):
        strat = S4UsOpenLag()
        sigs = strat.generate_signals(feature_matrix)
        triggered = sigs[sigs]
        if len(triggered) > 0:
            assert all(h in (13, 14) for h in triggered.index.hour)

    def test_strategy_run_returns_result(self, feature_matrix):
        strat = S1BtcLag()
        result = strat.run(feature_matrix, position_eur=500.0)
        assert isinstance(result, BacktestResult)
        assert result.strategy_id == "S1_btc_lag"
