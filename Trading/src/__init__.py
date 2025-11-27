"""NIFTY Pin Bar Trading Strategy Module.

Components:
- PinBarStrategy: Bullish pin bar pattern detection with EMA(7) filter
- CandleDataFetcher: Historical/intraday data from Upstox API
- BacktestEngine: Strategy backtesting
- ChargesCalculator: Brokerage estimation
- OrderPlacer: Live/paper order placement
"""

from .data import CandleDataFetcher
from .strategy import PinBarStrategy, Trade
from .backtest import BacktestEngine, BacktestResult
from .charges import ChargesCalculator, TradeCharges
from .orders import OrderPlacer, NIFTY_FUTURES
from .utils import Logger

__version__ = "1.0.0"

__all__ = [
    "CandleDataFetcher",
    "PinBarStrategy",
    "Trade",
    "BacktestEngine",
    "BacktestResult",
    "ChargesCalculator",
    "TradeCharges",
    "OrderPlacer",
    "NIFTY_FUTURES",
    "Logger"
]
