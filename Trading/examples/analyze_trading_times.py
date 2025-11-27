"""Analyze trading performance by time of day to find optimal trading windows.

This script analyzes backtest results to identify:
1. Most profitable time slots
2. Best hours to trade
3. Time periods to avoid
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

# Add paths for imports
trading_dir = Path(__file__).parent.parent
assignment_dir = trading_dir.parent

sys.path.insert(0, str(trading_dir))
sys.path.insert(0, str(assignment_dir))

from src.data import CandleDataFetcher, NIFTY_INDEX_KEY
from src.strategy import PinBarStrategy
from src.backtest import BacktestEngine
from src.utils import Logger

from UpstoxAuth.src.config import Config, Credentials
from UpstoxAuth.src.auth import TokenManager


def get_token():
    """Get authentication token."""
    creds_path = Path.home() / '.hft' / 'credentials.json'
    creds = Credentials.from_file(str(creds_path))
    config = Config(credentials=creds)
    token_manager = TokenManager(config)
    
    if token_manager.is_token_valid():
        return token_manager.get_access_token()
    return None


def analyze_by_time():
    """Analyze trade performance by time of day."""
    
    print("\n" + "=" * 80)
    print("TRADING TIME ANALYSIS - Finding Optimal Trading Windows")
    print("=" * 80)
    
    # Get data
    token = get_token()
    if not token:
        print("Error: No valid token")
        return
    
    fetcher = CandleDataFetcher(token)
    
    # Fetch 6 months data
    to_date = datetime.now() - timedelta(days=1)
    from_date = to_date - timedelta(days=180)
    
    print(f"\nFetching data from {from_date.date()} to {to_date.date()}...")
    df = fetcher.get_nifty_index_candles(
        interval=5,
        unit="minutes",
        to_date=to_date,
        from_date=from_date
    )
    
    if df is None or len(df) == 0:
        print("No data available")
        return
    
    print(f"Fetched {len(df)} candles")
    
    # Run strategy
    strategy = PinBarStrategy(risk_reward_ratio=3.0, stop_loss_buffer=5.0)
    trades = strategy.find_bullish_pin_bars(df, stock="NIFTY_FUT")
    
    print(f"Found {len(trades)} pin bar patterns")
    
    # Backtest
    engine = BacktestEngine()
    results = engine.backtest(trades, {"NIFTY_FUT": df})
    
    # Analyze by hour
    hourly_stats = defaultdict(lambda: {"wins": 0, "losses": 0, "pnl": 0.0, "trades": 0})
    
    # Analyze by 30-minute slots
    slot_stats = defaultdict(lambda: {"wins": 0, "losses": 0, "pnl": 0.0, "trades": 0})
    
    for result in results:
        if result.status not in ["HIT_TP", "HIT_SL"]:
            continue
        
        entry_time = result.trade.entry_time
        hour = entry_time.hour
        minute = entry_time.minute
        
        # Round to 30-min slot
        slot_minute = 0 if minute < 30 else 30
        slot_key = f"{hour:02d}:{slot_minute:02d}"
        
        # Update hourly stats
        hourly_stats[hour]["trades"] += 1
        hourly_stats[hour]["pnl"] += result.pnl
        if result.status == "HIT_TP":
            hourly_stats[hour]["wins"] += 1
        else:
            hourly_stats[hour]["losses"] += 1
        
        # Update slot stats
        slot_stats[slot_key]["trades"] += 1
        slot_stats[slot_key]["pnl"] += result.pnl
        if result.status == "HIT_TP":
            slot_stats[slot_key]["wins"] += 1
        else:
            slot_stats[slot_key]["losses"] += 1
    
    # Print hourly analysis
    print("\n" + "-" * 80)
    print("ANALYSIS BY HOUR")
    print("-" * 80)
    print(f"{'Hour':<8} {'Trades':<10} {'Wins':<8} {'Losses':<8} {'Win Rate':<12} {'P&L':<12}")
    print("-" * 80)
    
    profitable_hours = []
    for hour in sorted(hourly_stats.keys()):
        stats = hourly_stats[hour]
        win_rate = (stats["wins"] / stats["trades"] * 100) if stats["trades"] > 0 else 0
        print(f"{hour:02d}:00    {stats['trades']:<10} {stats['wins']:<8} {stats['losses']:<8} "
              f"{win_rate:<12.1f}% ₹{stats['pnl']:<10.2f}")
        
        if stats["pnl"] > 0:
            profitable_hours.append((hour, stats["pnl"], win_rate, stats["trades"]))
    
    # Print 30-minute slot analysis
    print("\n" + "-" * 80)
    print("ANALYSIS BY 30-MINUTE SLOTS")
    print("-" * 80)
    print(f"{'Time Slot':<12} {'Trades':<10} {'Wins':<8} {'Losses':<8} {'Win Rate':<12} {'P&L':<12}")
    print("-" * 80)
    
    profitable_slots = []
    for slot in sorted(slot_stats.keys()):
        stats = slot_stats[slot]
        win_rate = (stats["wins"] / stats["trades"] * 100) if stats["trades"] > 0 else 0
        pnl_indicator = "+" if stats["pnl"] > 0 else ""
        print(f"{slot:<12} {stats['trades']:<10} {stats['wins']:<8} {stats['losses']:<8} "
              f"{win_rate:<12.1f}% {pnl_indicator}₹{stats['pnl']:<10.2f}")
        
        if stats["pnl"] > 0 and stats["trades"] >= 5:  # Minimum 5 trades for significance
            profitable_slots.append((slot, stats["pnl"], win_rate, stats["trades"]))
    
    # Sort by P&L
    profitable_slots.sort(key=lambda x: x[1], reverse=True)
    profitable_hours.sort(key=lambda x: x[1], reverse=True)
    
    # Recommendations
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    
    print("\n📈 TOP PROFITABLE HOURS (sorted by P&L):")
    for hour, pnl, win_rate, trades in profitable_hours[:5]:
        print(f"   {hour:02d}:00 - {hour:02d}:59 → P&L: ₹{pnl:.2f}, Win Rate: {win_rate:.1f}%, Trades: {trades}")
    
    print("\n📈 TOP PROFITABLE 30-MIN SLOTS (min 5 trades):")
    for slot, pnl, win_rate, trades in profitable_slots[:5]:
        hour, minute = map(int, slot.split(':'))
        end_minute = minute + 30
        end_hour = hour if end_minute < 60 else hour + 1
        end_minute = end_minute % 60
        print(f"   {slot} - {end_hour:02d}:{end_minute:02d} → P&L: ₹{pnl:.2f}, Win Rate: {win_rate:.1f}%, Trades: {trades}")
    
    # Find losing time periods
    losing_hours = [(h, s["pnl"], s["trades"]) for h, s in hourly_stats.items() if s["pnl"] < 0]
    losing_hours.sort(key=lambda x: x[1])
    
    print("\n📉 WORST HOURS TO AVOID:")
    for hour, pnl, trades in losing_hours[:3]:
        print(f"   {hour:02d}:00 - {hour:02d}:59 → P&L: ₹{pnl:.2f}, Trades: {trades}")
    
    # Calculate optimal trading window
    if profitable_slots:
        best_slots = [s[0] for s in profitable_slots[:3]]
        print(f"\n✅ SUGGESTED OPTIMAL TRADING WINDOWS:")
        for slot in best_slots:
            hour, minute = map(int, slot.split(':'))
            end_minute = minute + 30
            end_hour = hour if end_minute < 60 else hour + 1
            end_minute = end_minute % 60
            print(f"   • {slot} to {end_hour:02d}:{end_minute:02d}")
    
    # Return optimal times for use in strategy
    optimal_times = {
        "profitable_hours": [h[0] for h in profitable_hours],
        "profitable_slots": profitable_slots,
        "avoid_hours": [h[0] for h in losing_hours],
    }
    
    return optimal_times


if __name__ == "__main__":
    analyze_by_time()
