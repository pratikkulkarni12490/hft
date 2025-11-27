"""Trading Logger - Detailed logging for live trading analysis.

Generates daily log files with comprehensive candle and decision data.
Log files are stored in: ~/trading_logs/YYYY-MM-DD.log
"""

import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import pandas as pd


class TradingLogger:
    """Specialized logger for trading decisions and candle analysis."""
    
    _instance: Optional['TradingLogger'] = None
    LOG_DIR = Path.home() / "trading_logs"
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.LOG_DIR.mkdir(parents=True, exist_ok=True)
        self._current_date = None
        self._logger = None
        self._file_handler = None
        self._setup_logger()
    
    def _setup_logger(self):
        """Setup or rotate the logger for the current day."""
        today = datetime.now().strftime("%Y-%m-%d")
        
        if self._current_date == today and self._logger:
            return
        
        # Remove old file handler if exists
        if self._file_handler and self._logger:
            self._logger.removeHandler(self._file_handler)
        
        self._current_date = today
        log_file = self.LOG_DIR / f"{today}.log"
        
        self._logger = logging.getLogger("TradingAnalysis")
        self._logger.setLevel(logging.DEBUG)
        self._logger.handlers = []  # Clear existing handlers
        
        # File handler for detailed logs
        self._file_handler = logging.FileHandler(log_file, mode='a')
        self._file_handler.setLevel(logging.DEBUG)
        
        # Detailed format for analysis
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self._file_handler.setFormatter(formatter)
        self._logger.addHandler(self._file_handler)
        
        # Console handler for important messages
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(formatter)
        self._logger.addHandler(console)
    
    def _ensure_today(self):
        """Ensure logger is set up for today's date."""
        today = datetime.now().strftime("%Y-%m-%d")
        if self._current_date != today:
            self._setup_logger()
    
    def log_check_start(self, check_time: datetime):
        """Log the start of a candle check cycle."""
        self._ensure_today()
        self._logger.info("=" * 80)
        self._logger.info(f"CANDLE CHECK STARTED at {check_time.strftime('%H:%M:%S')}")
        self._logger.info("=" * 80)
    
    def log_candles_fetched(self, df: pd.DataFrame, num_candles: int):
        """Log information about fetched candles."""
        self._ensure_today()
        if df is None or len(df) == 0:
            self._logger.warning("No candles fetched - DataFrame is empty")
            return
        
        self._logger.info(f"Fetched {num_candles} candles")
        self._logger.info(f"Latest candle time: {df.iloc[-1]['timestamp']}")
    
    def log_candle_details(self, candle: Dict[str, Any], label: str = "CURRENT"):
        """Log detailed candle OHLC data."""
        self._ensure_today()
        self._logger.debug(f"--- {label} CANDLE ---")
        self._logger.debug(f"  Timestamp: {candle.get('timestamp', 'N/A')}")
        self._logger.debug(f"  Open:      {candle.get('open', 0):.2f}")
        self._logger.debug(f"  High:      {candle.get('high', 0):.2f}")
        self._logger.debug(f"  Low:       {candle.get('low', 0):.2f}")
        self._logger.debug(f"  Close:     {candle.get('close', 0):.2f}")
        
        # Calculate candle metrics
        o, h, l, c = candle.get('open', 0), candle.get('high', 0), candle.get('low', 0), candle.get('close', 0)
        rng = h - l if h != l else 1
        body = abs(c - o)
        upper_wick = h - max(o, c)
        lower_wick = min(o, c) - l
        
        self._logger.debug(f"  Range:     {rng:.2f}")
        self._logger.debug(f"  Body:      {body:.2f} ({body/rng*100:.1f}%)")
        self._logger.debug(f"  Upper Wick:{upper_wick:.2f} ({upper_wick/rng*100:.1f}%)")
        self._logger.debug(f"  Lower Wick:{lower_wick:.2f} ({lower_wick/rng*100:.1f}%)")
        self._logger.debug(f"  Color:     {'GREEN' if c > o else 'RED' if c < o else 'DOJI'}")
    
    def log_pin_bar_analysis(self, 
                             prev_candle: Dict[str, Any], 
                             curr_candle: Dict[str, Any],
                             ema_value: Optional[float] = None):
        """Log detailed pin bar analysis with all criteria checks."""
        self._ensure_today()
        
        self._logger.info("-" * 60)
        self._logger.info("PIN BAR ANALYSIS")
        self._logger.info("-" * 60)
        
        # Log both candles
        self.log_candle_details(prev_candle, "PREVIOUS")
        self.log_candle_details(curr_candle, "CURRENT")
        
        # Calculate criteria
        prev_o, prev_c = prev_candle.get('open', 0), prev_candle.get('close', 0)
        curr_o, curr_h, curr_l, curr_c = (
            curr_candle.get('open', 0), 
            curr_candle.get('high', 0), 
            curr_candle.get('low', 0), 
            curr_candle.get('close', 0)
        )
        
        rng = curr_h - curr_l if curr_h != curr_l else 1
        body = curr_c - curr_o
        upper_wick = curr_h - curr_c
        lower_wick = curr_o - curr_l
        
        # Check conditions
        prev_red = prev_c < prev_o
        curr_green = curr_c > curr_o
        upper_wick_pct = upper_wick / rng * 100
        lower_wick_pct = lower_wick / rng * 100
        close_position_pct = (curr_c - curr_l) / rng * 100
        
        is_upper_wick_ok = upper_wick_pct < 15
        is_lower_wick_ok = lower_wick_pct > 50
        is_wick_gt_body = lower_wick > body
        is_close_high = close_position_pct >= 60
        
        self._logger.info("")
        self._logger.info("CRITERIA CHECK:")
        self._logger.info(f"  [{'✓' if prev_red else '✗'}] Previous candle RED:     {prev_red}")
        self._logger.info(f"  [{'✓' if curr_green else '✗'}] Current candle GREEN:   {curr_green}")
        self._logger.info(f"  [{'✓' if is_upper_wick_ok else '✗'}] Upper wick < 15%:       {upper_wick_pct:.1f}%")
        self._logger.info(f"  [{'✓' if is_lower_wick_ok else '✗'}] Lower wick > 50%:       {lower_wick_pct:.1f}%")
        self._logger.info(f"  [{'✓' if is_wick_gt_body else '✗'}] Lower wick > body:      {lower_wick:.2f} > {body:.2f}")
        self._logger.info(f"  [{'✓' if is_close_high else '✗'}] Close in upper 40%:     {close_position_pct:.1f}%")
        
        if ema_value:
            above_ema = curr_c > ema_value
            self._logger.info(f"  [{'✓' if above_ema else '✗'}] Close > EMA(7):         {curr_c:.2f} > {ema_value:.2f}")
        
        is_pin_bar = (prev_red and curr_green and is_upper_wick_ok and 
                      is_lower_wick_ok and is_wick_gt_body and is_close_high)
        
        self._logger.info("")
        return is_pin_bar
    
    def log_time_filter(self, timestamp: datetime, in_window: bool):
        """Log time window check."""
        self._ensure_today()
        self._logger.info(f"  [{'✓' if in_window else '✗'}] In trading window:      {timestamp.strftime('%H:%M')} "
                         f"{'(11:00-12:30 or 13:30-15:30)' if in_window else '(OUTSIDE trading hours)'}")
    
    def log_decision(self, is_signal: bool, reason: str = ""):
        """Log the final trading decision."""
        self._ensure_today()
        self._logger.info("-" * 60)
        if is_signal:
            self._logger.info("🎯 DECISION: PIN BAR DETECTED - TRADE SIGNAL!")
        else:
            self._logger.info(f"❌ DECISION: NO SIGNAL - {reason}")
        self._logger.info("-" * 60)
    
    def log_trade_entry(self, entry_price: float, stop_loss: float, 
                        take_profit: float, risk: float, reward: float):
        """Log trade entry details."""
        self._ensure_today()
        self._logger.info("")
        self._logger.info("🚀 TRADE ENTRY")
        self._logger.info(f"  Entry Price:  {entry_price:.2f}")
        self._logger.info(f"  Stop Loss:    {stop_loss:.2f}")
        self._logger.info(f"  Take Profit:  {take_profit:.2f}")
        self._logger.info(f"  Risk:         {risk:.2f} points")
        self._logger.info(f"  Reward:       {reward:.2f} points")
        self._logger.info(f"  RR Ratio:     1:{reward/risk:.1f}" if risk > 0 else "  RR Ratio:     N/A")
    
    def log_trade_exit(self, exit_price: float, pnl: float, status: str):
        """Log trade exit details."""
        self._ensure_today()
        self._logger.info("")
        self._logger.info("📊 TRADE EXIT")
        self._logger.info(f"  Exit Price:   {exit_price:.2f}")
        self._logger.info(f"  Status:       {status}")
        self._logger.info(f"  P&L:          ₹{pnl:.2f} {'(PROFIT)' if pnl > 0 else '(LOSS)' if pnl < 0 else ''}")
    
    def log_error(self, error_msg: str):
        """Log error messages."""
        self._ensure_today()
        self._logger.error(f"ERROR: {error_msg}")
    
    def log_market_status(self, is_open: bool, current_time: datetime):
        """Log market status."""
        self._ensure_today()
        status = "OPEN" if is_open else "CLOSED"
        self._logger.info(f"Market Status: {status} | Time: {current_time.strftime('%H:%M:%S')}")
    
    def log_check_end(self, next_check_time: Optional[datetime] = None):
        """Log the end of a candle check cycle."""
        self._ensure_today()
        if next_check_time:
            self._logger.info(f"Next check at: {next_check_time.strftime('%H:%M:%S')}")
        self._logger.info("=" * 80)
        self._logger.info("")
    
    def log_session_start(self, mode: str, instrument: str):
        """Log trading session start."""
        self._ensure_today()
        self._logger.info("")
        self._logger.info("*" * 80)
        self._logger.info(f"TRADING SESSION STARTED")
        self._logger.info(f"Mode: {mode}")
        self._logger.info(f"Instrument: {instrument}")
        self._logger.info(f"Date: {datetime.now().strftime('%Y-%m-%d')}")
        self._logger.info("*" * 80)
        self._logger.info("")
    
    def log_session_end(self, total_signals: int, trades_executed: int):
        """Log trading session end summary."""
        self._ensure_today()
        self._logger.info("")
        self._logger.info("*" * 80)
        self._logger.info("TRADING SESSION ENDED")
        self._logger.info(f"Total Signals Detected: {total_signals}")
        self._logger.info(f"Trades Executed: {trades_executed}")
        self._logger.info("*" * 80)
    
    def get_log_file_path(self) -> Path:
        """Get the current day's log file path."""
        self._ensure_today()
        return self.LOG_DIR / f"{self._current_date}.log"


# Singleton instance
def get_trading_logger() -> TradingLogger:
    """Get the trading logger instance."""
    return TradingLogger()
