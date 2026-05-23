"""Unit tests for src/signal/."""

from __future__ import annotations

import pytest

from src.signal.generator import SignalOutput


class TestSignalOutput:
    def _make_output(self, action: str = "KAUFE") -> SignalOutput:
        return SignalOutput(
            timestamp_cet="2026-05-23 09:15",
            regime="Bull",
            regime_confidence=0.78,
            action=action,
            hold_h=3,
            exit_time_cet="12:00",
            expected_return_p25=2.1,
            expected_return_p75=6.4,
            position_analyses=[
                {"position_eur": 500.0, "breakeven_pct": 4.0, "expected_pnl_eur": 9.0},
                {"position_eur": 1000.0, "breakeven_pct": 2.0, "expected_pnl_eur": 31.0},
            ],
            drivers=["BTC +2.3%", "MARA +3.1%"],
            tradegate_price=27.15,
            tradegate_deviation_pct=0.008,
            trigger_name="09:15 XETRA-Open Momentum",
        )

    def test_buy_signal_contains_kaufe(self):
        out = self._make_output("KAUFE")
        formatted = out.format()
        assert "KAUFE ASWM.DE" in formatted

    def test_no_signal_message(self):
        out = self._make_output("KEIN EINSTIEG")
        formatted = out.format()
        assert "KEIN EINSTIEG" in formatted

    def test_sensitivity_both_positions(self):
        out = self._make_output("KAUFE")
        formatted = out.format()
        assert "€500" in formatted
        assert "€1000" in formatted

    def test_tradegate_shown_when_present(self):
        out = self._make_output("KAUFE")
        formatted = out.format()
        assert "Tradegate" in formatted
        assert "27.1" in formatted

    def test_drivers_shown(self):
        out = self._make_output("KAUFE")
        formatted = out.format()
        assert "BTC" in formatted
        assert "MARA" in formatted
