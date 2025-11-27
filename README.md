# HFT - NIFTY Pin Bar Trading System

An automated trading system for NIFTY futures using Pin Bar pattern detection with backtesting and live trading capabilities.

## Features

- **Pin Bar Strategy**: Detects bullish pin bar patterns with configurable risk-reward ratios
- **Backtesting Engine**: Test strategies on historical data with detailed performance metrics
- **Live Trading**: Real-time monitoring and order execution (paper/live modes)
- **Upstox Integration**: OAuth authentication and API integration for Indian markets
- **Profit Analysis**: Comprehensive charge analysis and optimization recommendations

## Project Structure

```
├── Trading/               # Core trading module
│   ├── src/
│   │   ├── backtest/     # Backtesting engine
│   │   ├── charges/      # Brokerage & charges calculator
│   │   ├── data/         # Data fetching utilities
│   │   ├── orders/       # Order management
│   │   ├── strategy/     # Trading strategies
│   │   └── utils/        # Logging & utilities
│   └── examples/         # Usage examples
│
└── UpstoxAuth/           # Authentication module
    └── src/
        ├── auth/         # OAuth & token management
        └── config/       # Configuration & credentials
```

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/pratikkulkarni12490/hft.git
cd hft
```

### 2. Install Dependencies

```bash
pip install -r Trading/requirements.txt
pip install -r UpstoxAuth/requirements.txt
```

### 3. Configure Credentials

Copy the template and add your Upstox API credentials:

```bash
mkdir -p ~/.hft
cp credentials.template.json ~/.hft/credentials.json
```

Edit `~/.hft/credentials.json` with your credentials:
```json
{
  "client_id": "your_client_id",
  "client_secret": "your_client_secret",
  "redirect_uri": "http://localhost"
}
```

**Or** use environment variables:
```bash
export UPSTOX_CLIENT_ID="your_client_id"
export UPSTOX_CLIENT_SECRET="your_client_secret"
```

## Usage

### Run Backtest

```bash
cd Trading
python examples/main.py
```

### Run Profit Analysis

```bash
cd Trading
python profit_analysis.py
```

### Live Trading (Paper Mode)

```bash
cd Trading
python examples/live_trading.py
```

### Live Trading (Real)

```bash
cd Trading
python examples/live_trading.py --live
```

## Getting Upstox API Credentials

1. Sign up at [Upstox Developer Portal](https://upstox.com/developer/api-documentation/)
2. Create an app to get your `client_id` and `client_secret`
3. Set redirect URI to `http://localhost`

## License

MIT
