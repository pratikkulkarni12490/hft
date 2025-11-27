#!/usr/bin/env python3
"""
Live Trading Runner for Pin Bar Strategy on NIFTY

This script monitors NIFTY 50 Index candles in real-time and places trades
on NIFTY Futures when pin bar patterns are detected.

Architecture:
- Monitors: NIFTY 50 Index (NSE_INDEX|Nifty 50)
- Trades:   NIFTY Futures (NSE_FO|NIFTY{expiry}FUT)

Strategy Logic (shared with backtesting):
- Bullish pin bar preceded by red candle
- 1:3 Risk-Reward ratio
- Stop Loss: Low of pin bar - 5 points
- Time Filter: 11:00-12:30, 13:30-15:30

Usage:
    # Paper trading (default)
    python live_trading.py
    
    # Live trading
    python live_trading.py --live
    
    # Custom check interval
    python live_trading.py --interval 60  # Check every 60 seconds
"""

import sys
import time
import argparse
from datetime import datetime, time as dtime, timedelta
from pathlib import Path

# Add paths for imports
trading_dir = Path(__file__).parent.parent
assignment_dir = trading_dir.parent

sys.path.insert(0, str(trading_dir))
sys.path.insert(0, str(assignment_dir))

from src.data import CandleDataFetcher, NIFTY_INDEX_KEY
from src.strategy import PinBarStrategy, Trade
from src.orders import OrderPlacer, TransactionType, NIFTY_FUTURES_CURRENT
from src.utils import Logger, get_trading_logger

# Import from UpstoxAuth module
from UpstoxAuth.src.config import Config, Credentials
from UpstoxAuth.src.auth import TokenManager


# Configuration
NIFTY_FUTURES_KEY = NIFTY_FUTURES_CURRENT  # Update this for current month contract
CANDLE_INTERVAL = 5  # 5-minute candles
DEFAULT_CHECK_INTERVAL = 60  # seconds
DEFAULT_QUANTITY = 1  # Number of lots


class LiveTrader:
    """Live trading engine for NIFTY pin bar strategy."""
    
    # Market hours
    MARKET_OPEN = dtime(9, 15)
    MARKET_CLOSE = dtime(15, 30)
    
    def __init__(self, 
                 paper_trading: bool = True,
                 check_interval: int = DEFAULT_CHECK_INTERVAL,
                 quantity: int = DEFAULT_QUANTITY,
                 test_mode: bool = False):
        """Initialize live trader.
        
        Args:
            paper_trading: If True, simulates trades without sending to exchange.
            check_interval: Seconds between candle checks.
            quantity: Number of lots to trade.
            test_mode: If True, uses yesterday's historical data for testing.
        """
        self.paper_trading = paper_trading
        self.check_interval = check_interval
        self.quantity = quantity
        self.test_mode = test_mode
        self.logger = Logger.get()
        self.trading_logger = get_trading_logger()  # Detailed trading logs
        
        # Initialize components
        self._init_auth()
        self._init_components()
        
        # Track state
        self.active_trade = None
        self.trades_today = []
        self.last_signal_time = None  # Prevent duplicate signals on same candle
        
        mode = "PAPER TRADING" if paper_trading else "🔴 LIVE TRADING"
        if test_mode:
            mode = "📊 TEST MODE (Historical Data)"
        self.logger.info(f"=== {mode} ===")
        self.logger.info(f"Monitoring: {NIFTY_INDEX_KEY}")
        self.logger.info(f"Trading: {NIFTY_FUTURES_KEY}")
        self.logger.info(f"Check interval: {check_interval} seconds")
        self.logger.info(f"Quantity: {quantity} lots ({quantity * 25} units)")
        
        # Log session start to trading log file
        self.trading_logger.log_session_start(mode, NIFTY_INDEX_KEY)
        self.logger.info(f"📁 Trading logs: {self.trading_logger.get_log_file_path()}")
    
    def _init_auth(self):
        """Initialize authentication using TokenManager."""
        try:
            # Load credentials
            creds_path = Path.home() / '.hft' / 'credentials.json'
            if not creds_path.exists():
                raise RuntimeError("Credentials file not found at ~/.hft/credentials.json")
            
            creds = Credentials.from_file(str(creds_path))
            config = Config(credentials=creds)
            
            # Use TokenManager for token operations
            self.token_manager = TokenManager(config)
            
            # Check if we have a valid cached token
            if self.token_manager.is_token_valid():
                self.token = self.token_manager.get_access_token()
                token_info = self.token_manager.get_token_info()
                user_name = token_info.get('user_name', 'Unknown')
                self.logger.info(f"✅ Authentication successful for user: {user_name}")
            else:
                # No valid token, generate auth URL
                self.logger.info("No valid token found. Please authenticate:")
                auth_url = self.token_manager.get_authorization_url()
                print(f"\n[AUTH] Open this URL in your browser:\n{auth_url}\n")
                
                # Wait for auth code
                auth_code = input("[AUTH] Enter the authorization code from the redirect URL: ").strip()
                
                if not auth_code:
                    raise RuntimeError("No authorization code provided")
                
                # Exchange code for token
                self.logger.info("Exchanging code for token...")
                success = self.token_manager.exchange_code_for_token(auth_code)
                
                if success:
                    self.token = self.token_manager.get_access_token()
                    token_info = self.token_manager.get_token_info()
                    user_name = token_info.get('user_name', 'Unknown')
                    self.logger.info(f"✅ Token obtained successfully for: {user_name}")
                else:
                    raise RuntimeError("Failed to obtain token")
            
        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            raise
    
    def _init_components(self):
        """Initialize strategy, data fetcher, and order placer."""
        # Strategy with time filter (same as backtesting)
        self.strategy = PinBarStrategy(
            risk_reward_ratio=3.0,
            stop_loss_buffer=5.0,
            use_time_filter=True
        )
        
        # Data fetcher for intraday candles
        self.data_fetcher = CandleDataFetcher(auth_token=self.token)
        
        # Order placer
        self.order_placer = OrderPlacer(
            auth_token=self.token,
            paper_trading=self.paper_trading
        )
    
    def is_market_hours(self) -> bool:
        """Check if current time is within market hours."""
        now = datetime.now().time()
        return self.MARKET_OPEN <= now <= self.MARKET_CLOSE
    
    def fetch_latest_candles(self):
        """Fetch latest intraday candles from NIFTY Index."""
        try:
            if self.test_mode:
                # In test mode, use last week's historical data
                # This gives more chances to find a pin bar signal
                yesterday = datetime.now() - timedelta(days=1)
                df = self.data_fetcher.get_nifty_index_candles(
                    interval=CANDLE_INTERVAL,
                    unit="minutes",
                    to_date=yesterday,
                    from_date=yesterday - timedelta(days=7)
                )
                if df is not None and len(df) > 0:
                    self.logger.info(f"[TEST] Fetched {len(df)} historical candles (last 7 days)")
            else:
                # In live mode, use intraday API
                df = self.data_fetcher.get_nifty_index_intraday(
                    interval=CANDLE_INTERVAL
                )
            
            if df is None or df.empty:
                self.logger.warning("No candle data received")
                self.trading_logger.log_error("No data from API")
                return None
            
            self.logger.debug(f"Fetched {len(df)} candles, latest: {df.iloc[-1]['timestamp']}")
            return df
            
        except Exception as e:
            self.logger.error(f"Error fetching candles: {e}")
            self.trading_logger.log_error(f"Error fetching candles: {e}")
            return None
    
    def check_for_signal(self, df) -> Trade:
        """Check latest candles for pin bar signal.
        
        Returns:
            Trade object if signal detected, None otherwise.
        """
        if df is None or len(df) < 3:
            return None
        
        # Log candle check and get candle data
        prev_candle, curr_candle = self.trading_logger.log_candle_check(df)
        
        if prev_candle is None or curr_candle is None:
            return None
        
        # Calculate pin bar metrics for logging
        rng = curr_candle['high'] - curr_candle['low'] if curr_candle['high'] != curr_candle['low'] else 1
        lower_wick_pct = ((min(curr_candle['open'], curr_candle['close']) - curr_candle['low']) / rng) * 100
        
        # Check conditions
        prev_red = prev_candle['close'] < prev_candle['open']
        curr_green = curr_candle['close'] > curr_candle['open']
        in_window = self.strategy._in_trading_window(curr_candle['timestamp'])
        
        # Calculate EMA check
        above_ema = True
        if self.strategy.use_ema_filter:
            df_sorted = df.sort_values("timestamp").reset_index(drop=True)
            df_sorted['ema_7'] = df_sorted['close'].ewm(span=7, adjust=False).mean()
            above_ema = curr_candle['close'] > df_sorted.iloc[-2]['ema_7']
        
        # Use the strategy's check method
        trade = self.strategy.check_live_signal(df, stock="NIFTY")
        
        # Determine reason for no signal
        reason = ""
        if not prev_red:
            reason = "prev candle not red"
        elif not curr_green:
            reason = "curr candle not green"
        elif lower_wick_pct <= 50:
            reason = f"wick {lower_wick_pct:.0f}% < 50%"
        elif not in_window:
            reason = "outside trading window"
        elif not above_ema:
            reason = "below EMA(7)"
        elif not trade:
            reason = "pin bar criteria not met"
        
        # Log result
        is_valid = trade is not None
        self.trading_logger.log_pin_bar_result(is_valid, in_window, above_ema, lower_wick_pct, reason)
        
        if trade:
            # Check if this is a new signal (not the same candle as before)
            if self.last_signal_time == trade.entry_time:
                self.logger.debug("Signal already processed for this candle")
                return None
            self.last_signal_time = trade.entry_time
        
        return trade
    
    def execute_trade(self, trade: Trade):
        """Execute a trade based on detected signal.
        
        Args:
            trade: Trade object with entry, SL, and TP levels.
        """
        # Check if we already have an active trade
        if self.active_trade:
            self.logger.warning("Already have an active trade, skipping new signal")
            return
        
        # Log trade signal to journal
        self.trading_logger.log_trade_signal(
            entry=trade.entry_price,
            sl=trade.stop_loss,
            tp=trade.take_profit,
            risk=trade.risk_per_trade
        )
        
        # Place bracket order (entry + SL + TP)
        results = self.order_placer.place_bracket_order(
            instrument_token=NIFTY_FUTURES_KEY,
            quantity=self.quantity,
            entry_price=trade.entry_price,
            stop_loss=trade.stop_loss,
            take_profit=trade.take_profit,
            transaction_type=TransactionType.BUY
        )
        
        # Log order results to journal
        for order_type, response in results.items():
            self.trading_logger.log_order_status(
                order_type.upper(), 
                response.success, 
                response.order_id or ""
            )
        
        # Track trade
        if results.get("entry", {}).success:
            self.active_trade = {
                "trade": trade,
                "orders": results,
                "entry_time": datetime.now()
            }
            self.trades_today.append(self.active_trade)
    
    def run_once(self):
        """Run one iteration of the trading loop."""
        # Check market status
        if not self.is_market_hours():
            self.trading_logger.log_market_status(False)
            return
        
        # Fetch latest candles
        df = self.fetch_latest_candles()
        
        if df is None:
            return
        
        if self.test_mode:
            # In test mode, scan ALL candles for pin bars (for validation)
            trades = self.strategy.find_bullish_pin_bars(df, "NIFTY")
            if trades:
                self.logger.info(f"[TEST] Found {len(trades)} pin bar signals in historical data:")
                for i, trade in enumerate(trades, 1):
                    self.logger.info(
                        f"  {i}. {trade.entry_time}: Entry={trade.entry_price:.2f}, "
                        f"SL={trade.stop_loss:.2f}, TP={trade.take_profit:.2f}"
                    )
                    # Execute the last trade as a demonstration
                    if i == len(trades):
                        self.logger.info("Executing the most recent signal...")
                        self.execute_trade(trade)
            else:
                self.logger.info("[TEST] No pin bar signals found in historical data")
        else:
            # In live mode, check only the latest candle
            trade = self.check_for_signal(df)
            if trade:
                self.execute_trade(trade)
    
    def run(self):
        """Main trading loop."""
        self.logger.info("Starting live trading loop...")
        self.logger.info(f"Press Ctrl+C to stop")
        
        try:
            while True:
                now = datetime.now()
                
                # Check if market is open
                if not self.is_market_hours():
                    self.logger.info(f"Market closed. Current time: {now.strftime('%H:%M:%S')}")
                    
                    # If before market open, wait until open
                    if now.time() < self.MARKET_OPEN:
                        wait_time = 60  # Check every minute before market open
                    else:
                        # Market closed for the day
                        self.logger.info("Market closed for the day. Exiting.")
                        break
                else:
                    # Run trading logic
                    self.run_once()
                    wait_time = self.check_interval
                
                # Wait before next check
                time.sleep(wait_time)
                
        except KeyboardInterrupt:
            self.logger.info("\n\n🛑 Trading stopped by user")
        finally:
            self.print_summary()
    
    def print_summary(self):
        """Print summary of trading session."""
        self.logger.info("\n" + "=" * 60)
        self.logger.info("📊 TRADING SESSION SUMMARY")
        self.logger.info("=" * 60)
        
        total_signals = len(self.trades_today)
        self.logger.info(f"Total signals detected: {total_signals}")
        
        trades_executed = 0
        if self.paper_trading:
            paper_trades = self.order_placer.get_paper_trades()
            trades_executed = len(paper_trades)
            self.logger.info(f"Paper orders placed: {trades_executed}")
            
            if paper_trades:
                self.logger.info("\nPaper Trade Details:")
                for i, pt in enumerate(paper_trades, 1):
                    self.logger.info(
                        f"  {i}. {pt['transaction_type']} {pt['quantity']} @ {pt['order_type']} "
                        f"(Trigger: {pt.get('trigger_price', 'N/A')})"
                    )
        
        self.logger.info("=" * 60)
        self.logger.info(f"📁 Trading logs saved to: {self.trading_logger.get_log_file_path()}")
        
        # Log session end to trading log
        self.trading_logger.log_session_end(total_signals, trades_executed)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Live trading runner for NIFTY pin bar strategy"
    )
    
    parser.add_argument(
        "--live",
        action="store_true",
        help="Enable live trading (default is paper trading)"
    )
    
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_CHECK_INTERVAL,
        help=f"Check interval in seconds (default: {DEFAULT_CHECK_INTERVAL})"
    )
    
    parser.add_argument(
        "--quantity",
        type=int,
        default=DEFAULT_QUANTITY,
        help=f"Number of lots to trade (default: {DEFAULT_QUANTITY})"
    )
    
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run only once (for testing)"
    )
    
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test mode: use yesterday's historical data instead of live data"
    )
    
    args = parser.parse_args()
    
    # Safety check for live trading
    if args.live:
        print("\n" + "⚠️ " * 20)
        print("WARNING: You are about to enable LIVE TRADING!")
        print("Real money will be at risk.")
        print("⚠️ " * 20 + "\n")
        
        confirm = input("Type 'CONFIRM' to proceed with live trading: ")
        if confirm != "CONFIRM":
            print("Live trading cancelled.")
            return
    
    # Initialize and run trader
    trader = LiveTrader(
        paper_trading=not args.live,
        check_interval=args.interval,
        quantity=args.quantity,
        test_mode=args.test
    )
    
    if args.once:
        trader.run_once()
        trader.print_summary()
    else:
        trader.run()


if __name__ == "__main__":
    main()
