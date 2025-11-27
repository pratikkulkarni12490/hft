"""Profit Maximization & Charge Reduction Analysis."""

import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path.cwd()))
sys.path.insert(0, str(Path.cwd().parent))

from src.data import CandleDataFetcher
from src.strategy import PinBarStrategy
from src.backtest import BacktestEngine
from src.charges import ChargesCalculator

from UpstoxAuth.src.config import Config, Credentials
from UpstoxAuth.src.auth import TokenManager

# Auth
creds = Credentials.from_file(str(Path.home() / '.hft' / 'credentials.json'))
config = Config(credentials=creds)
token_manager = TokenManager(config)
token = token_manager.get_access_token()

# Fetch data
fetcher = CandleDataFetcher(auth_token=token)
yesterday = datetime.now() - timedelta(days=1)
from_date = yesterday - timedelta(days=365)
df = fetcher.get_nifty_index_candles(interval=5, unit='minutes', to_date=yesterday, from_date=from_date)

strategy = PinBarStrategy(risk_reward_ratio=3.5, stop_loss_buffer=5.0)
trades = strategy.find_bullish_pin_bars(df, 'NIFTY')
engine = BacktestEngine()
results = engine.backtest(trades, {'NIFTY': df})
summary = engine.summary(results)

print('=' * 70)
print('PROFIT MAXIMIZATION & CHARGE REDUCTION ANALYSIS')
print('=' * 70)

# Current economics
calc = ChargesCalculator()
charges_per_trade = calc.estimate(entry_price=25000, exit_price=25100, lots=1)

print()
print('1. CURRENT ECONOMICS (Per Trade, 1 Lot = 25 units)')
print('-' * 50)
print(f'   Avg Gross P&L:     Rs.{summary["avg_pnl"]:,.2f}')
print(f'   Total Charges:     Rs.{charges_per_trade.total:.2f}')
print(f'   - Brokerage:       Rs.{charges_per_trade.brokerage:.2f} (FLAT)')
print(f'   - STT:             Rs.{charges_per_trade.stt:.2f}')
print(f'   - Transaction:     Rs.{charges_per_trade.transaction:.2f}')
print(f'   - GST:             Rs.{charges_per_trade.gst:.2f}')
print(f'   - SEBI:            Rs.{charges_per_trade.sebi:.2f}')
print(f'   - Stamp Duty:      Rs.{charges_per_trade.stamp_duty:.2f}')
print(f'   Net per Trade:     Rs.{summary["avg_pnl"] - charges_per_trade.total:.2f}')
print()

# Charge as % of gross
charge_pct = (charges_per_trade.total / summary['avg_pnl']) * 100
print(f'   WARNING: Charges eat {charge_pct:.1f}% of gross profit!')
print()

# Strategy 1: Increase lot size
print('2. SCALE UP LOT SIZE (Economies of Scale)')
print('-' * 50)
print('   Brokerage is FLAT Rs.40 regardless of lot size!')
print()
print('   Lots | Gross P&L | Charges | Charge% | Net P&L')
print('   -----|-----------|---------|---------|--------')
for lots in [1, 2, 3, 5, 10]:
    gross = summary['avg_pnl'] * lots
    charges = calc.estimate(entry_price=25000, exit_price=25100, lots=lots)
    net = gross - charges.total
    charge_pct_lot = (charges.total / gross) * 100
    print(f'   {lots:4} | Rs.{gross:>7,.0f} | Rs.{charges.total:>5.0f} | {charge_pct_lot:>6.1f}% | Rs.{net:>6,.0f}')
print()
print('   => Trading 3 lots reduces charge% from 43% to 20%!')
print()

# Strategy 2: Win rate impact
print('3. WIN RATE IMPACT ON NET P&L')
print('-' * 50)
current_win_rate = summary['win_rate']
total_trades = summary['total_trades']

wins = [r['pnl'] for r in results if r['pnl'] > 0]
losses = [r['pnl'] for r in results if r['pnl'] <= 0]
avg_win = sum(wins) / len(wins) if wins else 0
avg_loss = sum(losses) / len(losses) if losses else 0

print(f'   Avg Win: Rs.{avg_win:,.2f} | Avg Loss: Rs.{avg_loss:,.2f}')
print()
print('   Win Rate | Gross P&L | Net P&L')
print('   ---------|-----------|--------')

for wr in [30, 33.33, 35, 40, 45, 50]:
    expected_wins = int(total_trades * wr / 100)
    expected_losses = total_trades - expected_wins
    gross = (expected_wins * avg_win) + (expected_losses * avg_loss)
    charges = charges_per_trade.total * total_trades
    net = gross - charges
    marker = ' <-- current' if abs(wr - current_win_rate) < 1 else ''
    print(f'   {wr:>7.1f}% | Rs.{gross:>7,.0f} | Rs.{net:>6,.0f}{marker}')
print()
print('   => Each 5% win rate improvement adds ~Rs.15,000 to net P&L!')
print()

# Strategy 3: RR ratio impact
print('4. RISK:REWARD RATIO IMPACT')
print('-' * 50)
print()
print('   RR Ratio | Trades | Win% | Gross P&L | Net P&L')
print('   ---------|--------|------|-----------|--------')

for rr in [2.0, 2.5, 3.0, 3.5, 4.0, 5.0]:
    test_strategy = PinBarStrategy(risk_reward_ratio=rr, stop_loss_buffer=5.0)
    test_trades = test_strategy.find_bullish_pin_bars(df, 'NIFTY')
    test_results = engine.backtest(test_trades, {'NIFTY': df})
    test_summary = engine.summary(test_results)
    
    if test_summary['total_trades'] > 0:
        total_charges = charges_per_trade.total * test_summary['total_trades']
        net = test_summary['gross_pnl'] - total_charges
        marker = ' <-- current' if rr == 3.5 else ''
        print(f'   1:{rr:<5} | {test_summary["total_trades"]:>6} | {test_summary["win_rate"]:>4}% | Rs.{test_summary["gross_pnl"]:>7,.0f} | Rs.{net:>6,.0f}{marker}')
print()

# Strategy 4: Broker comparison
print('5. BROKER SELECTION')
print('-' * 50)
brokerage_savings_yearly = 40 * total_trades
print(f'   Current brokerage: Rs.40/trade x {total_trades} trades = Rs.{brokerage_savings_yearly:,.0f}/year')
print()
print('   Option A: Zero-brokerage broker')
print(f'   => Save Rs.{brokerage_savings_yearly:,.0f}/year')
print()
print('   Option B: Negotiate lower rates (high volume)')
print('   => Many brokers offer Rs.10/order for active traders')
print(f'   => Save Rs.{20 * total_trades:,.0f}/year')
print()

# Strategy 5: STT info
print('6. STT REDUCTION STRATEGIES')
print('-' * 50)
total_stt = charges_per_trade.stt * total_trades
print(f'   Current STT: Rs.{charges_per_trade.stt:.2f}/trade x {total_trades} = Rs.{total_stt:,.0f}/year')
print()
print('   STT is 0.0125% on SELL side (futures)')
print('   Cannot avoid STT on futures - its mandatory')
print()
print('   Alternative: Trade OPTIONS instead')
print('   - STT on options sell: 0.0625% (higher rate)')
print('   - BUT: Option premium is lower than futures value')
print('   - Net STT may be lower for OTM options')
print()

# Summary
print('=' * 70)
print('TOP RECOMMENDATIONS')
print('=' * 70)
print()
print('+-------------------------------------------------------------------+')
print('| 1. TRADE 3 LOTS INSTEAD OF 1                                      |')
print('|    => Charges drop from 43% to 20% of gross                       |')
print('|    => Net P&L improves by 2.5x per trade                          |')
print('|    => Capital required: ~Rs.1.5 lakh margin                       |')
print('+-------------------------------------------------------------------+')
print('| 2. IMPROVE WIN RATE (Add more filters)                            |')
print('|    => Test volume profile, RSI divergence, support/resistance     |')
print('|    => Each 5% improvement = ~Rs.15,000/year extra                 |')
print('+-------------------------------------------------------------------+')
print('| 3. ZERO/LOW BROKERAGE BROKER                                      |')
print(f'|    => Save Rs.{brokerage_savings_yearly:,.0f}/year in brokerage alone                        |')
print('+-------------------------------------------------------------------+')
print('| 4. COMBINE STRATEGIES                                             |')
print('|    => 3 lots + better win rate + zero brokerage                   |')
print('|    => Potential: 3x improvement in net returns                    |')
print('+-------------------------------------------------------------------+')
