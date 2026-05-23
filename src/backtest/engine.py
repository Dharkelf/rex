"""Strategy pattern — ABC + walk-forward engine for backtesting ASWM.DE signals."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit

from src.utils.config import load_config

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    entry_ts: pd.Timestamp
    exit_ts: pd.Timestamp
    entry_price: float
    exit_price: float
    position_eur: float
    fee_per_side_eur: float

    @property
    def gross_return(self) -> float:
        return (self.exit_price - self.entry_price) / self.entry_price

    @property
    def gross_pnl_eur(self) -> float:
        return self.position_eur * self.gross_return

    @property
    def net_pnl_eur(self) -> float:
        return self.gross_pnl_eur - 2 * self.fee_per_side_eur

    @property
    def net_return(self) -> float:
        return self.net_pnl_eur / self.position_eur


@dataclass
class BacktestResult:
    strategy_id: str
    position_eur: float
    trades: list[Trade] = field(default_factory=list)

    @property
    def n_trades(self) -> int:
        return len(self.trades)

    @property
    def win_rate(self) -> float:
        if not self.trades:
            return float("nan")
        return sum(1 for t in self.trades if t.net_pnl_eur > 0) / len(self.trades)

    @property
    def avg_net_pnl_eur(self) -> float:
        if not self.trades:
            return float("nan")
        return np.mean([t.net_pnl_eur for t in self.trades])

    @property
    def sharpe(self) -> float:
        if len(self.trades) < 2:
            return float("nan")
        rets = [t.net_return for t in self.trades]
        mu, sigma = np.mean(rets), np.std(rets, ddof=1)
        return mu / sigma if sigma > 0 else float("nan")

    @property
    def max_drawdown(self) -> float:
        if not self.trades:
            return float("nan")
        equity = np.cumsum([t.net_pnl_eur for t in self.trades])
        running_max = np.maximum.accumulate(equity)
        dd = equity - running_max
        return float(dd.min())

    @property
    def break_even_pct(self) -> float:
        if not self.trades:
            return float("nan")
        fee = self.trades[0].fee_per_side_eur
        return (2 * fee) / self.position_eur

    def summary(self) -> dict:
        return {
            "strategy": self.strategy_id,
            "position_eur": self.position_eur,
            "n_trades": self.n_trades,
            "win_rate": round(self.win_rate, 3),
            "avg_net_pnl_eur": round(self.avg_net_pnl_eur, 2),
            "sharpe": round(self.sharpe, 3),
            "max_drawdown_eur": round(self.max_drawdown, 2),
            "break_even_pct": round(self.break_even_pct * 100, 2),
        }


class BacktestStrategy(ABC):
    """Template Method — subclasses implement generate_signals()."""

    strategy_id: str = "base"

    def __init__(self, cfg: dict | None = None) -> None:
        self.cfg = cfg or load_config()

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Return a boolean Series aligned to data.index: True = enter long."""
        ...

    def run(self, data: pd.DataFrame, position_eur: float) -> BacktestResult:
        cfg = self.cfg
        fee = cfg["backtest"]["fee_per_side_eur"]
        result = BacktestResult(strategy_id=self.strategy_id, position_eur=position_eur)

        signals = self.generate_signals(data)
        hold_bars = self._hold_bars()
        aswm_close = data["aswm_close"]

        i = 0
        index = data.index.tolist()
        while i < len(index):
            ts = index[i]
            if signals.get(ts, False):
                entry_price = aswm_close.iloc[i]
                exit_i = min(i + hold_bars, len(index) - 1)
                exit_ts = index[exit_i]
                exit_price = aswm_close.iloc[exit_i]
                if entry_price > 0 and exit_price > 0:
                    result.trades.append(
                        Trade(
                            entry_ts=ts,
                            exit_ts=exit_ts,
                            entry_price=entry_price,
                            exit_price=exit_price,
                            position_eur=position_eur,
                            fee_per_side_eur=fee,
                        )
                    )
                i = exit_i + 1
            else:
                i += 1

        return result

    def _hold_bars(self) -> int:
        return 3


class WalkForwardEvaluator:
    """Run any BacktestStrategy with TimeSeriesSplit and aggregate results."""

    def __init__(self, strategy: BacktestStrategy) -> None:
        self.strategy = strategy

    def evaluate(self, data: pd.DataFrame) -> list[dict]:
        cfg = load_config()
        n_splits = cfg["backtest"]["n_splits"]
        position_sizes = cfg["backtest"]["position_sizes_eur"]

        tscv = TimeSeriesSplit(n_splits=n_splits)
        fold_results: list[dict] = []

        for fold, (train_idx, test_idx) in enumerate(tscv.split(data), start=1):
            test_data = data.iloc[test_idx]
            for pos in position_sizes:
                result = self.strategy.run(test_data, position_eur=pos)
                summary = result.summary()
                summary["fold"] = fold
                fold_results.append(summary)
                logger.info(
                    "Fold %d | %s | €%d: trades=%d win=%.0f%% avg_pnl=€%.2f sharpe=%.2f",
                    fold,
                    self.strategy.strategy_id,
                    pos,
                    result.n_trades,
                    result.win_rate * 100,
                    result.avg_net_pnl_eur,
                    result.sharpe,
                )

        return fold_results
