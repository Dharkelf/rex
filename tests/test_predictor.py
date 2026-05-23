"""Unit tests for src/predictor/."""

from __future__ import annotations

import numpy as np
import pytest

from src.predictor.xgb_predictor import XGBPredictor


class TestXGBPredictor:
    def test_fit_and_predict(self, feature_matrix):
        pred = XGBPredictor(regime=None)
        pred.cfg = {
            "target_horizons_h": [1, 3],
            "target_symbol": "ASWM.DE",
            "xgb": {
                "n_estimators": 20,
                "max_depth": 3,
                "learning_rate": 0.1,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "random_state": 42,
                "autoregressive_lags": [1, 2],
            },
        }
        pred.fit(feature_matrix)
        assert 1 in pred.models
        assert 3 in pred.models
        result = pred.predict(feature_matrix, horizon_h=3)
        assert isinstance(result, float)

    def test_quantiles_ordered(self, feature_matrix):
        pred = XGBPredictor(regime=None)
        pred.cfg = {
            "target_horizons_h": [3],
            "target_symbol": "ASWM.DE",
            "xgb": {
                "n_estimators": 20,
                "max_depth": 3,
                "learning_rate": 0.1,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "random_state": 42,
                "autoregressive_lags": [1],
            },
        }
        pred.fit(feature_matrix)
        q25, q75 = pred.predict_quantiles(feature_matrix, horizon_h=3)
        assert q25 <= q75

    def test_save_and_load(self, feature_matrix, tmp_path, monkeypatch):
        monkeypatch.setattr("src.predictor.xgb_predictor.processed_dir", lambda: tmp_path)
        pred = XGBPredictor(regime=None)
        pred.cfg = {
            "target_horizons_h": [1],
            "target_symbol": "ASWM.DE",
            "xgb": {
                "n_estimators": 10,
                "max_depth": 2,
                "learning_rate": 0.1,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "random_state": 42,
                "autoregressive_lags": [1],
            },
        }
        pred.fit(feature_matrix)

        pred2 = XGBPredictor(regime=None)
        monkeypatch.setattr("src.predictor.xgb_predictor.processed_dir", lambda: tmp_path)
        pred2.load()
        assert 1 in pred2.models
