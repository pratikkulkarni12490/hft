"""Trading Journal Logger - Clean, minimal logging for trading analysis.

Generates daily journal files at: ~/trading_logs/YYYY-MM-DD.log
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import pandas as pd


class TradingLogger:
    """Trading journal logger - minimal but important information."""
    
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
        self._check_count = 0
        self._signal_count = 0
        self._setup_logger()
    
    def _setup_logger(self):
        """Setup or rotate the logger for the current day."""
        today = datetime.now().strftime("%Y-%m-%d")
        
        if self._current_date == today and self._logger:
            return
        
        if self._file_handler and self._logger:
            self._logger.removeHandler(self._file_handler)
        
        self._current_date = today
        self._check_count = 0
        self._signal_count = 0
        log_file = self.LOG_DIR / f"{today}.log"
        
        self._logger = logging.getLogger("TradingJournal")
        self._logger.setLevel(logging.DEBUG)
        self._logger.handlers = []
        
        self._file_handler = logging.FileHandler(log_file, mode='a')
        self._file_handler.setLevel(logging.DEBUG)
        self._file_handler.setFormatter(logging.Formatter('%(message)s'))
        self._logger.addHandler(self._file_handler)
        
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(logging.Formatter('%(message)s'))
        self._logger.addHandler(console)
    
    def _ensure_today(self):
        """Ensure logger is set up for today's date."""
        today = datetime.now().strftime("%Y-%m-%d")
        if self._current_date != today:
            self._setup_logger()
    
    def _log(self, msg: str, level: str = "info"):
        """Write to log."""
        self._ensure_today()
        getattr(self._logger, level)(msg)
    
    def log_session_start(self, mode: str, instrument: str):
        """Log session start."""
        self._log("")
        self._log("╔════════════════════════════════════════════════════════════╗")
        self._log(f"║  TRADING JOURNAL - {datetime.now().strftime('%A, %d %B %Y'):<36}  ║")
        self._log("╠════════════════════════════════════════════════════════════╣")
        self._log(f"║  Mode:       {mode:<43}  ║")
        self._log(f"║  Instrument: {instrument:<43}  ║")
        self._log(f"║  Started:    {datetime.now().strftime('%H:%M:%S'):<43}  ║")
        self._log("╚════════════════════════════════════════════════════════════╝")
        self._log("")
    
    def log_candle_check(self, df: pd.DataFrame):
        """Log a candle check with current market snapshot."""
        self._ensure_today()
        self._check_count += 1
        
        if df is None or len(df) < 2:
            self._log(f"[{datetime.now().strftime('%H:%M')}] ⚠️  No data available")
            return None, None
        
        df_sorted = df.sort_values("timestamp").reset_index(drop=True)
        prev = df_sorted.iloc[-3] if len(df_sorted) >= 3 else None
        curr = df_sorted.iloc[-2]  # Last closed candle
        
        time_str = datetime.now().strftime('%H:%M')
        candle_time = curr['timestamp'].strftime('%H:%M') if hasattr(curr['timestamp'], 'strftime') else str(curr['timestamp'])[-8:-3]
        
        prev_color = "🔴" if prev is not None and prev['close'] < prev['open'] else "🟢"
        curr_color = "🟢" if curr['close'] > curr['open'] else "🔴"
        
        self._log(f"[{time_str}] #{self._check_count:03d} │ {candle_time} │ {prev_color}→{curr_color} │ "
                  f"O:{curr['open']:.0f} H:{curr['high']:.0f} L:{curr['low']:.0f} C:{curr['close']:.0f}")
        
        return prev.to_dict() if prev is not None else None, curr.to_dict()
    
    def log_pin_bar_result(self, is_pin_bar: bool, in_window: bool, above_ema: bool,
                           lower_wick_pct: float, reason: str = ""):
        """Log pin bar analysis result in one compact line."""
        self._ensure_today()
        
        if is_pin_bar and in_window and above_ema:
            self._log(f"         └─ ✅ PIN BAR! Wick:{lower_wick_pct:.0f}%")
            return True
        else:
            self._log(f"         └─ ❌ {reason}")
            return False
    
    def log_trade_signal(self, entry: float, sl: float, tp: float, risk: float):
        """Log when a trade signal is generated."""
        self._ensure_today()
        self._signal_count += 1
        
        self._log("")
        self._log("  ┌─────────────────────────────────────────┐")
        self._log(f"  │  🎯 SIGNAL #{self._signal_count:<3}  {datetime.now().strftime('%H:%M:%S'):<21}  │")
        self._log("  ├─────────────────────────────────────────┤")
        self._log(f"  │  Entry:     ₹{entry:>8.2f}                 │")
        self._log(f"  │  Stop Loss: ₹{sl:>8.2f}  ({entry-sl:>+.0f} pts)       │")
        self._log(f"  │  Target:    ₹{tp:>8.2f}  ({tp-entry:>+.0f} pts)       │")
        self._log(f"  │  Risk:Reward = 1:{(tp-entry)/risk:.1f}                   │")
        self._log("  └─────────────────────────────────────────┘")
        self._log("")
    
    def log_order_status(self, order_type: str, success: bool, order_id: str = ""):
        """Log order execution status."""
        self._ensure_today()
        status = "✅" if success else "❌"
        self._log(f"         {status} {order_type}: {'OK' if success else 'FAILED'} {f'(#{order_id})' if order_id else ''}")
    
    def log_trade_exit(self, exit_price: float, pnl: float, status: str):
        """Log trade exit."""
        self._ensure_today()
        emoji = "💰" if pnl > 0 else "📉" if pnl < 0 else "➖"
        self._log("")
        self._log(f"  {emoji} EXIT: {status} @ ₹{exit_price:.2f} │ P&L: ₹{pnl:+.2f}")
        self._log("")
    
    def log_market_status(self, is_open: bool, current_time: datetime = None):
        """Log market status."""
        self._ensure_today()
        if not is_open:
            self._log(f"[{datetime.now().strftime('%H:%M')}] 🔒 Market closed")
    
    def log_error(self, msg: str):
        """Log error."""
        self._log(f"[{datetime.now().strftime('%H:%M')}] ⚠️  {msg}")
    
    def log_session_end(self, total_signals: int, trades_executed: int):
        """Log session end summary."""
        self._ensure_today()
        self._log("")
        self._log("╔════════════════════════════════════════════════════════════╗")
        self._log("║  SESSION SUMMARY                                           ║")
        self._log("╠════════════════════════════════════════════════════════════╣")
        self._log(f"║  Ended:          {datetime.now().strftime('%H:%M:%S'):<39}  ║")
        self._log(f"║  Candle Checks:  {self._check_count:<39}  ║")
        self._log(f"║  Signals Found:  {total_signals:<39}  ║")
        self._log(f"║  Trades Placed:  {trades_executed:<39}  ║")
        self._log("╚════════════════════════════════════════════════════════════╝")
        self._log("")
    
    def get_log_file_path(self) -> Path:
        """Get current log file path."""
        self._ensure_today()
        return self.LOG_DIR / f"{self._current_date}.log"


def get_trading_logger() -> TradingLogger:
    """Get the trading logger instance."""
    return TradingLogger()
