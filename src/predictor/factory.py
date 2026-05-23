"""Factory pattern — constructs XGBPredictor or NeuralProphetPredictor from config."""

from __future__ import annotations

import logging

from src.utils.config import load_config

logger = logging.getLogger(__name__)


class ModelFactory:
    """Returns configured predictor instances."""

    @staticmethod
    def xgb(regime: int | None = None) -> "XGBPredictor":
        from src.predictor.xgb_predictor import XGBPredictor
        return XGBPredictor(regime=regime)

    @staticmethod
    def neural_prophet() -> "NeuralProphetPredictor":
        from src.predictor.np_predictor import NeuralProphetPredictor
        return NeuralProphetPredictor()
