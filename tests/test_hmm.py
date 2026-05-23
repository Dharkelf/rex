"""Unit tests for src/hmm/."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.hmm.detector import RegimeDetector


class TestRegimeDetector:
    def test_fit_predict_shape(self, feature_matrix):
        detector = RegimeDetector()
        # Override config for fast test
        detector.cfg = {
            "n_components": 3,
            "n_iter": 10,
            "random_state": 42,
            "covariance_type": "diag",
            "n_trials": 3,
            "optuna_seed": 1,
            "n_splits": 2,
            "feature_candidates": ["btc_return_1h", "BITQ_return_1h", "vix_level"],
        }
        detector.fit(feature_matrix)
        labels = detector.predict(feature_matrix)
        assert len(labels) == len(feature_matrix)
        assert set(labels.unique()).issubset({0, 1, 2})

    def test_regime_map_assigned_after_fit(self, feature_matrix):
        detector = RegimeDetector()
        detector.cfg = {
            "n_components": 3,
            "n_iter": 10,
            "random_state": 42,
            "covariance_type": "diag",
            "n_trials": 2,
            "optuna_seed": 1,
            "n_splits": 2,
            "feature_candidates": ["btc_return_1h", "vix_level"],
        }
        detector.fit(feature_matrix)
        assert set(detector._regime_map.values()) == {"Bull", "Neutral", "Bear"}

    def test_predict_proba_sums_to_one(self, feature_matrix):
        detector = RegimeDetector()
        detector.cfg = {
            "n_components": 3,
            "n_iter": 10,
            "random_state": 42,
            "covariance_type": "diag",
            "n_trials": 2,
            "optuna_seed": 1,
            "n_splits": 2,
            "feature_candidates": ["btc_return_1h", "vix_level"],
        }
        detector.fit(feature_matrix)
        probas = detector.predict_proba(feature_matrix)
        assert probas.shape[1] == 3
        np.testing.assert_allclose(probas.sum(axis=1), 1.0, atol=1e-6)

    def test_save_and_load(self, feature_matrix, tmp_path, monkeypatch):
        monkeypatch.setattr("src.hmm.detector.processed_dir", lambda: tmp_path)
        detector = RegimeDetector()
        detector.cfg = {
            "n_components": 3,
            "n_iter": 10,
            "random_state": 42,
            "covariance_type": "diag",
            "n_trials": 2,
            "optuna_seed": 1,
            "n_splits": 2,
            "feature_candidates": ["btc_return_1h", "vix_level"],
        }
        detector.fit(feature_matrix)

        detector2 = RegimeDetector()
        monkeypatch.setattr("src.hmm.detector.processed_dir", lambda: tmp_path)
        detector2.load()
        assert detector2.best_features == detector.best_features
