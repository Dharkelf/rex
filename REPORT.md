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

Run: 2026-05-23 (v5). Walk-forward, 3 folds, ~1 443 hourly bars.
Hold: [2,3,5,8,16,24]h. Log-returns. S1-S6 inkl. Zeitfenster-Varianten, Take-Profit-Engine, vix_min.

**Änderungen v5 vs v4:**
- S3: Zeitfenster-Varianten (08-10, 11-13, 13-16 UTC, Mon-Wed, Thu-Fri)
- S4: Zeitfenster-Varianten (08-12, 10-13, 13-16 UTC, Mon-Wed 12-15, Thu-Fri 12-15) + tp15-Variante
  Base S4 zurück auf 13-14 UTC (original Gewinner)
- S5: vix_min = 18 (Covered-Call-Prämien-Zone)
- S6: neu — IV-Prämien-Harvest (Holdings-Pullback + VIX 18-30 + TP 1.5%)
- Engine: Take-Profit-Frühausstieg, Signal-Generator Exit-Zeit-Fix + "Weitere Checks"

### Top-Ergebnisse (€1000 Position, alle Bars)

| Strategy | Hold | Trades/fold | Win% | Ø P&L | W | L | Sharpe |
|---|---|---|---|---|---|---|---|
| S1 BTC-Lag | 24h | 6.7 | 46% | €-3.96 | €+26.10 | €-29.05 | -0.11 |
| **S4_us_open_lag** | **16h** | **1.7** | **88%** | **€+19.93** | **€+26.03** | **€-15.86** | **+0.78** |
| S4_us_open_lag | 24h | 1.7 | 38% | €-0.92 | €+52.03 | €-45.49 | +0.33 |

### S4 Zeitfenster-Experiment (€1000, 16h Hold, alle Bars)

| Variante | Fenster UTC | Trades/fold | Win% | Ø P&L | Sharpe |
|---|---|---|---|---|---|
| **S4_us_open_lag** | **13-14** | **1.7** | **88%** | **€+19.93** | **+0.78** |
| S4_thu_fri_12_15 | 12-15, Do-Fr | 1.7 | 50% | €-4.43 | -1.17 |
| S4_mon_wed_12_15 | 12-15, Mo-Mi | 4.0 | 37% | €-4.92 | -0.22 |
| S4_usopen_13_16 | 13-16 | 6.3 | 39% | €-8.20 | -0.27 |
| S4_morning_08_12 | 8-12 | 1.0 | 33% | €-22.88 | nan |
| S4_preusopen_10_13 | 10-13 | 0.0 | — | — | — |
| S4_usopen_tp15 | 13-16+tp1.5% | 7.7 | 28% | €-10.57 | -0.47 |

**Kernerkenntnis:** Fenster 13-14 UTC ist das einzig profitable. Jede Erweiterung verdünnt die
Signalqualität massiv. Der US-Open-Lag ist ein Präzisionssignal in den ersten 2 Bars nach 13:30 UTC.
Take-Profit 1.5% hilft nicht — die guten Trades brauchen den vollen 16h-Hold.

### S3 Zeitfenster-Experiment (€1000, alle Holds)

Alle S3-Varianten: 0-1.3 Trades/fold, durchgehend negativ. S3-Konzept (Holdings + ASWM-Falling + BTC +
enges Fenster) mit 5 Monaten ASWM-Daten nicht belastbar. Gilt für alle Tagesabschnitte.
**Referenz**: v3 S3 (abs() Bedingung, 8-16 UTC): 4.0 trades/fold, 56%, €-1.35 — marginaler,
aber W/L strukturell schwach (€+24.58 vs €-34.81).

### S5 Mean-Reversion mit vix_min=18 (€1000, alle Bars)

| Hold | Trades/fold | Win% | Ø P&L | W | L | Sharpe |
|---|---|---|---|---|---|---|
| 8h | 6.3 | 50% | €-14.38 | €+19.84 | €-49.46 | -0.38 |
| 16h | 5.0 | 40% | €-11.03 | €+28.04 | €-40.11 | -0.30 |
| 24h | 4.0 | 42% | €-12.56 | €+36.76 | €-41.14 | -0.21 |

_Referenz v4 ohne vix_min: 6.3 trades/fold, 36%, €-12.49. vix_min=18 reduziert Trades leicht,
verbessert Win-Rate auf 40% — minimale Verbesserung. Covered-Call-Deckel begrenzt Bounce strukturell._

### S6 IV Premium Harvest (€1000, alle Bars)

| Hold | Trades/fold | Win% | Ø P&L | W | L | Sharpe |
|---|---|---|---|---|---|---|
| 16h | 9.7 | 42% | €-22.46 | €+7.32 | €-48.04 | -0.64 |
| 24h | 9.0 | 37% | €-23.11 | €+8.18 | €-44.34 | -0.68 |

_S6 nicht funktionsfähig mit aktuellen Parametern: holdings_pullback_threshold -1.5% triggert 10×/fold._
_Avg. Winner €7.32 << TP-Schwelle €15 (1.5%) → TP nie ausgelöst. Konzept mit restriktiverem Threshold_
_(-3% oder -4%) und >2 Jahren ASWM-Daten erneut testen._

### Gesamtbefund v5

- **Einzige positive Strategie**: S4_us_open_lag (13-14 UTC, 16h, €1000): 88%, €+19.93, Sharpe 0.78.
  Mechanisch: die ersten 2 Stunden nach US-Open, wenn MARA/IREN/MSTR stark eröffnen aber ASWM noch
  auf dem XETRA-Niveau des europäischen Handels steht.
- **Zeitfenster-Experiment**: bestätigt 13-14 UTC als einzig funktionierendes Fenster.
- **S3/S6**: Konzepte valide, aber unzureichende Datenbasis (5 Monate ASWM) für statistische Belastbarkeit.
- **S5 vix_min**: minimale Verbesserung, strukturelles Problem bleibt (Covered-Call-Deckel).
- **Nächster Schritt**: Bayesian-Optimierung S4-Schwelle via Optuna; mehr ASWM-Daten abwarten.

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
