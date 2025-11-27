"""Pin bar strategy module for NIFTY 50 Index trading."""

import pandas as pd
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from ..utils import Logger


@dataclass
class Trade:
    """Represents a trading opportunity."""
    
    stock: str
    entry_time: datetime
    entry_price: float
    stop_loss: float
    risk_reward_ratio: float = 3.5
    take_profit: float = 0.0
    risk_per_trade: float = 0.0
    reward_per_trade: float = 0.0
    
    def __post_init__(self):
        """Calculate TP based on RR ratio."""
        self.risk_per_trade = abs(self.entry_price - self.stop_loss)
        self.reward_per_trade = self.risk_per_trade * self.risk_reward_ratio
        self.take_profit = self.entry_price + self.reward_per_trade


class PinBarStrategy:
    """Bullish pin bar strategy with time and EMA(7) filters.
    
    Entry Criteria:
    - Previous candle is RED
    - Current candle is GREEN bullish pin bar
    - Price > EMA(7)
    - Within trading windows (11:00-12:30, 13:30-15:30)
    
    Exit:
    - Stop Loss: Low of pin bar - 5 points
    - Take Profit: Entry + (Risk × 3.5)
    """
    
    # Trading windows (avoid 09:00-10:59 high volatility)
    TRADING_WINDOWS = [
        (11, 0, 12, 30),   # 11:00 - 12:30
        (13, 30, 15, 30),  # 13:30 - 15:30
    ]
    
    EMA_PERIOD = 7
    
    def __init__(self, risk_reward_ratio: float = 3.5, stop_loss_buffer: float = 5.0,
                 use_time_filter: bool = True, use_ema_filter: bool = True):
        self.risk_reward_ratio = risk_reward_ratio
        self.stop_loss_buffer = stop_loss_buffer
        self.use_time_filter = use_time_filter
        self.use_ema_filter = use_ema_filter
        self.logger = Logger.get()
    
    def _add_ema(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add EMA(7) column to dataframe."""
        df = df.copy()
        df['ema_7'] = df['close'].ewm(span=self.EMA_PERIOD, adjust=False).mean()
        return df
    
    def _in_trading_window(self, ts: datetime) -> bool:
        """Check if timestamp is within trading windows."""
        if not self.use_time_filter:
            return True
        
        minutes = ts.hour * 60 + ts.minute
        for sh, sm, eh, em in self.TRADING_WINDOWS:
            if sh * 60 + sm <= minutes <= eh * 60 + em:
                return True
        return False
    
    def _is_pin_bar(self, o: float, h: float, l: float, c: float) -> bool:
        """Check if candle is a bullish pin bar.
        
        Criteria:
        - Green candle (close > open)
        - Upper wick < 15% of range
        - Lower wick > 50% of range
        - Lower wick > body
        - Close in upper 40% of candle
        """
        rng = h - l
        if rng == 0 or c <= o:
            return False
        
        body = c - o
        upper_wick = h - c
        lower_wick = o - l
        
        return (
            upper_wick / rng < 0.15 and
            lower_wick / rng > 0.50 and
            lower_wick > body and
            (c - l) / rng >= 0.60
        )
    
    def find_bullish_pin_bars(self, df: pd.DataFrame, stock: str = "NIFTY") -> List[Trade]:
        """Find bullish pin bar patterns in historical data."""
        trades = []
        
        if len(df) < 2:
            return trades
        
        df = df.sort_values("timestamp").reset_index(drop=True)
        
        if self.use_ema_filter:
            df = self._add_ema(df)
        
        for i in range(1, len(df)):
            prev = df.iloc[i - 1]
            curr = df.iloc[i]
            
            # Check all conditions
            prev_red = prev["close"] < prev["open"]
            curr_green = curr["close"] > curr["open"]
            is_pin = self._is_pin_bar(curr["open"], curr["high"], curr["low"], curr["close"])
            in_window = self._in_trading_window(curr["timestamp"])
            above_ema = (not self.use_ema_filter or 
                        'ema_7' not in df.columns or 
                        curr["close"] > df.iloc[i]['ema_7'])
            
            if prev_red and curr_green and is_pin and in_window and above_ema:
                trade = Trade(
                    stock=stock,
                    entry_time=curr["timestamp"],
                    entry_price=curr["close"],
                    stop_loss=curr["low"] - self.stop_loss_buffer,
                    risk_reward_ratio=self.risk_reward_ratio
                )
                trades.append(trade)
        
        return trades
    
    def check_live_signal(self, df: pd.DataFrame, stock: str = "NIFTY") -> Optional[Trade]:
        """Check for pin bar signal on last confirmed candle (for live trading).
        
        Uses [-3] and [-2] candles, ignoring [-1] which is still forming.
        """
        if len(df) < 3:
            return None
        
        df = df.sort_values("timestamp").reset_index(drop=True)
        
        if self.use_ema_filter:
            df = self._add_ema(df)
        
        prev = df.iloc[-3]
        curr = df.iloc[-2]
        
        prev_red = prev["close"] < prev["open"]
        curr_green = curr["close"] > curr["open"]
        is_pin = self._is_pin_bar(curr["open"], curr["high"], curr["low"], curr["close"])
        in_window = self._in_trading_window(curr["timestamp"])
        above_ema = (not self.use_ema_filter or 
                    'ema_7' not in df.columns or 
                    curr["close"] > df.iloc[-2]['ema_7'])
        
        if prev_red and curr_green and is_pin and in_window and above_ema:
            trade = Trade(
                stock=stock,
                entry_time=curr["timestamp"],
                entry_price=curr["close"],
                stop_loss=curr["low"] - self.stop_loss_buffer,
                risk_reward_ratio=self.risk_reward_ratio
            )
            self.logger.info(f"🎯 PIN BAR: Entry={trade.entry_price:.2f}, SL={trade.stop_loss:.2f}, TP={trade.take_profit:.2f}")
            return trade
        
        return None
