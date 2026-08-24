"""
ICT-Backtester-RU - Entry point.
"""
import logging
import argparse
from src.data.provider import load_config, create_provider
from src.analysis.detectors import SwingDetector, FVGDetector, StructureDetector, SweepDetector
from src.analysis.levels import LiquidityLevelDetector
from src.strategies import get_strategy
from src.backtest.engine import BacktestEngine
from src.visualization.chart import ChartRenderer

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="ICT-Backtester-RU")
    parser.add_argument("--config", type=str, default="configs/config.yaml")
    parser.add_argument("--ticker", type=str, help="Ticker for backtest")
    parser.add_argument("--interval", type=str, help="Timeframe")
    parser.add_argument("--days", type=int, help="History depth in days")
    parser.add_argument("--strategy", type=str, default="sweep_mss", help="Strategy name")
    args = parser.parse_args()

    logger.info("Loading configuration...")
    config = load_config(args.config)

    if args.ticker: config["data"]["ticker"] = args.ticker
    if args.interval: config["data"]["interval"] = args.interval
    if args.days: config["data"]["days_back"] = args.days

    logger.info(f"Ticker: {config['data']['ticker']}")
    logger.info(f"Strategy: {args.strategy}")
    
    logger.info("Initializing data provider...")
    provider = create_provider(config)
    
    logger.info("Loading historical data...")
    df = provider.get_historical_data(
        ticker=config["data"]["ticker"],
        interval=config["data"]["interval"],
        days_back=config["data"]["days_back"]
    )
    logger.info(f"Loaded {len(df)} candles")

    logger.info("Initializing detectors...")
    swing_detector = SwingDetector(
        left_bars=config["detectors"]["swing"]["left_bars"],
        right_bars=config["detectors"]["swing"]["right_bars"]
    )
    fvg_detector = FVGDetector(
        min_size_percent=config["detectors"]["fvg"]["min_size_percent"],
        max_age_bars=config["detectors"]["fvg"]["max_age_bars"]
    )
    structure_detector = StructureDetector()
    sweep_detector = SweepDetector()
    level_detector = LiquidityLevelDetector(
        cluster_distance_percent=config["detectors"]["levels"]["cluster_distance_percent"],
        min_touches=config["detectors"]["levels"]["min_touches"]
    )

    logger.info("Running pattern analysis...")
    swings = swing_detector.detect(df)
    fvgs = fvg_detector.detect(df)
    breaks = structure_detector.detect(df, swings)
    sweeps = sweep_detector.detect(df, swings)
    levels = level_detector.detect(df, swings)

    logger.info(f"Found: {len(swings)} swings, {len(fvgs)} FVGs, {len(breaks)} breaks, {len(sweeps)} sweeps, {len(levels)} levels")

    # Запуск стратегии
    logger.info(f"Running strategy: {args.strategy}")
    strategy_config = config["strategies"].get(args.strategy, {})
    strategy = get_strategy(args.strategy, strategy_config)
    signals = strategy.generate_signals(df, swings, fvgs, breaks, sweeps, levels)
    logger.info(f"Generated {len(signals)} signals")

    # Бэктест
    logger.info("Running backtest...")
    engine = BacktestEngine(config["backtest"])
    results = engine.run(df, strategy, signals)

    # Визуализация
    logger.info("Creating visualization...")
    renderer = ChartRenderer(config["visualization"])
    renderer.render_backtest_results(
        df=df,
        trades=results['trades'],
        fvgs=fvgs,
        levels=levels,
        metrics=results['metrics'],
        output_path=f"backtest_{args.strategy}_{config['data']['ticker']}.html"
    )

    # Вывод метрик
    logger.info("=" * 60)
    logger.info("BACKTEST RESULTS")
    logger.info("=" * 60)
    for key, value in results['metrics'].items():
        logger.info(f"{key}: {value}")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()