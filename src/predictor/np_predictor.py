"""NeuralProphet multivariate predictor for ASWM.DE hourly returns."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from src.utils.config import load_config
from src.utils.paths import processed_dir

logger = logging.getLogger(__name__)

_MODEL_FILE = "neuralprophet_model.pkl"


class NeuralProphetPredictor:
    """
    NeuralProphet wrapper with external regressors.
    Trains on ASWM.DE close prices with BTC, BITQ, SMH as regressors.
    """

    def __init__(self) -> None:
        self.cfg = load_config()["predictor"]["neuralprophet"]
        self.model = None
        self._regressors: list[str] = ["BTC_USD_return_1h", "BITQ_return_1h", "SMH_return_1h"]

    def fit(self, feature_matrix: pd.DataFrame) -> None:
        try:
            from neuralprophet import NeuralProphet  # noqa: PLC0415
        except ImportError:
            logger.warning("neuralprophet not installed — skipping NeuralProphet fit")
            return

        df_np = self._prepare_df(feature_matrix)
        if df_np is None or len(df_np) < 50:
            logger.warning("Insufficient data for NeuralProphet fit (%d rows)", len(df_np) if df_np is not None else 0)
            return

        cfg = self.cfg
        model = NeuralProphet(
            n_forecasts=cfg["n_forecasts"],
            n_lags=cfg["n_lags"],
            epochs=cfg["epochs"],
            batch_size=cfg["batch_size"],
            learning_rate=cfg["learning_rate"],
            seasonality_mode=cfg["seasonality_mode"],
            daily_seasonality=True,
            weekly_seasonality=True,
            yearly_seasonality=False,
            trainer_config={"accelerator": "cpu"},
        )
        for reg in self._regressors:
            if reg in df_np.columns:
                model.add_lagged_regressor(reg)

        model.fit(df_np, freq="h")
        self.model = model
        self._save()
        logger.info("NeuralProphet fitted on %d rows", len(df_np))

    def predict(self, feature_matrix: pd.DataFrame, horizon_h: int = 3) -> float:
        if self.model is None:
            raise RuntimeError("NeuralProphet model not fitted.")
        df_np = self._prepare_df(feature_matrix)
        if df_np is None or len(df_np) < self.cfg["n_lags"]:
            return float("nan")
        future = self.model.make_future_dataframe(df_np, n_historic_predictions=True)
        forecast = self.model.predict(future)
        col = f"yhat{min(horizon_h, self.cfg['n_forecasts'])}"
        if col not in forecast.columns:
            return float("nan")
        return float(forecast[col].iloc[-1])

    def _prepare_df(self, feature_matrix: pd.DataFrame) -> pd.DataFrame | None:
        if "aswm_close" not in feature_matrix.columns:
            return None
        df = pd.DataFrame()
        df["ds"] = feature_matrix.index.tz_localize(None) if feature_matrix.index.tz else feature_matrix.index
        df["y"] = feature_matrix["aswm_close"].values
        for reg in self._regressors:
            if reg in feature_matrix.columns:
                df[reg] = feature_matrix[reg].values
        return df.dropna(subset=["y"])

    def _save(self) -> None:
        if self.model is None:
            return
        path = processed_dir() / _MODEL_FILE
        try:
            self.model.save(str(path))
        except Exception as exc:
            logger.warning("Could not save NeuralProphet model: %s", exc)

    def load(self) -> None:
        try:
            from neuralprophet import NeuralProphet  # noqa: PLC0415
        except ImportError:
            logger.warning("neuralprophet not installed")
            return
        path = processed_dir() / _MODEL_FILE
        if not path.exists():
            raise FileNotFoundError(f"No saved NeuralProphet model at {path}")
        self.model = NeuralProphet.load(str(path))
        logger.info("Loaded NeuralProphet model from %s", path)
