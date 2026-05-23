# REPORT.md — Observed Runtime Behaviour

This file documents **actual observed results** when the pipeline is run.
Updated alongside every essential code change that affects data flow, features, or model output.

---

## Data Collection

_Not yet run. Update after first `python main.py --collect`._

| Symbol | Rows | Date range | File size | Gaps observed |
|---|---|---|---|---|
| ASWM.DE | — | — | — | — |
| BTC-USD | — | — | — | — |
| … | | | | |

---

## Feature Matrix

_Not yet run. Update after first `python main.py --fit-hmm`._

| Metric | Value |
|---|---|
| Shape | — |
| NaN rate (max) | — |
| NaN rate (mean) | — |
| Date range | — |

---

## Backtest Results

_Not yet run. Update after first `python main.py --backtest`._

### S1 — BTC-Lag

| Metric | €500 | €1000 |
|---|---|---|
| Trades | — | — |
| Win rate | — | — |
| Avg return | — | — |
| Sharpe | — | — |
| Max drawdown | — | — |
| Ø P&L per trade | — | — |

### S2 — Overnight-Gap

_(same table)_

### S3 — Holdings-Lag

_(same table)_

### S4 — US-Open Lag

_(same table)_

---

## HMM Regime Model

_Not yet run._

| Metric | Value |
|---|---|
| n_components | — |
| Log-likelihood | — |
| BIC | — |
| Regime 0 frequency | — |
| Regime 1 frequency | — |
| Regime 2 frequency | — |
| Best feature subset (Optuna) | — |
| Best CV score | — |

---

## Predictor

_Not yet run._

| Model | Horizon | MAE | RMSE | Dir. accuracy |
|---|---|---|---|---|
| XGB (Bull) | 1h | — | — | — |
| XGB (Neutral) | 1h | — | — | — |
| XGB (Bear) | 1h | — | — | — |
| NeuralProphet | 1h | — | — | — |

---

## Known Issues

_None observed yet._
