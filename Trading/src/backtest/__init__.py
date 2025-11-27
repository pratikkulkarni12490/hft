"""Backtesting engine for strategy evaluation."""

import pandas as pd
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
from ..strategy import Trade


@dataclass
class BacktestResult:
    """Results of a backtest trade."""
    
    trade: Trade
    exit_time: Optional[datetime] = None
    exit_price: float = 0.0
    status: str = "PENDING"  # HIT_TP, HIT_SL, PENDING
    pnl: float = 0.0


class BacktestEngine:
    """Engine for backtesting trading strategies."""
    
    NIFTY_LOT_SIZE = 25
    
    def backtest(self, trades: List[Trade], data: Dict[str, pd.DataFrame]) -> List[BacktestResult]:
        """Backtest trades against historical data.
        
        Args:
            trades: List of Trade objects.
            data: Dictionary {stock: DataFrame with OHLC}.
        
        Returns:
            List of BacktestResult objects.
        """
        results = []
        
        for trade in trades:
            if trade.stock not in data:
                results.append(BacktestResult(trade=trade, status="NO_DATA"))
                continue
            
            df = data[trade.stock]
            future = df[df["timestamp"] > trade.entry_time].reset_index(drop=True)
            
            if len(future) == 0:
                results.append(BacktestResult(trade=trade, status="NO_FUTURE_DATA"))
                continue
            
            result = self._process_trade(trade, future)
            results.append(result)
        
        return results
    
    def _process_trade(self, trade: Trade, df: pd.DataFrame) -> BacktestResult:
        """Process single trade against price data."""
        for _, candle in df.iterrows():
            # Check TP hit
            if candle["high"] >= trade.take_profit:
                return BacktestResult(
                    trade=trade,
                    exit_time=candle["timestamp"],
                    exit_price=trade.take_profit,
                    status="HIT_TP",
                    pnl=trade.reward_per_trade * self.NIFTY_LOT_SIZE
                )
            
            # Check SL hit
            if candle["low"] <= trade.stop_loss:
                return BacktestResult(
                    trade=trade,
                    exit_time=candle["timestamp"],
                    exit_price=trade.stop_loss,
                    status="HIT_SL",
                    pnl=-trade.risk_per_trade * self.NIFTY_LOT_SIZE
                )
        
        # Trade not closed
        return BacktestResult(
            trade=trade,
            exit_time=df.iloc[-1]["timestamp"],
            exit_price=df.iloc[-1]["close"],
            status="PENDING",
            pnl=(df.iloc[-1]["close"] - trade.entry_price) * self.NIFTY_LOT_SIZE
        )
    
    def summary(self, results: List[BacktestResult]) -> dict:
        """Calculate summary statistics."""
        closed = [r for r in results if r.status in ["HIT_TP", "HIT_SL"]]
        wins = [r for r in results if r.status == "HIT_TP"]
        losses = [r for r in results if r.status == "HIT_SL"]
        
        total_pnl = sum(r.pnl for r in closed)
        win_rate = len(wins) / len(closed) * 100 if closed else 0
        
        return {
            "total_trades": len(results),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(win_rate, 2),
            "gross_pnl": round(total_pnl, 2),
            "avg_pnl": round(total_pnl / len(closed), 2) if closed else 0
        }
