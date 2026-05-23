"""Run full backtest suite and print summary table."""

from __future__ import annotations

import logging

import pandas as pd

from src.backtest.engine import WalkForwardEvaluator
from src.backtest.features import build_backtest_features
from src.backtest.strategies import ALL_STRATEGIES
from src.utils.config import load_config

logger = logging.getLogger(__name__)


def run_backtest() -> pd.DataFrame:
    """Run all strategies × all position sizes via walk-forward. Return summary DataFrame."""
    logger.info("Building backtest feature matrix …")
    data = build_backtest_features()

    cfg = load_config()
    fee = cfg["backtest"]["fee_per_side_eur"]

    all_rows: list[dict] = []
    for StratCls in ALL_STRATEGIES:
        strat = StratCls()
        evaluator = WalkForwardEvaluator(strat)
        rows = evaluator.evaluate(data)
        all_rows.extend(rows)

    summary = pd.DataFrame(all_rows)

    # Aggregate across folds — grouped by strategy × hold_h × position
    group_cols = ["strategy", "hold_h", "position_eur"]
    agg = (
        summary.groupby(group_cols)
        .agg(
            folds=("fold", "count"),
            avg_trades=("n_trades", "mean"),
            avg_win_rate=("win_rate", "mean"),
            avg_pnl_eur=("avg_net_pnl_eur", "mean"),
            avg_sharpe=("sharpe", "mean"),
            avg_max_dd=("max_drawdown_eur", "mean"),
            break_even_pct=("break_even_pct", "first"),
        )
        .reset_index()
    )

    _print_summary(agg, fee)
    return agg


def _print_summary(df: pd.DataFrame, fee: float) -> None:
    logger.info("\n" + "=" * 78)
    logger.info("BACKTEST SUMMARY  (fee/side: €%.2f)  — hold_h × position", fee)
    logger.info("=" * 78)
    prev_strat = None
    for _, row in df.iterrows():
        if row["strategy"] != prev_strat:
            logger.info("--- %s ---", row["strategy"])
            prev_strat = row["strategy"]
        logger.info(
            "  %2dh | €%-6.0f  trades=%.1f  win=%.0f%%  avg_pnl=€%+.2f"
            "  sharpe=%.2f  break-even=%.1f%%",
            row["hold_h"],
            row["position_eur"],
            row["avg_trades"],
            row["avg_win_rate"] * 100,
            row["avg_pnl_eur"],
            row["avg_sharpe"],
            row["break_even_pct"],
        )
    logger.info("=" * 78)
