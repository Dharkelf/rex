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

Run: 2026-05-23 (v3). Walk-forward, 3 folds, ~1 443 hourly bars.
Default thresholds (nicht optimiert). Hold: [2,3,5,8,16,24]h. Log-returns. Regime-Filter (HMM Bull).
W = avg. winner / L = avg. loser (long-only Aufschlüsselung).

### Top-Ergebnisse (€1000 Position, alle Bars)

| Strategy | Hold | Trades/fold | Win% | Ø P&L | W | L | Sharpe |
|---|---|---|---|---|---|---|---|
| S1 BTC-Lag | 24h | 6.7 | 46% | €-3.96 | €+26.10 | €-29.05 | -0.11 |
| S3 Holdings-Lag | 16h | 4.0 | 56% | **€-1.35** | €+24.58 | €-34.81 | -0.02 |
| S4 US-Open Lag | 16h | 1.7 | **88%** | **€+19.93** | €+26.03 | €-15.86 | +0.78 |
| S4 US-Open Lag | 24h | 1.7 | 38% | €-0.92 | €+52.03 | €-45.49 | +0.33 |

### S1 BTC-Lag — Hold-Sweep (€1000, alle Bars)

| Hold | Trades/fold | Win% | Ø P&L | W | L | Sharpe |
|---|---|---|---|---|---|---|
| 3h | 12.7 | 22% | €-15.43 | €+6.30 | €-21.56 | -1.06 |
| 16h | 9.7 | 15% | €-21.59 | €+28.44 | €-30.11 | -0.79 |
| **24h** | **6.7** | **46%** | **€-3.96** | **€+26.10** | **€-29.05** | **-0.11** |

### S3 Holdings-Lag — Hold-Sweep (€1000, alle Bars)

| Hold | Trades/fold | Win% | Ø P&L | W | L | Sharpe |
|---|---|---|---|---|---|---|
| 8h | 4.3 | 33% | €-10.73 | €+12.43 | €-23.48 | -0.59 |
| **16h** | **4.0** | **56%** | **€-1.35** | **€+24.58** | **€-34.81** | **-0.02** |
| 24h | 3.7 | 33% | €-20.35 | €+31.83 | €-51.02 | -0.83 |

### S4 US-Open Lag — Hold-Sweep (€1000, alle Bars)

| Hold | Trades/fold | Win% | Ø P&L | W | L | Sharpe |
|---|---|---|---|---|---|---|
| 8h | 1.7 | 25% | €-7.05 | €+4.24 | €-10.73 | -0.30 |
| **16h** | **1.7** | **88%** | **€+19.93** | **€+26.03** | **€-15.86** | **+0.78** |
| 24h | 1.7 | 38% | €-0.92 | €+52.03 | €-45.49 | +0.33 |

### S5 Mean-Reversion — Hold-Sweep (€1000, alle Bars)

| Hold | Trades/fold | Win% | Ø P&L | W | L | Sharpe |
|---|---|---|---|---|---|---|
| 8h | 22.7 | 32% | €-15.61 | €+19.39 | €-31.66 | -0.51 |
| 16h | 14.7 | 41% | €-13.08 | €+25.27 | €-40.14 | -0.31 |
| 24h | 11.0 | 31% | €-17.43 | €+29.85 | €-38.38 | -0.52 |

### Regime-Filter (HMM Bull only) — Auswirkung

| Strategy | Hold | Alle Bars Ø P&L | Bull only Ø P&L | Trades/fold (Bull) |
|---|---|---|---|---|
| S1 BTC-Lag | 24h | €-3.96 | €-8.30 | 5.3 |
| S3 Holdings-Lag | 16h | €-1.35 | €-12.04 | 2.7 |
| S4 US-Open Lag | 16h | **€+19.93** | NaN (0 Trades) | 0.0 |
| S5 Mean-Reversion | 16h | €-13.08 | €-19.64 | 11.3 |

**Interpretation (v3):**
- **S4 US-Open Lag + 16h + €1000**: weiterhin einzige Strategie mit positivem Ø P&L (€+19.93).
  W/L zeigt: durchschn. Gewinner €+26.03, Verlierer €-15.86 — gutes W/L-Verhältnis 1.64.
  Aber: nur 5 Trades total (1.7/fold) — nicht statistisch belastbar.
  **S4 im Bull-Regime: 0 Trades** — US-Open-Signale entstehen nie im HMM-Bull-Zustand.
  Das deutet darauf hin, dass der HMM-Regime-Filter für S4 nicht passend ist.
- **S1 BTC-Lag + 24h**: 46% Win-Rate, €-3.96 — deutlich besser als 16h. Mit Schwellen-Opt. ausbaufähig.
- **S3 Holdings-Lag + 16h**: W/L-Verhältnis strukturell schwach (€+24.58 vs €-34.81) — Verlierer
  sind fast 50% größer als Gewinner. Trotz 56% Win-Rate negatives Ø P&L.
- **S5 Mean-Reversion**: zu viele Trades (Drawdown-Schwelle 2% zu niedrig — ETF ist strukturell
  oft >2% unter 24h-High wegen Covered-Call). VIX-Filter und Volatilitäts-Filter reduzieren
  Trades kaum. Drawdown-Schwelle auf -4% oder -5% erhöhen (nächste Optimierung).
- **Regime-Filter schadet generell**: Bull-only führt zu weniger Trades aber schlechterer Performance
  — HMM-Bull-Regime korreliert nicht mit Strategiesignalen der S1–S5.
- **Nächster Schritt**: Schwellen-Optimierung via Optuna (Bayesian), insb. S5-Drawdown-Schwelle.

---

## HMM Regime Model

Run: 2026-05-23 (v2 — log-returns + StandardScaler). GaussianHMM, 3 states, 100 Optuna trials (TPE).
Saved: `data/processed/hmm_model_v1.pkl`.

| Metric | Value |
|---|---|
| n_components | 3 |
| Features (Optuna best) | vix_change_1h, holdings_composite_1h, us_open_flag |
| n_samples | 1 443 |
| Total log-likelihood | 12 933 643 |
| Bull regime (State 0) | 438 bars = 30.4% — mean ASWM log-return **+0.147%/h** |
| Neutral regime (State 1) | 318 bars = 22.0% — mean ASWM log-return −0.031%/h |
| Bear regime (State 2) | 687 bars = 47.6% — mean ASWM log-return −0.045%/h |

**Verbesserung gegenüber v1 (einfache Returns, kein Scaler):**
- Regime-Separation deutlich stärker: Bull +0.147%/h vs. Neutral/Bear ~−0.04%/h
  (v1: +0.081% vs. +0.020% / −0.016% — kaum unterscheidbar)
- Bull-Anteil 30.4% (v1: 13.8%) — mehr Handelssignale in besserem Marktumfeld
- StandardScaler stabilisiert das EM-Training und verhindert featureskalen-dominanz

**Interpretation:**
- In Bull-Regime: erwartete Stundenrendite +0.147% → bei 16h Hold ca. +2.35% kumuliert
  = knapp über Break-even (€1000 Position: 2.0%). **Erste positive Erwartungswertstruktur.**
- Bear hat knapp die Hälfte aller Bars — strukturell bearishes Marktumfeld seit ETF-Inception.
  Covered-Call-Overlay dämpft Upside auch in Bull-Phasen.
- Nächster Schritt: Backtest mit Regime-Filter (nur Bull) → erwartete Win-Rate-Verbesserung.

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
