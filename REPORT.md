# REPORT.md — Observed Runtime Behaviour

This file documents **actual observed results** when the pipeline is run.
Updated alongside every essential code change that affects data flow, features, or model output.

---

## Data Collection

Run: 2026-05-23. All 19 symbols fetched successfully via yfinance 1h.

| Symbol | Rows | Date range | File size |
|---|---|---|---|
| ASWM.DE | 1 444 | 2025-07-02 → 2026-05-22 | 46 KB |
| CEGI.L | 1 199 | 2025-07-09 → 2026-05-22 | 42 KB |
| BTC-USD | 17 339 | 2 years | 705 KB |
| ETH-USD | 17 339 | 2 years | 711 KB |
| BITQ/SMH/QQQ/IPAY | ~5 078 | 2 years | ~175–215 KB |
| ^VIX | 9 967 | 2 years | 173 KB |
| Holdings (10×) | ~5 078 | 2 years | ~175–217 KB |

Total: 118 157 rows across 19 symbols.

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

Run: 2026-05-23. Walk-forward, 3 folds, ~1 443 hourly bars.
Default thresholds from settings.yaml (not yet optimised).

| Strategy | Position | Trades/fold | Win rate | Ø P&L | Sharpe | Max DD | Break-even |
|---|---|---|---|---|---|---|---|
| S1 BTC-Lag | €500 | 12.7 | 3% | €-17.72 | -2.42 | €-206 | 4.0% |
| S1 BTC-Lag | €1000 | 12.7 | 22% | €-15.43 | -1.06 | €-179 | 2.0% |
| S2 Overnight-Gap | €500 | 23.0 | 0% | €-20.23 | -3.60 | €-443 | 4.0% |
| S2 Overnight-Gap | €1000 | 23.0 | 7% | €-20.47 | -1.82 | €-447 | 2.0% |
| S3 Holdings-Lag | €500 | 4.3 | 8% | €-16.38 | -2.08 | €-59 | 4.0% |
| S3 Holdings-Lag | €1000 | 4.3 | 28% | €-12.76 | -0.83 | €-54 | 2.0% |
| S4 US-Open Lag | €500 | 1.7 | 0% | €-15.29 | -1.44 | €-19 | 4.0% |
| S4 US-Open Lag | €1000 | 1.7 | 25% | €-10.58 | -0.51 | €-15 | 2.0% |

**Interpretation:**
- Alle Strategien mit Default-Schwellen unprofitabel nach Transaktionskosten.
- S3 Holdings-Lag bei €1000 zeigt in Fold 2 avg_pnl €-1.26, 50% Win-Rate — nächste an Break-even.
- S4 US-Open Lag: zu wenig Trades für statistisch belastbare Aussagen.
- Hauptursache: ASWM-Stundenrenditen überschreiten Break-even (4% bei €500 / 2% bei €1000)
  zu selten. Covered-Call-Overlay begrenzt Upside strukturell.
- Regime-Filter (HMM Bull) und Schwellen-Optimierung nächster Schritt.

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
