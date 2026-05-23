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
Default thresholds from settings.yaml (nicht optimiert). Hold-Perioden: [2, 3, 5, 8, 16]h.

### Bestes Hold-Ergebnis je Strategie (Ø über 3 Folds, €1000 Position)

| Strategy | Hold | Trades/fold | Win rate | Ø P&L | Sharpe | Break-even |
|---|---|---|---|---|---|---|
| S1 BTC-Lag | 3h | 12.7 | 22% | €-15.43 | -1.06 | 2.0% |
| S2 Overnight-Gap | 16h | 11.0 | 26% | €-16.86 | -0.60 | 2.0% |
| S3 Holdings-Lag | 16h | 4.0 | **56%** | **€-1.35** | -0.02 | 2.0% |
| S4 US-Open Lag | 16h | 1.7 | **88%** | **€+19.93** | +0.78 | 2.0% |

### S1 BTC-Lag — alle Hold-Perioden (€1000)

| Hold | Trades/fold | Win% | Ø P&L | Sharpe |
|---|---|---|---|---|
| 2h | 13.3 | 14% | €-15.48 | -1.25 |
| 3h | 12.7 | 22% | €-15.43 | -1.06 |
| 5h | 12.3 | 16% | €-17.48 | -1.07 |
| 8h | 10.7 | 30% | €-19.69 | -0.68 |
| 16h | 9.7 | 15% | €-21.59 | -0.79 |

### S2 Overnight-Gap — alle Hold-Perioden (€1000)

| Hold | Trades/fold | Win% | Ø P&L | Sharpe |
|---|---|---|---|---|
| 2h | 23.0 | 5% | €-20.44 | -2.29 |
| 3h | 23.0 | 7% | €-20.47 | -1.82 |
| 5h | 22.0 | 16% | €-19.10 | -0.99 |
| 8h | 14.7 | 18% | €-24.69 | -0.84 |
| 16h | 11.0 | 26% | €-16.86 | -0.60 |

### S3 Holdings-Lag — alle Hold-Perioden (€1000)

| Hold | Trades/fold | Win% | Ø P&L | Sharpe |
|---|---|---|---|---|
| 2h | 4.3 | 28% | €-12.76 | -0.83 |
| 3h | 4.3 | 33% | €-13.89 | -0.72 |
| 5h | 4.3 | 28% | €-14.69 | -0.75 |
| 8h | 4.3 | 33% | €-10.73 | -0.59 |
| **16h** | **4.0** | **56%** | **€-1.35** | **-0.02** |

### S4 US-Open Lag — alle Hold-Perioden (€1000)

| Hold | Trades/fold | Win% | Ø P&L | Sharpe |
|---|---|---|---|---|
| 2h | 1.7 | 25% | €-10.58 | -0.51 |
| 3h | 1.7 | 25% | €-17.88 | -0.50 |
| 5h | 1.7 | 25% | €-25.60 | -0.51 |
| 8h | 1.7 | 25% | €-7.05 | -0.30 |
| **16h** | **1.7** | **88%** | **€+19.93** | **+0.78** |

**Interpretation:**
- Alle Strategien bei kurzen Hold-Perioden (<8h) klar unprofitabel nach Transaktionskosten.
- **16h Hold (Overnight)** ist strukturell am besten — ETF erholt sich im Laufe des nächsten Handelstags.
- **S3 Holdings-Lag + 16h + €1000**: Ø P&L €-1.35, 56% Win-Rate — fast Break-even.
  Nur 4 Trades/Fold; mit Regime-Filter potenziell profitabel.
- **S4 US-Open Lag + 16h + €1000**: Ø P&L €+19.93, 88% Win-Rate — **einzige Strategie mit positivem Ø P&L**.
  Aber: nur 1.7 Trades/Fold (≈5 Trades gesamt) — statistisch nicht belastbar.
  Alle Trades aus Fold 1+3; Fold 2 hat 0 Trades (kein Signal erfüllt).
- **S1 BTC-Lag**: Länger halten schadet — Covered-Call-Overlay kürzt Upside bei starken BTC-Moves.
- **S2 Overnight-Gap**: Zu viele False Positives (ETF reagiert nicht bei jedem BTC-Overnight-Move).
- Hauptursache genereller Underperformance: ASWM break-even 2% bei €1000 wird zu selten
  überschritten; Covered-Call-Overlay begrenzt Upside strukturell.
- **Nächste Schritte**: HMM Regime-Filter (nur in Bull-Phase handeln) + Schwellen-Optimierung.

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
