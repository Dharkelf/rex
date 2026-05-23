"""
Template Method pattern — BaseSignalGenerator defines the trigger flow.
Concrete subclasses override _context_label() for each of the 4 triggers.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

import pandas as pd
import pytz

from src.collector.repository import DataRepository
from src.collector.tradegate import fetch_tradegate_quote, tradegate_deviation
from src.hmm.detector import RegimeDetector
from src.hmm.features import build_feature_matrix
from src.predictor.xgb_predictor import XGBPredictor
from src.utils.config import load_config
from src.utils.paths import signal_log_path

logger = logging.getLogger(__name__)
_CET = pytz.timezone("Europe/Vienna")


@dataclass
class SignalOutput:
    timestamp_cet: str
    regime: str
    regime_confidence: float
    action: str                   # "KAUFE" or "KEIN EINSTIEG"
    hold_h: int
    exit_time_cet: str
    expected_return_p25: float
    expected_return_p75: float
    position_analyses: list[dict]  # one per position size
    drivers: list[str]
    tradegate_price: float | None
    tradegate_deviation_pct: float | None
    trigger_name: str

    def format(self) -> str:
        now = self.timestamp_cet
        lines = [
            f"[{now}]  REGIME: {self.regime} (Konfidenz {self.regime_confidence:.0%})",
        ]

        if self.action == "KAUFE":
            lines += [
                f"Signal:    KAUFE ASWM.DE am Ask",
                f"Haltedauer: {self.hold_h}h  (Exit ~{self.exit_time_cet} CET)",
                "",
                "SENSITIVITÄT:",
            ]
            for pa in self.position_analyses:
                lines.append(
                    f"  €{pa['position_eur']:<5.0f} →  Break-even {pa['breakeven_pct']:+.1f}%  "
                    f"|  Erwartet {self.expected_return_p25:+.1f}% / {self.expected_return_p75:+.1f}% (p25/p75)"
                    f"  |  Ø P&L: {pa['expected_pnl_eur']:+.0f}€"
                )
        else:
            lines.append(f"KEIN EINSTIEG — Regime: {self.regime}")

        if self.drivers:
            lines.append("")
            lines.append("Treiber: " + " | ".join(self.drivers))

        if self.tradegate_price is not None and self.tradegate_deviation_pct is not None:
            dev = self.tradegate_deviation_pct * 100
            lines.append(
                f"Tradegate: €{self.tradegate_price:.4f} ({dev:+.1f}% vs. XETRA-Close)"
            )

        return "\n".join(lines)


class BaseSignalGenerator(ABC):
    """Skeleton: load data → detect regime → predict → format output."""

    @property
    @abstractmethod
    def trigger_name(self) -> str: ...

    @property
    @abstractmethod
    def default_hold_h(self) -> int: ...

    def run(self) -> SignalOutput:
        cfg = load_config()
        min_confidence: float = cfg["signal"]["min_confidence"]

        # 1. Update data
        feature_matrix = build_feature_matrix()
        if feature_matrix.empty:
            return self._no_signal("Keine Daten verfügbar")

        # 2. Regime
        detector = RegimeDetector()
        try:
            detector.load()
        except FileNotFoundError:
            return self._no_signal("HMM-Modell nicht trainiert")

        probas = detector.predict_proba(feature_matrix)
        current_state_int = int(detector.predict(feature_matrix).iloc[-1])
        regime_name = detector.regime_name(current_state_int)
        confidence = float(probas.iloc[-1].max())

        # 3. Predict
        predictor = XGBPredictor(regime=current_state_int)
        try:
            predictor.load()
        except FileNotFoundError:
            predictor = XGBPredictor()
            try:
                predictor.load()
            except FileNotFoundError:
                return self._no_signal("XGB-Modell nicht trainiert")

        hold_h = self.default_hold_h
        pred_return = predictor.predict(feature_matrix, horizon_h=hold_h)
        p25, p75 = predictor.predict_quantiles(feature_matrix, horizon_h=hold_h)

        # 4. Action decision
        fee = cfg["backtest"]["fee_per_side_eur"]
        position_sizes: list[float] = cfg["backtest"]["position_sizes_eur"]

        action = "KEIN EINSTIEG"
        if confidence >= min_confidence and regime_name == "Bull" and not pd.isna(pred_return):
            min_pos = min(position_sizes)
            breakeven = (2 * fee) / min_pos
            if pred_return > breakeven:
                action = "KAUFE"

        # 5. Position sensitivity
        position_analyses = []
        for pos in position_sizes:
            be_pct = (2 * fee) / pos
            exp_return = pred_return if not pd.isna(pred_return) else 0.0
            exp_pnl = pos * exp_return - 2 * fee
            position_analyses.append(
                {"position_eur": pos, "breakeven_pct": be_pct * 100, "expected_pnl_eur": exp_pnl}
            )

        # 6. Drivers
        drivers = self._compute_drivers(feature_matrix)

        # 7. Tradegate
        tg_price, tg_dev = self._tradegate_check(cfg)

        # 8. Exit time
        now_cet = datetime.now(_CET)
        exit_h = (now_cet.hour + hold_h) % 24
        exit_time = f"{exit_h:02d}:00"

        output = SignalOutput(
            timestamp_cet=now_cet.strftime("%Y-%m-%d %H:%M"),
            regime=regime_name,
            regime_confidence=confidence,
            action=action,
            hold_h=hold_h,
            exit_time_cet=exit_time,
            expected_return_p25=(p25 or 0.0) * 100,
            expected_return_p75=(p75 or 0.0) * 100,
            position_analyses=position_analyses,
            drivers=drivers,
            tradegate_price=tg_price,
            tradegate_deviation_pct=tg_dev,
            trigger_name=self.trigger_name,
        )

        self._log_signal(output)
        return output

    @staticmethod
    def _compute_drivers(feature_matrix: pd.DataFrame) -> list[str]:
        drivers = []
        last = feature_matrix.iloc[-1]
        checks = [
            ("btc_return_1h", "BTC"),
            ("MARA_return_1h", "MARA"),
            ("BITQ_return_1h", "BITQ"),
            ("SMH_return_1h", "SMH"),
            ("NVDA_return_1h", "NVDA"),
        ]
        for col, label in checks:
            if col in last.index and not pd.isna(last[col]):
                val = last[col] * 100
                if abs(val) >= 0.5:
                    drivers.append(f"{label} {val:+.1f}%")
        return drivers[:4]

    @staticmethod
    def _tradegate_check(cfg: dict) -> tuple[float | None, float | None]:
        threshold: float = cfg["etf"]["tradegate_deviation_threshold"]
        try:
            quote = fetch_tradegate_quote()
        except Exception:
            return None, None

        if quote.last is None:
            return None, None

        # Compare to last XETRA close
        repo = DataRepository(cfg["etf"]["ticker_xetra"])
        df = repo.load()
        if df.empty:
            return quote.last, None
        xetra_close = float(df["close"].iloc[-1])
        dev = tradegate_deviation(quote.last, xetra_close)
        if abs(dev) >= threshold:
            return quote.last, dev
        return None, None

    @staticmethod
    def _no_signal(reason: str) -> SignalOutput:
        logger.warning("No signal: %s", reason)
        now_cet = datetime.now(_CET).strftime("%Y-%m-%d %H:%M")
        return SignalOutput(
            timestamp_cet=now_cet,
            regime="UNBEKANNT",
            regime_confidence=0.0,
            action="KEIN EINSTIEG",
            hold_h=0,
            exit_time_cet="—",
            expected_return_p25=0.0,
            expected_return_p75=0.0,
            position_analyses=[],
            drivers=[reason],
            tradegate_price=None,
            tradegate_deviation_pct=None,
            trigger_name="—",
        )

    @staticmethod
    def _log_signal(output: SignalOutput) -> None:
        log_path = signal_log_path()
        formatted = output.format()
        separator = "-" * 60
        entry = f"\n{separator}\nTRIGGER: {output.trigger_name}\n{formatted}\n"
        with log_path.open("a", encoding="utf-8") as f:
            f.write(entry)
        # Also emit to logger for console
        for line in formatted.splitlines():
            logger.info(line)


# ---------------------------------------------------------------------------
# Concrete trigger subclasses
# ---------------------------------------------------------------------------

class OvernightGapSignal(BaseSignalGenerator):
    trigger_name = "08:45 Overnight-Gap"
    default_hold_h = 3


class XetraOpenSignal(BaseSignalGenerator):
    trigger_name = "09:15 XETRA-Open Momentum"
    default_hold_h = 3


class UsOpenLagSignal(BaseSignalGenerator):
    trigger_name = "15:35 US-Open Lag"
    default_hold_h = 2


class EveningSignal(BaseSignalGenerator):
    trigger_name = "17:00 Abend / Overnight"
    default_hold_h = 16


class SignalGenerator:
    """Facade: run any trigger by name, or on-demand."""

    _TRIGGERS: dict[str, type[BaseSignalGenerator]] = {
        "overnight": OvernightGapSignal,
        "xetra_open": XetraOpenSignal,
        "us_open": UsOpenLagSignal,
        "evening": EveningSignal,
    }

    def run(self, trigger: str = "xetra_open") -> SignalOutput:
        cls = self._TRIGGERS.get(trigger, XetraOpenSignal)
        return cls().run()

    def run_all(self) -> list[SignalOutput]:
        return [cls().run() for cls in self._TRIGGERS.values()]
