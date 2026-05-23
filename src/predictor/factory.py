"""Factory pattern — constructs XGBPredictor or NeuralProphetPredictor from config."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.predictor.np_predictor import NeuralProphetPredictor
    from src.predictor.xgb_predictor import XGBPredictor

logger = logging.getLogger(__name__)


class ModelFactory:
    """Returns configured predictor instances."""

    @staticmethod
    def xgb(regime: int | None = None) -> XGBPredictor:
        from src.predictor.xgb_predictor import XGBPredictor

        return XGBPredictor(regime=regime)

    @staticmethod
    def neural_prophet() -> NeuralProphetPredictor:
        from src.predictor.np_predictor import NeuralProphetPredictor

        return NeuralProphetPredictor()
