"""GaussianHMM regime detector with Bayesian feature-subset optimisation via Optuna."""

from __future__ import annotations

import logging
import pickle
from pathlib import Path

import numpy as np
import optuna
import pandas as pd
from hmmlearn.hmm import GaussianHMM
from sklearn.model_selection import TimeSeriesSplit

from src.utils.config import load_config
from src.utils.paths import processed_dir

logger = logging.getLogger(__name__)
optuna.logging.set_verbosity(optuna.logging.WARNING)

_MODEL_PATH_TEMPLATE = "hmm_model_v{version}.pkl"


class RegimeDetector:
    """
    Gaussian HMM with 3 states (Bull=0 / Neutral=1 / Bear=2).
    Feature subset is selected via Optuna Bayesian optimisation.
    """

    def __init__(self) -> None:
        self.cfg = load_config()["hmm"]
        self.model: GaussianHMM | None = None
        self.best_features: list[str] = []
        self._regime_map: dict[int, str] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fit(self, feature_matrix: pd.DataFrame) -> None:
        """Optimise feature subset and fit final model on full data."""
        logger.info("Starting HMM feature optimisation (%d trials) …", self.cfg["n_trials"])
        self.best_features = self._optimise_features(feature_matrix)
        logger.info("Best features: %s", self.best_features)

        X = self._prepare_X(feature_matrix, self.best_features)
        model = self._build_model()
        model.fit(X)
        self.model = model

        # Label regimes by mean ASWM return in each state
        if "aswm_return_1h" in feature_matrix.columns:
            states = model.predict(X)
            means = {}
            for s in range(self.cfg["n_components"]):
                mask = states == s
                means[s] = feature_matrix["aswm_return_1h"].iloc[mask].mean() if mask.any() else 0.0
            sorted_states = sorted(means, key=lambda s: means[s])
            labels = {sorted_states[0]: "Bear", sorted_states[1]: "Neutral", sorted_states[2]: "Bull"}
            self._regime_map = labels
            logger.info("Regime map: %s", labels)

        self._save_model()

    def predict(self, feature_matrix: pd.DataFrame) -> pd.Series:
        """Return integer regime labels aligned to feature_matrix.index."""
        if self.model is None:
            raise RuntimeError("Model not fitted. Call fit() or load() first.")
        X = self._prepare_X(feature_matrix, self.best_features)
        states = self.model.predict(X)
        return pd.Series(states, index=feature_matrix.index, name="regime")

    def predict_proba(self, feature_matrix: pd.DataFrame) -> pd.DataFrame:
        """Return state posterior probabilities."""
        if self.model is None:
            raise RuntimeError("Model not fitted.")
        X = self._prepare_X(feature_matrix, self.best_features)
        posteriors = self.model.predict_proba(X)
        cols = [self._regime_map.get(i, str(i)) for i in range(self.cfg["n_components"])]
        return pd.DataFrame(posteriors, index=feature_matrix.index, columns=cols)

    def regime_name(self, state: int) -> str:
        return self._regime_map.get(state, str(state))

    def save(self) -> None:
        self._save_model()

    def load(self) -> None:
        path = self._model_path()
        if not path.exists():
            raise FileNotFoundError(f"No saved model at {path}")
        with path.open("rb") as f:
            data = pickle.load(f)
        self.model = data["model"]
        self.best_features = data["features"]
        self._regime_map = data["regime_map"]
        logger.info("Loaded HMM model from %s", path)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _optimise_features(self, feature_matrix: pd.DataFrame) -> list[str]:
        candidates = [c for c in self.cfg["feature_candidates"] if c in feature_matrix.columns]
        cfg = self.cfg

        def objective(trial: optuna.Trial) -> float:
            selected = [c for c in candidates if trial.suggest_categorical(c, [True, False])]
            if len(selected) < 2:
                return float("-inf")
            X_all = self._prepare_X(feature_matrix, selected)
            tscv = TimeSeriesSplit(n_splits=cfg["n_splits"])
            scores: list[float] = []
            for _, test_idx in tscv.split(X_all):
                X_test = X_all[test_idx]
                if len(X_test) < cfg["n_components"] * 2:
                    continue
                try:
                    m = self._build_model()
                    m.fit(X_all)   # train on all, score on held-out
                    ll = m.score(X_test)
                    scores.append(ll)
                except Exception:
                    scores.append(float("-inf"))
            return float(np.mean(scores)) if scores else float("-inf")

        sampler = optuna.samplers.TPESampler(seed=cfg["optuna_seed"])
        study = optuna.create_study(direction="maximize", sampler=sampler)
        study.optimize(objective, n_trials=cfg["n_trials"], show_progress_bar=False)

        best = study.best_params
        selected = [c for c in candidates if best.get(c, False)]
        # Fallback: if Optuna found no valid subset, use all candidates
        return selected if len(selected) >= 2 else candidates

    def _build_model(self) -> GaussianHMM:
        cfg = self.cfg
        return GaussianHMM(
            n_components=cfg["n_components"],
            covariance_type=cfg["covariance_type"],
            n_iter=cfg["n_iter"],
            random_state=cfg["random_state"],
        )

    @staticmethod
    def _prepare_X(feature_matrix: pd.DataFrame, features: list[str]) -> np.ndarray:
        sub = feature_matrix[features].copy()
        sub = sub.replace([np.inf, -np.inf], np.nan).ffill().fillna(0.0)
        return sub.values.astype(np.float64)

    def _model_path(self) -> Path:
        cfg = load_config()
        version = cfg["features"]["feature_schema_version"]
        return processed_dir() / _MODEL_PATH_TEMPLATE.format(version=version)

    def _save_model(self) -> None:
        path = self._model_path()
        with path.open("wb") as f:
            pickle.dump(
                {"model": self.model, "features": self.best_features, "regime_map": self._regime_map},
                f,
            )
        logger.info("Saved HMM model to %s", path)
