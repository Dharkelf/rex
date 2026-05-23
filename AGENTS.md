# AGENTS.md — REX: Crypto Equity Income Signal Pipeline

This file governs how AI agents (Claude Code, Codex, etc.) work in this repository.
Read it before making any structural or architectural decisions.

---

## Project Purpose

Hourly-resolution data pipeline, backtest engine, and live signal generator for the
**REX Crypto Equity Income & Growth UCITS ETF** (ISIN IE0008BA4TY1, WKN A419AX).

- **Exchange (trading):** XETRA — ticker `ASWM.DE` (EUR)
- **Reference feed:** LSE — ticker `CEGI.L` (USD)
- **Tradegate feed:** scraped from tradegate.de (live quote only, no historical Parquet)
- **Broker:** flatex.at (no automated order execution — signal output only)

The pipeline:
1. Collects 1h OHLCV for the ETF and all feature series (yfinance + Tradegate scraper).
2. Detects the current market regime (Bull / Neutral / Bear) via GaussianHMM + Bayesian
   feature-subset optimisation (Optuna).
3. Predicts the next 1–8h return via XGBoost (autoregressive) and NeuralProphet.
4. Emits a human-readable trading signal at four scheduled times and on demand,
   including sensitivity analysis for €500 and €1000 position sizes.

**No automated order execution.** Signals are console output + log file only.

---

## Standard Directory Layout

```
<project-root>/
├── AGENTS.md               # this file
├── README.md               # technical wiki (mandatory, always committed)
├── REPORT.md               # observed runtime behaviour
├── requirements.txt        # pinned deps (pip freeze after every install)
├── .gitignore
├── .env                    # secrets — NEVER commit
├── .env.example            # template
├── .pre-commit-config.yaml
│
├── config/
│   └── settings.yaml       # single source of truth for all parameters
│
├── data/                   # gitignored
│   ├── raw/                # append-only Parquet per symbol
│   └── processed/          # feature matrix, regime labels
│
├── src/
│   ├── __init__.py
│   ├── utils/              # path helpers, logging setup
│   ├── collector/          # yfinance fetcher + Tradegate scraper
│   ├── backtest/           # strategy engine + walk-forward evaluation
│   ├── hmm/                # GaussianHMM + Optuna regime detection
│   ├── predictor/          # XGBoost + NeuralProphet
│   └── signal/             # live signal generator + APScheduler
│
├── tests/
│   ├── conftest.py
│   ├── test_collector.py
│   ├── test_backtest.py
│   ├── test_hmm.py
│   ├── test_predictor.py
│   └── test_signal.py
│
├── notebooks/              # exploration only
│
└── main.py                 # CLI entry point
```

---

## Modules

| Module | Path | Responsibility |
|---|---|---|
| utils | `src/utils/` | Path helpers, logging config, timezone constants |
| collector | `src/collector/` | yfinance 1h fetcher (ASWM.DE + features), Tradegate live scraper, append-only Parquet |
| backtest | `src/backtest/` | 4 strategies, walk-forward TimeSeriesSplit, break-even analysis, sensitivity (€500/€1000) |
| hmm | `src/hmm/` | Feature engineering, GaussianHMM, Optuna Bayesian optimisation, regime labelling |
| predictor | `src/predictor/` | XGBoost with autoregressive lags (per regime), NeuralProphet multivariate |
| signal | `src/signal/` | APScheduler (4 triggers), on-demand CLI, Tradegate deviation check, console/log output |

---

## ETF & Data Facts

- **Inception:** 2025-07-02 — ~222 trading days / ~1 444 hourly bars (full history available)
- **XETRA hours:** 09:00–17:30 CET (08:00–16:30 UTC)
- **Tradegate hours:** 08:00–22:00 CET (available for pre/post-XETRA signals)
- **US markets open:** 15:30 CET — key structural delay point
- **AUM:** ~$16.6M (small fund; spreads may be wider than large ETFs)
- **TER:** 0.65% | **Distribution:** monthly, covered-call income (~19% p.a.)
- **Covered-call overlay:** ~50% of holdings — upside partially capped

### Top 10 Holdings (update manually when fund rebalances)

| Symbol | Name | Weight |
|---|---|---|
| MU | Micron Technology | 5.45% |
| APLD | Applied Digital | 5.04% |
| AMD | Advanced Micro Devices | 4.75% |
| MARA | MARA Holdings | 4.49% |
| IREN | IREN Ltd | 4.48% |
| HOOD | Robinhood Markets | 4.23% |
| NVDA | Nvidia | 4.16% |
| TSLA | Tesla | 3.99% |
| V | Visa | 3.93% |
| MSTR | Strategy (MicroStrategy) | 3.93% |

### Feature Series

| Symbol | Description | Source |
|---|---|---|
| `BTC-USD` | Bitcoin / USD | yfinance |
| `ETH-USD` | Ethereum / USD | yfinance |
| `BITQ` | Bitwise Crypto Industry Innovators ETF | yfinance |
| `SMH` | VanEck Semiconductor ETF | yfinance |
| `IPAY` | ETFMG Prime Mobile Payments ETF | yfinance |
| `QQQ` | NASDAQ-100 | yfinance |
| `^VIX` | CBOE Volatility Index | yfinance |
| MU, APLD, AMD, MARA, IREN, HOOD, NVDA, TSLA, V, MSTR | Top-10 holdings | yfinance |
| Tradegate quote | Live ASWM bid/ask pre/post XETRA | tradegate.de scrape |

---

## Signal Triggers

| Time CET | Name | Horizon | Data required |
|---|---|---|---|
| 08:45 | Overnight-Gap | 3h or until noon | BTC overnight move, Tradegate live |
| 09:15 | XETRA-Open Momentum | 3h | First XETRA bar |
| 15:35 | US-Open Lag | until 17:30 | US holdings open vs ASWM lag |
| 17:00 | Evening / Overnight Hold | until next morning | Daily summary |

On-demand: `python main.py --signal`

### Signal Output Format

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

`KEIN EINSTIEG — Regime: NEUTRAL` when no signal.

---

## Backtest Strategies

| ID | Name | Entry | Exit |
|---|---|---|---|
| S1 | BTC-Lag | BTC 1h return > threshold → Long ASWM next bar | +3h |
| S2 | Overnight-Gap | BTC move 16:30–09:00 → entry at XETRA open | +3h or noon |
| S3 | Holdings-Lag | MARA/IREN/MSTR move > threshold, ASWM not yet moved | +1–3 bars |
| S4 | US-Open Lag | Holdings open strongly at 15:30, ASWM lags | until 16:30 |

Break-even computed for both €500 (4.0%) and €1000 (2.0%) at flat €10/side transaction costs.
Walk-forward: `TimeSeriesSplit` with 3 folds on the ~1 444 hourly bars.

---

## Pre-commit Hooks

```bash
pip install pre-commit
pre-commit install
```

Hooks run in order: **ruff** (lint + format) → **mypy** (type check) → **pytest** (full suite).
No commit may pass with errors in any hook.

---

## Testing

- Unit tests mock yfinance and HTTP calls; use synthetic DataFrames.
- Integration tests use real Parquet fixtures from `tests/fixtures/`.
- Time-series models: always `TimeSeriesSplit` — never shuffle.
- Run before every commit: `pytest tests/ -v`

---

## Design Patterns

| Pattern | Location |
|---|---|
| **Repository** | `DataRepository` in `collector/` — single access point per symbol |
| **Strategy** | `BacktestStrategy` ABC in `backtest/` — one class per strategy |
| **Factory** | `ModelFactory` in `predictor/` — constructs XGB/NeuralProphet from config |
| **Template Method** | `BaseSignalGenerator` in `signal/` — skeleton defines trigger flow |
| **Observer** | APScheduler job hooks for signal emission |

---

## Coding Conventions

- Python 3.11+. Type hints on all public functions and methods.
- `logging` only — never `print()` in library code.
- No hard-coded values — all parameters in `config/settings.yaml`.
- Parquet (append-only) for OHLCV storage. UTC timestamps (`datetime64[ns, UTC]`).
- `TimeSeriesSplit` for all cross-validation — never shuffle time-series data.
- All file I/O via path helpers in `src/utils/paths.py`.

---

## Data Conventions

- Raw Parquet files are **append-only**. Never overwrite; deduplicate on load.
- All timestamps stored as UTC. Display in CET for signal output.
- XETRA trading mask: 08:00–16:30 UTC (09:00–17:30 CET), Mon–Fri.
- US-Open bar: 13:30 UTC (14:30 UTC in winter / 15:30 CET summer).

---

## Reproducibility

- All random seeds in `settings.yaml` (`hmm.random_state`, `hmm.optuna_seed`).
- `requirements.txt` regenerated via `pip freeze` after every dependency change.
- Feature schema versioned in `settings.yaml` (`feature_schema_version`).

---

## Failure Conditions — Agents Must NOT

- Push to remote without explicit user request.
- Overwrite existing Parquet files (append only).
- Hard-code numeric values that belong in `settings.yaml`.
- Use `print()` in library code.
- Commit `.env`, `data/`, `.venv/`, `__pycache__/`.
- Skip or silence failing tests.
- Emit any automated buy/sell order — signal output is read-only.

---

## Git Rules

- **Never push automatically.** `git push` only on explicit user request.
- Conventional Commits: `<type>(<scope>): <subject>` (imperative, max 72 chars)
- Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`
- Always commit: `AGENTS.md`, `README.md`, `config/settings.yaml`, `requirements.txt`

---

## External References

- HANetf fund page: https://hanetf.com/de/fund/cegi-crpto-equity-income-and-growth-etf/
- Tradegate quote: https://www.tradegate.de/orderbuch.php?isin=IE0008BA4TY1
- yfinance docs: https://ranaroussi.github.io/yfinance/
- deribit blueprint: https://github.com/Dharkelf/deribit
- hmmlearn: https://hmmlearn.readthedocs.io/
- Optuna: https://optuna.readthedocs.io/
- NeuralProphet: https://neuralprophet.com/
