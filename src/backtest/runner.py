"""Run full backtest suite and print summary table."""

from __future__ import annotations

import logging

import pandas as pd

from src.backtest.engine import WalkForwardEvaluator
from src.backtest.features import build_backtest_features
from src.backtest.strategies import ALL_STRATEGIES
from src.utils.config import load_config
from src.utils.paths import processed_dir

logger = logging.getLogger(__name__)


def _load_bull_mask(data: pd.DataFrame) -> pd.Series | None:
    """Load pre-fitted HMM and return a boolean Series: True where Bull regime."""
    model_path = processed_dir() / "hmm_model_v1.pkl"
    if not model_path.exists():
        logger.warning("HMM model not found — running without regime filter")
        return None
    try:
        from src.hmm.detector import RegimeDetector
        from src.hmm.features import build_feature_matrix

        det = RegimeDetector()
        det.load()
        hmm_feat = build_feature_matrix()
        regimes = det.predict(hmm_feat)
        bull_state = next(k for k, v in det._regime_map.items() if v == "Bull")
        return (regimes == bull_state).reindex(data.index, fill_value=False)
    except Exception as exc:
        logger.warning("Failed to load HMM for regime filter: %s", exc)
        return None


def run_backtest() -> pd.DataFrame:
    """Run all strategies × positions × regime variants via walk-forward."""
    logger.info("Building backtest feature matrix …")
    data = build_backtest_features()

    cfg = load_config()
    fee = cfg["backtest"]["fee_per_side_eur"]

    bull_mask = _load_bull_mask(data)

    all_rows: list[dict] = []
    for StratCls in ALL_STRATEGIES:
        strat = StratCls()
        evaluator = WalkForwardEvaluator(strat)

        # Full dataset
        all_rows.extend(evaluator.evaluate(data, regime_mask=None))

        # Bull-only (if HMM available)
        if bull_mask is not None:
            all_rows.extend(evaluator.evaluate(data, regime_mask=bull_mask))

    summary = pd.DataFrame(all_rows)

    # Aggregate across folds
    group_cols = ["strategy", "regime_filtered", "hold_h", "position_eur"]
    agg = (
        summary.groupby(group_cols)
        .agg(
            folds=("fold", "count"),
            avg_trades=("n_trades", "mean"),
            avg_win_rate=("win_rate", "mean"),
            avg_pnl_eur=("avg_net_pnl_eur", "mean"),
            avg_winner_eur=("avg_winner_eur", "mean"),
            avg_loser_eur=("avg_loser_eur", "mean"),
            avg_sharpe=("sharpe", "mean"),
            avg_max_dd=("max_drawdown_eur", "mean"),
            break_even_pct=("break_even_pct", "first"),
        )
        .reset_index()
    )

    _print_summary(agg, fee)
    return agg


def _print_summary(df: pd.DataFrame, fee: float) -> None:
    logger.info("\n" + "=" * 80)
    logger.info("BACKTEST SUMMARY  (fee/side: €%.2f)  — hold_h × position", fee)
    logger.info("=" * 80)
    prev_key = None
    for _, row in df.iterrows():
        key = (row["strategy"], row["regime_filtered"])
        if key != prev_key:
            regime_label = "Bull only" if row["regime_filtered"] else "all bars"
            logger.info("--- %s  [%s] ---", row["strategy"], regime_label)
            prev_key = key
        logger.info(
            "  %2dh | €%-6.0f  trades=%.1f  win=%.0f%%  avg=€%+.2f"
            "  [W:€%+.2f / L:€%+.2f]  sharpe=%.2f  be=%.1f%%",
            row["hold_h"],
            row["position_eur"],
            row["avg_trades"],
            row["avg_win_rate"] * 100,
            row["avg_pnl_eur"],
            row["avg_winner_eur"],
            row["avg_loser_eur"],
            row["avg_sharpe"],
            row["break_even_pct"],
        )
    logger.info("=" * 80)
