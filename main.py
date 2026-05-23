"""CLI entry point — wires modules, no business logic."""

from __future__ import annotations

import argparse
import sys

from src.utils.logging_setup import setup_logging


def _collect() -> None:
    from src.collector.fetcher import collect_all
    results = collect_all()
    total = sum(results.values())
    print(f"Collection done: {len(results)} symbols, {total} new rows")


def _backtest() -> None:
    from src.backtest.runner import run_backtest
    run_backtest()


def _fit_hmm() -> None:
    from src.hmm.detector import RegimeDetector
    from src.hmm.features import build_feature_matrix
    from src.utils.paths import feature_matrix_path

    import pyarrow as pa
    import pyarrow.parquet as pq

    fm = build_feature_matrix()
    pq.write_table(pa.Table.from_pandas(fm), feature_matrix_path())

    detector = RegimeDetector()
    detector.fit(fm)
    print("HMM regime model fitted and saved.")


def _train() -> None:
    from src.hmm.detector import RegimeDetector
    from src.hmm.features import build_feature_matrix
    from src.predictor.factory import ModelFactory

    fm = build_feature_matrix()
    detector = RegimeDetector()
    try:
        detector.load()
        regimes = detector.predict(fm)
    except FileNotFoundError:
        regimes = None

    n_regimes = 3
    for r in range(n_regimes):
        model = ModelFactory.xgb(regime=r)
        model.fit(fm, regimes=regimes)

    # Also train regime-agnostic model
    model_all = ModelFactory.xgb(regime=None)
    model_all.fit(fm)

    np_model = ModelFactory.neural_prophet()
    np_model.fit(fm)
    print("Predictors trained and saved.")


def _signal(trigger: str = "xetra_open") -> None:
    from src.signal.generator import SignalGenerator
    gen = SignalGenerator()
    output = gen.run(trigger=trigger)
    print(output.format())


def _schedule() -> None:
    from src.signal.scheduler import start_scheduler
    start_scheduler()


def _all() -> None:
    _collect()
    _fit_hmm()
    _train()
    _signal()


def main() -> None:
    setup_logging()

    parser = argparse.ArgumentParser(
        prog="rex",
        description="REX Crypto Equity Income Signal Pipeline",
    )
    parser.add_argument("--collect", action="store_true", help="Fetch/update all 1h data")
    parser.add_argument("--backtest", action="store_true", help="Run walk-forward backtest")
    parser.add_argument("--fit-hmm", action="store_true", help="Fit HMM regime model")
    parser.add_argument("--train", action="store_true", help="Train XGB + NeuralProphet predictors")
    parser.add_argument(
        "--signal",
        nargs="?",
        const="xetra_open",
        metavar="TRIGGER",
        help="Emit signal on demand (overnight|xetra_open|us_open|evening)",
    )
    parser.add_argument("--schedule", action="store_true", help="Start APScheduler (blocking)")
    parser.add_argument("--all", action="store_true", help="collect → fit-hmm → train → signal")

    args = parser.parse_args()

    if args.collect:
        _collect()
    elif args.backtest:
        _backtest()
    elif args.fit_hmm:
        _fit_hmm()
    elif args.train:
        _train()
    elif args.signal is not None:
        _signal(trigger=args.signal)
    elif args.schedule:
        _schedule()
    elif getattr(args, "all"):
        _all()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
