# REX — Crypto Equity Income Signal Pipeline

Hourly signal pipeline for the **REX Crypto Equity Income & Growth UCITS ETF**
(ISIN IE0008BA4TY1, WKN A419AX, XETRA ticker `ASWM.DE`).

Collects 1h market data, detects the current market regime (Bull / Neutral / Bear),
predicts short-term ETF returns, and emits human-readable trading signals at four
scheduled times per day or on demand. No automated order execution.

---

## Architecture

```
  External sources
  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐
  │  yfinance    │  │ tradegate.de │  │  config/      │
  │  (1h OHLCV)  │  │  (live quot) │  │  settings.yaml│
  └──────┬───────┘  └──────┬───────┘  └──────┬────────┘
         │                 │                  │
         ▼                 ▼                  │
  ┌─────────────────────────────┐             │
  │   src/collector/            │◄────────────┘
  │   DataRepository            │
  │   append-only Parquet       │
  └──────────────┬──────────────┘
                 │  data/raw/*.parquet
                 ▼
  ┌─────────────────────────────┐
  │   src/hmm/                  │
  │   FeatureEngineer           │
  │   GaussianHMM + Optuna      │
  │   → regime label (0/1/2)    │
  └──────────────┬──────────────┘
                 │
        ┌────────┴────────┐
        ▼                 ▼
  ┌───────────┐    ┌───────────────┐
  │ src/      │    │ src/          │
  │ backtest/ │    │ predictor/    │
  │ 4 strats  │    │ XGB +         │
  │ walk-fwd  │    │ NeuralProphet │
  └───────────┘    └───────┬───────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │  src/signal/    │
                  │  APScheduler    │
                  │  4 triggers     │
                  │  console + log  │
                  └────────┬────────┘
                           │
                           ▼
                  [KAUFE ASWM.DE am Ask]
                  [KEIN EINSTIEG]
```

### Module Overview

```
  src/
  ├── utils/        path helpers, logging, timezone constants
  ├── collector/    DataRepository (yfinance fetcher + Tradegate scraper)
  ├── backtest/     BacktestStrategy ABC + 4 concrete strategies
  ├── hmm/          FeatureEngineer, RegimeDetector, BayesianOptimiser
  ├── predictor/    ModelFactory → XGBPredictor, NeuralProphetPredictor
  └── signal/       BaseSignalGenerator → 4 trigger subclasses, scheduler
```

---

## Setup

```bash
git clone https://github.com/Dharkelf/rex.git
cd rex
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pre-commit install
cp .env.example .env
# edit .env if needed (LOG_LEVEL etc.)
```

---

## Configuration

All parameters are in `config/settings.yaml`. Key sections:

| Section | Description |
|---|---|
| `etf` | Target ticker, XETRA/Tradegate hours, deviation threshold |
| `holdings` | Top-10 fund holdings with weights |
| `features.symbols` | All 1h feature series fetched by collector |
| `backtest` | Fee per side, position sizes, strategy thresholds, n_splits |
| `hmm` | n_components, n_iter, Optuna trials/seed, feature candidates |
| `predictor` | XGB and NeuralProphet hyperparameters, forecast horizons |
| `signal` | Trigger times (CET), min_confidence, log file path |
| `logging` | Level, format |

---

## Usage

### Collect / update all data
```bash
python main.py --collect
```

### Run backtest (all 4 strategies, walk-forward)
```bash
python main.py --backtest
```

### Fit HMM regime model
```bash
python main.py --fit-hmm
```

### Train predictors
```bash
python main.py --train
```

### Emit signal on demand
```bash
python main.py --signal
```

### Start scheduler (runs all day, triggers at 08:45 / 09:15 / 15:35 / 17:00 CET)
```bash
python main.py --schedule
```

### Full pipeline (collect → fit → train → signal)
```bash
python main.py --all
```

---

## Data

### Storage layout
```
data/
├── raw/
│   ├── ASWM.DE_1h.parquet      # target ETF (EUR, XETRA)
│   ├── CEGI.L_1h.parquet       # reference feed (USD, LSE)
│   ├── BTC-USD_1h.parquet
│   ├── ETH-USD_1h.parquet
│   ├── BITQ_1h.parquet
│   ├── SMH_1h.parquet
│   ├── IPAY_1h.parquet
│   ├── QQQ_1h.parquet
│   ├── ^VIX_1h.parquet
│   └── <HOLDING>_1h.parquet    # MU, APLD, AMD, MARA, IREN, HOOD, NVDA, TSLA, V, MSTR
└── processed/
    ├── feature_matrix.parquet  # engineered features, aligned to ASWM.DE index
    └── regimes.parquet         # regime label per hour
```

### Schema (raw Parquet, all symbols)

| Column | Type | Notes |
|---|---|---|
| `timestamp` | `datetime64[ns, UTC]` | index, UTC |
| `open` | float64 | |
| `high` | float64 | |
| `low` | float64 | |
| `close` | float64 | |
| `volume` | float64 | |

All files are **append-only**. Duplicates are dropped on load (keep last).

### ETF Data Facts

- Inception: 2025-07-02 → ~222 trading days / ~1 444 hourly bars
- XETRA session: 09:00–17:30 CET (08:00–16:30 UTC)
- US open: 15:30 CET — key structural delay window
- AUM: ~$16.6M | TER: 0.65% | Distribution: monthly (~19% p.a. from covered calls)

---

## Signal Output Format

```
[2026-05-23 09:15 CET]  REGIME: BULL (78%)
Signal:    KAUFE ASWM.DE am Ask
Haltedauer: 3h  (Exit ~12:15 CET)

SENSITIVITÄT:
  €500  →  Break-even +4.0%  |  Erwartet +2.1% / +6.4% (p25/p75)  |  Ø P&L: +€ 9
  €1000 →  Break-even +2.0%  |  Erwartet +2.1% / +6.4% (p25/p75)  |  Ø P&L: +€31

Treiber: BTC +2.3% (2h) | MARA +3.1% | BITQ +1.8%
Tradegate: €27.15 (+0.8% vs. XETRA-Close)  ← nur ausgewiesen wenn >0.5%
```

### Signal Trigger Times

```
08:45 CET  Overnight-Gap    BTC overnight move → 3h or until noon
09:15 CET  XETRA-Open       First XETRA bar momentum → 3h
15:35 CET  US-Open Lag      Holdings open vs ASWM lag → until 17:30
17:00 CET  Evening          Overnight hold → until next 09:00
```

### Delay-Hypothesis (structural basis for signals)

```
XETRA 09:00 opens
│
├── 09:00–15:30  ASWM price driven by BTC / overnight crypto moves
│                (US stocks not yet open → indirect pricing only)
│
├── 15:30        US markets open
│                NVDA, AMD, MARA, IREN etc. get real price discovery
│                ASWM.DE lags by 1–3 bars → tradeable window
│
└── 17:30        XETRA closes
                 US stocks continue → overnight gap accumulates
                 visible next morning at 09:00 open
```

---

## Backtest Strategies

| ID | Name | Entry condition | Hold |
|---|---|---|---|
| S1 | BTC-Lag | BTC 1h return > threshold | +3h |
| S2 | Overnight-Gap | BTC move during XETRA-closed window | +3h |
| S3 | Holdings-Lag | MARA/IREN/MSTR move > threshold, ASWM not yet | +1–3 bars |
| S4 | US-Open Lag | Holdings open > threshold at 15:35, ASWM lags | until 16:30 |

Walk-forward: `TimeSeriesSplit` with 3 folds on ~1 444 hourly bars.

Break-even analysis per strategy:
```
Position €500:   round-trip €20  →  break-even +4.0%
Position €1000:  round-trip €20  →  break-even +2.0%
```

---

## Development

```bash
# Run tests
pytest tests/ -v

# Lint + format + type check
pre-commit run --all-files

# Add a new strategy: subclass BacktestStrategy in src/backtest/strategies.py
# Add a new feature: add symbol to features.symbols in config/settings.yaml
```

### Adding a module

1. Create `src/<module>/` with `__init__.py` and module files.
2. Add module description to `AGENTS.md` module table.
3. Add corresponding `tests/test_<module>.py`.
4. Update `README.md` architecture section.
5. Commit all four files together.

---

## Known Limitations

- Only ~222 trading days / ~1 444 hourly bars since fund inception (2025-07-02).
  Walk-forward splits are statistically limited; results carry wide confidence intervals.
- Covered-call overlay on ~50% of holdings caps upside; return asymmetry is not yet
  explicitly modelled — treated as symmetric in current backtest.
- Tradegate feed is live-only (scraped on demand); no historical Tradegate Parquet.
- yfinance 1h data has a 730-day rolling window; older bars are permanently lost.
- Small AUM ($16.6M) may produce wider-than-expected XETRA spreads.

---

## Future Improvements

1. Model covered-call payoff explicitly (Black-Scholes overlay on return distribution).
2. Ingest Deribit BTC funding rate as regime feature (from Dharkelf/deribit pipeline).
3. Extend to 5-minute resolution via a paid data provider (Polygon.io).
4. Add Flatex broker API for live bid/ask confirmation and automated order logging.
5. Expand holdings to full 25-position index as individual features.

---

## References

- HANetf fund page: https://hanetf.com/de/fund/cegi-crpto-equity-income-and-growth-etf/
- Tradegate quote: https://www.tradegate.de/orderbuch.php?isin=IE0008BA4TY1
- deribit pipeline blueprint: https://github.com/Dharkelf/deribit
- hmmlearn: https://hmmlearn.readthedocs.io/
- Optuna: https://optuna.readthedocs.io/
- NeuralProphet: https://neuralprophet.com/
- yfinance: https://ranaroussi.github.io/yfinance/
