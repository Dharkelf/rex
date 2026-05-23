"""XGBoost predictor with autoregressive lags, trained per regime."""

from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit

from src.utils.config import load_config
from src.utils.paths import processed_dir

if TYPE_CHECKING:
    from xgboost import XGBRegressor

logger = logging.getLogger(__name__)


class XGBPredictor:
    """
    Per-regime XGBoost model predicting ASWM.DE returns at multiple horizons.
    Uses autoregressive lags of ASWM plus all feature columns as inputs.
    """

    def __init__(self, regime: int | None = None) -> None:
        self.regime = regime
        self.cfg = load_config()["predictor"]
        self.models: dict[int, XGBRegressor] = {}  # horizon_h → model

    def fit(self, feature_matrix: pd.DataFrame, regimes: pd.Series | None = None) -> None:
        """Train one model per forecast horizon. Optionally filter by regime."""
        data = feature_matrix.copy()
        if regimes is not None and self.regime is not None:
            data = data[regimes == self.regime]
            if len(data) < 50:
                logger.warning(
                    "Regime %d has only %d rows — skipping XGB fit", self.regime, len(data)
                )
                return

        for horizon in self.cfg["target_horizons_h"]:
            X, y = self._build_dataset(data, horizon)
            if len(X) < 20:
                continue
            model = self._build_model()
            model.fit(X, y)
            self.models[horizon] = model
            logger.info("XGB fitted: regime=%s horizon=%dh rows=%d", self.regime, horizon, len(X))

        self._save()

    def predict(self, feature_matrix: pd.DataFrame, horizon_h: int = 3) -> float:
        """Predict return for the last row of feature_matrix."""
        if horizon_h not in self.models:
            raise RuntimeError(f"No model for horizon {horizon_h}h. Call fit() first.")
        X, _ = self._build_dataset(feature_matrix, horizon_h)
        if len(X) == 0:
            return float("nan")
        pred = self.models[horizon_h].predict(X[-1:])
        return float(pred[0])

    def predict_quantiles(
        self, feature_matrix: pd.DataFrame, horizon_h: int = 3, quantiles: tuple = (0.25, 0.75)
    ) -> tuple[float, float]:
        """Approximate quantiles from cross-val residuals on the training set."""
        if horizon_h not in self.models:
            return float("nan"), float("nan")
        X, y = self._build_dataset(feature_matrix, horizon_h)
        if len(X) < 10:
            return float("nan"), float("nan")
        preds = self.models[horizon_h].predict(X)
        residuals = y.values - preds
        center = self.predict(feature_matrix, horizon_h)
        q_low = center + float(np.quantile(residuals, quantiles[0]))
        q_high = center + float(np.quantile(residuals, quantiles[1]))
        return q_low, q_high

    def evaluate(self, feature_matrix: pd.DataFrame) -> dict[int, dict]:
        """Walk-forward evaluation. Returns per-horizon metrics."""
        cfg_bt = load_config()["backtest"]
        tscv = TimeSeriesSplit(n_splits=cfg_bt["n_splits"])
        results: dict[int, list] = {h: [] for h in self.cfg["target_horizons_h"]}

        for horizon in self.cfg["target_horizons_h"]:
            X_all, y_all = self._build_dataset(feature_matrix, horizon)
            if len(X_all) < 30:
                continue
            for train_idx, test_idx in tscv.split(X_all):
                m = self._build_model()
                m.fit(X_all[train_idx], y_all.iloc[train_idx])
                preds = m.predict(X_all[test_idx])
                actual = y_all.iloc[test_idx].values
                mae = float(np.mean(np.abs(actual - preds)))
                dir_acc = float(np.mean(np.sign(actual) == np.sign(preds)))
                results[horizon].append({"mae": mae, "dir_acc": dir_acc})

        return {
            h: {
                "mae": np.mean([r["mae"] for r in rows]),
                "dir_acc": np.mean([r["dir_acc"] for r in rows]),
            }
            for h, rows in results.items()
            if rows
        }

    # ------------------------------------------------------------------

    def _build_dataset(self, df: pd.DataFrame, horizon_h: int) -> tuple[np.ndarray, pd.Series]:
        lags = self.cfg["xgb"]["autoregressive_lags"]
        feature_cols = [c for c in df.columns if c != "aswm_close"]

        lag_frames = []
        for lag in lags:
            lagged = df[feature_cols].shift(lag)
            lagged.columns = pd.Index([f"{c}_lag{lag}" for c in feature_cols])
            lag_frames.append(lagged)

        X_df = pd.concat([df[feature_cols]] + lag_frames, axis=1)
        y = df["aswm_return_1h"].shift(-horizon_h)

        mask = y.notna() & X_df.notna().all(axis=1)
        return (
            X_df[mask].replace([np.inf, -np.inf], np.nan).fillna(0.0).values,
            y[mask],
        )

    def _build_model(self) -> XGBRegressor:
        from xgboost import XGBRegressor  # noqa: PLC0415 — lazy import (requires libomp)

        c = self.cfg["xgb"]
        return XGBRegressor(
            n_estimators=c["n_estimators"],
            max_depth=c["max_depth"],
            learning_rate=c["learning_rate"],
            subsample=c["subsample"],
            colsample_bytree=c["colsample_bytree"],
            random_state=c["random_state"],
            verbosity=0,
        )

    def _model_path(self) -> Path:
        suffix = f"_regime{self.regime}" if self.regime is not None else "_all"
        return processed_dir() / f"xgb{suffix}.pkl"

    def _save(self) -> None:
        with self._model_path().open("wb") as f:
            pickle.dump(self.models, f)

    def load(self) -> None:
        path = self._model_path()
        if not path.exists():
            raise FileNotFoundError(f"No saved XGB model at {path}")
        with path.open("rb") as f:
            self.models = pickle.load(f)
        logger.info("Loaded XGB model from %s", path)
