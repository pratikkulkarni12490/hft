"""NIFTY Futures Pin Bar Trading Strategy - Backtest Mode.

This script:
1. Checks for valid access token, generates auth URL if invalid
2. Fetches last 7 days of 5-minute NIFTY futures data
3. Identifies green pin bar patterns preceded by red candles
4. Backtests with 1:3 RR ratio (risk = low - 5 points)
"""

import sys
import time
from pathlib import Path
from datetime import datetime, timedelta

# Add paths for imports
trading_dir = Path(__file__).parent.parent
assignment_dir = trading_dir.parent

sys.path.insert(0, str(trading_dir))
sys.path.insert(0, str(assignment_dir))

from src.data import CandleDataFetcher, NIFTY_INDEX_KEY
from src.strategy import PinBarStrategy
from src.backtest import BacktestEngine
from src.utils import Logger

# Import from UpstoxAuth module
from UpstoxAuth.src.config import Config, Credentials
from UpstoxAuth.src.auth import TokenManager


def setup_logging():
    """Set up logging configuration."""
    log_file = Path.home() / ".trading" / "logs" / "trading.log"
    Logger.setup(log_file=log_file, level="DEBUG")
    return Logger.get()


def authenticate():
    """Handle authentication with token management.
    
    Returns:
        tuple: (token, user_name) if successful, (None, None) if failed
    """
    print("\n[AUTH] Checking authentication status...")
    
    try:
        # Load credentials
        creds_path = Path.home() / '.hft' / 'credentials.json'
        if not creds_path.exists():
            print("[AUTH] ✗ Credentials file not found at ~/.hft/credentials.json")
            return None, None
        
        creds = Credentials.from_file(str(creds_path))
        config = Config(credentials=creds)
        
        # Use TokenManager for token operations
        token_manager = TokenManager(config)
        
        # Check if we have a valid cached token
        if token_manager.is_token_valid():
            token = token_manager.get_access_token()
            token_info = token_manager.get_token_info()
            user_name = token_info.get('user_name', 'Unknown')
            print(f"[AUTH] ✓ Using cached token for user: {user_name}")
            return token, user_name
        
        # No valid token, generate auth URL
        print("[AUTH] ✗ No valid token found. Please authenticate:")
        auth_url = token_manager.get_authorization_url()
        print(f"\n[AUTH] Open this URL in your browser:\n{auth_url}\n")
        
        # Wait for auth code
        auth_code = input("[AUTH] Enter the authorization code from the redirect URL: ").strip()
        
        if not auth_code:
            print("[AUTH] ✗ No authorization code provided")
            return None, None
        
        # Exchange code for token
        print("[AUTH] Exchanging code for token...")
        success = token_manager.exchange_code_for_token(auth_code)
        
        if success:
            token = token_manager.get_access_token()
            token_info = token_manager.get_token_info()
            user_name = token_info.get('user_name', 'Unknown')
            print(f"[AUTH] ✓ Token obtained successfully for: {user_name}")
            return token, user_name
        else:
            print("[AUTH] ✗ Failed to obtain token")
            return None, None
    
    except Exception as e:
        print(f"[AUTH] ✗ Authentication error: {str(e)}")
        return None, None


def fetch_nifty_futures_data(token, logger):
    """Fetch NIFTY 50 Index data for the last 6 months.
    
    Args:
        token: Upstox API token
        logger: Logger instance
    
    Returns:
        DataFrame with OHLC data or None
    """
    print("\n[DATA] Fetching NIFTY 50 Index 5-minute candle data (last 6 months)...")
    
    try:
        fetcher = CandleDataFetcher(token)
        
        # Fetch last 6 months of data
        to_date = datetime.now() - timedelta(days=1)  # Yesterday
        from_date = to_date - timedelta(days=180)
        
        df = fetcher.get_nifty_index_candles(
            interval=5,
            unit="minutes",
            to_date=to_date,
            from_date=from_date
        )
        
        if df is not None and len(df) > 0:
            print(f"[DATA] ✓ Fetched {len(df)} candles")
            print(f"[DATA]   Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
            return df
        else:
            print("[DATA] ✗ No data available")
            return None
    
    except Exception as e:
        print(f"[DATA] ✗ Error fetching data: {str(e)}")
        logger.error(f"Data fetch error: {str(e)}")
        return None


def identify_trades(df, logger):
    """Identify pin bar trading opportunities.
    
    Args:
        df: DataFrame with OHLC data
        logger: Logger instance
    
    Returns:
        List of Trade objects
    """
    print("\n[STRATEGY] Scanning for green pin bar patterns...")
    
    try:
        # Initialize strategy with 1:3 RR, 5-point buffer, and time filtering
        # Time filter: Only trade during optimal windows (11:00-12:30, 13:30-15:30)
        strategy = PinBarStrategy(
            risk_reward_ratio=3.0, 
            stop_loss_buffer=5.0,
            use_time_filter=True  # Enable time-based filtering
        )
        
        # Find pin bar patterns
        trades = strategy.find_bullish_pin_bars(df, stock="NIFTY_FUT")
        
        print(f"[STRATEGY] ✓ Found {len(trades)} pin bar patterns (with time filter)")
        
        return trades
    
    except Exception as e:
        print(f"[STRATEGY] ✗ Error scanning: {str(e)}")
        logger.error(f"Strategy error: {str(e)}")
        return []


def run_backtest(trades, df, logger):
    """Run backtest on identified trades.
    
    Args:
        trades: List of Trade objects
        df: DataFrame with OHLC data
        logger: Logger instance
    
    Returns:
        Tuple of (results, summary)
    """
    print("\n[BACKTEST] Running backtest on identified trades...")
    
    try:
        engine = BacktestEngine()
        
        # Run backtest
        results = engine.backtest(trades, {"NIFTY_FUT": df})
        summary = engine.calculate_summary(results)
        
        print(f"[BACKTEST] ✓ Completed backtest for {len(trades)} trades")
        
        return results, summary
    
    except Exception as e:
        print(f"[BACKTEST] ✗ Error: {str(e)}")
        logger.error(f"Backtest error: {str(e)}")
        return [], {}


def display_results(trades, results, summary):
    """Display trading results."""
    print("\n" + "=" * 90)
    print("NIFTY FUTURES PIN BAR STRATEGY - BACKTEST RESULTS")
    print("=" * 90)
    
    print(f"\nStrategy Parameters:")
    print(f"  • Instrument: NIFTY 50 Index ({NIFTY_INDEX_KEY})")
    print(f"  • Timeframe: 5-minute candles")
    print(f"  • Risk:Reward: 1:3")
    print(f"  • Stop Loss: Low of pin bar - 5 points")
    print(f"  • Time Filter: 11:00-12:30, 13:30-15:30 (avoid opening volatility)")
    
    if not trades:
        print("\nNo pin bar patterns found in the data.")
        return
    
    print("\n" + "-" * 90)
    print("IDENTIFIED TRADES:")
    print("-" * 90)
    print(f"{'Entry Time':<22} {'Entry':<12} {'Stop Loss':<12} {'Target':<12} {'Risk':<10}")
    print("-" * 90)
    
    for trade in trades:
        print(f"{str(trade.entry_time):<22} "
              f"{trade.entry_price:<12.2f} "
              f"{trade.stop_loss:<12.2f} "
              f"{trade.take_profit:<12.2f} "
              f"{trade.risk_per_trade:<10.2f}")
    
    if results:
        print("\n" + "-" * 90)
        print("BACKTEST OUTCOMES:")
        print("-" * 90)
        print(f"{'Entry Time':<22} {'Entry':<10} {'Exit':<10} {'Status':<16} {'P&L':<12}")
        print("-" * 90)
        
        for result in results:
            if result.status == "HIT_TP":
                status_icon = "✓"
                status_display = "HIT_TP"
            elif result.status == "HIT_SL":
                status_icon = "✗"
                status_display = "HIT_SL"
            else:
                status_icon = "?"
                status_display = result.status
            
            exit_price = f"{result.exit_price:.2f}" if result.exit_price else "N/A"
            print(f"{str(result.trade.entry_time):<22} "
                  f"{result.trade.entry_price:<10.2f} "
                  f"{exit_price:<10} "
                  f"{status_icon} {status_display:<14} "
                  f"₹{result.pnl:<10.2f}")
    
    if summary:
        print("\n" + "=" * 90)
        print("SUMMARY STATISTICS")
        print("=" * 90)
        print(f"  Total Trades:      {summary.get('total_trades', 0)}")
        print(f"  Winning Trades:    {summary.get('winning_trades', 0)}")
        print(f"  Losing Trades:     {summary.get('losing_trades', 0)}")
        print(f"  Pending Trades:    {summary.get('pending_trades', 0)}")
        print(f"  Win Rate:          {summary.get('win_rate', 0)}%")
        print(f"  Total P&L:         ₹{summary.get('total_pnl', 0):.2f}")
        print(f"  Profit Factor:     {summary.get('profit_factor', 0):.2f}")
    
    print("=" * 90 + "\n")


def run_strategy():
    """Execute one cycle of the strategy."""
    logger = setup_logging()
    
    # Step 1: Authenticate
    token, user_name = authenticate()
    if not token:
        return False
    
    # Step 2: Fetch data
    df = fetch_nifty_futures_data(token, logger)
    if df is None or len(df) == 0:
        return False
    
    # Step 3: Identify trades
    trades = identify_trades(df, logger)
    
    # Step 4: Backtest
    results, summary = run_backtest(trades, df, logger)
    
    # Step 5: Display results
    display_results(trades, results, summary)
    
    return True


def main():
    """Main entry point - runs strategy every 5 minutes."""
    print("\n" + "╔" + "=" * 68 + "╗")
    print("║" + " " * 12 + "NIFTY FUTURES PIN BAR STRATEGY (BACKTEST)" + " " * 15 + "║")
    print("╚" + "=" * 68 + "╝")
    
    # Check if running in continuous mode
    continuous_mode = "--continuous" in sys.argv or "-c" in sys.argv
    
    if continuous_mode:
        print("\n[MODE] Running in continuous mode (every 5 minutes)")
        print("[MODE] Press Ctrl+C to stop\n")
        
        while True:
            try:
                run_strategy()
                print(f"\n[WAIT] Next execution in 5 minutes... ({datetime.now().strftime('%H:%M:%S')})")
                time.sleep(300)  # 5 minutes
            except KeyboardInterrupt:
                print("\n[EXIT] Strategy stopped by user")
                break
            except Exception as e:
                print(f"\n[ERROR] {str(e)}")
                print("[WAIT] Retrying in 5 minutes...")
                time.sleep(300)
    else:
        # Single execution mode
        print("\n[MODE] Single execution mode")
        print("[MODE] Use --continuous or -c for 5-minute intervals\n")
        run_strategy()
        print("\n[DONE] Strategy execution completed")


if __name__ == "__main__":
    main()
