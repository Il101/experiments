# 🚀 Breakout Bot Trading System

A sophisticated cryptocurrency trading bot designed for range breakout strategies with advanced risk management and real-time market analysis.

## ✨ Features

- **🎯 4 Trading Presets**: breakout_v1, smallcap_top_gainers, smallcap_top_losers, high_liquidity_top30
- **📊 Real-time Market Scanning**: Multi-stage filtering and scoring algorithms
- **⚡ Signal Generation**: Momentum and retest strategies
- **🛡️ Risk Management**: R-based position sizing and daily limits
- **📈 Position Management**: Stop loss, take profit, trailing stops
- **🌐 Web Interface**: Modern React frontend with real-time updates
- **🔌 API Interface**: RESTful API with WebSocket support
- **💻 CLI Interface**: Command-line tools for all operations
- **📱 Mobile Responsive**: Works on desktop and mobile devices

## 🚀 Quick Start

### 1. Start All Services
```bash
./start.sh
```

### 2. Check Status
```bash
./status.sh
```

### 3. Stop All Services
```bash
./stop.sh
```

## 📋 Prerequisites

- **Python 3.11+**
- **Node.js 16+**
- **npm**
- **Ports 8000 and 5173 available**

## 🛠️ Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd breakout_bot
```

2. **Install Python dependencies**
```bash
pip install -r requirements.txt
```

3. **Install frontend dependencies**
```bash
cd frontend
npm install
cd ..
```

4. **Make scripts executable**
```bash
chmod +x start.sh stop.sh status.sh
```

## 🎮 Usage

### Start Script (`start.sh`)

Launches all components of the trading system:

```bash
# Start all services
./start.sh

# Show help
./start.sh help
```

**What it does:**
- ✅ Starts API server on port 8000
- ✅ Starts frontend development server on port 5173
- ✅ Starts trading engine with breakout_v1 preset
- ✅ Monitors all services and shows status

### Status Script (`status.sh`)

Check the current status of all system components:

```bash
# Show system status
./status.sh

# Show verbose output
./status.sh --verbose
```

### Stop Script (`stop.sh`)

Stop all running services:

```bash
# Stop all services
./stop.sh
```

## 🌐 Access URLs

Once started, you can access:

- **🌐 Frontend**: http://localhost:5173
- **🔌 API**: http://localhost:8000
- **📊 API Documentation**: http://localhost:8000/docs
- **🔍 Health Check**: http://localhost:8000/api/health
- **📈 Engine Status**: http://localhost:8000/api/engine/status
- **📋 System Logs**: http://localhost:8000/api/logs
- **📊 Scanner Results**: http://localhost:8000/api/scanner/last
- **💼 Positions**: http://localhost:8000/api/trading/positions

## 💻 CLI Commands

```bash
# List available presets
python3 -m breakout_bot.cli.main presets

# Scan markets
python3 -m breakout_bot.cli.main scan breakout_v1

# Start trading
python3 -m breakout_bot.cli.main trade breakout_v1

# Check system status
python3 -m breakout_bot.cli.main status
```

## 🔌 API Commands

```bash
# Start engine
curl -X POST http://localhost:8000/api/engine/start \
  -H "Content-Type: application/json" \
  -d '{"preset": "breakout_v1"}'

# Check engine status
curl http://localhost:8000/api/engine/status

# Pause engine
curl -X POST "http://localhost:8000/api/engine/command?command=pause"

# Resume engine
curl -X POST "http://localhost:8000/api/engine/command?command=resume"
```

## 📊 Trading Presets

### 1. Breakout V1 (`breakout_v1`)
- **Target**: Major cryptocurrencies with high liquidity
- **Strategy**: Momentum breakout after volatility compression
- **Risk**: 0.6% per trade, max 3 positions
- **Filters**: High volume, low spread, good liquidity

### 2. Smallcap Top Gainers (`smallcap_top_gainers`)
- **Target**: Fastest rising small-cap tokens
- **Strategy**: Retest strategy with momentum fallback
- **Risk**: 0.3% per trade, max 2 positions
- **Filters**: Volume surge, OI delta, correlation limits

### 3. Smallcap Top Losers (`smallcap_top_losers`)
- **Target**: Fastest falling small-cap tokens
- **Strategy**: Short retest strategy
- **Risk**: 0.3% per trade, max 2 positions
- **Filters**: Volume surge, OI delta, correlation limits

### 4. High Liquidity Top 30 (`high_liquidity_top30`)
- **Target**: Top 30 cryptocurrencies by volume
- **Strategy**: Conservative momentum breakouts
- **Risk**: 0.5% per trade, max 3 positions
- **Filters**: Top volume, excellent liquidity

## 🛡️ Risk Management

- **R-based Position Sizing**: Risk per trade based on account equity
- **Daily Risk Limits**: Maximum daily loss protection
- **Kill Switch**: Automatic stop on consecutive losses
- **Correlation Limits**: Prevents overexposure to similar assets
- **Position Limits**: Maximum concurrent positions per preset

## 📈 Technical Indicators

- **ATR**: Average True Range for volatility measurement
- **Bollinger Bands**: Volatility compression detection
- **VWAP**: Volume Weighted Average Price
- **RSI**: Relative Strength Index
- **OBV**: On-Balance Volume
- **Donchian Channels**: Support/resistance levels
- **Chandelier Exit**: Trailing stop mechanism

## 🔧 Configuration

### Environment Variables
Create a `.env` file:
```bash
# Exchange Configuration
EXCHANGE=bybit
API_KEY=your_api_key
API_SECRET=your_api_secret
SUBACCOUNT=your_subaccount

# Trading Mode
TRADING_MODE=paper  # or 'live'

# Risk Settings
DAILY_RISK_LIMIT=2.0
MAX_CONCURRENT_POSITIONS=3
```

### Preset Configuration
Edit preset files in `breakout_bot/config/presets/`:
- `breakout_v1.json`
- `smallcap_top_gainers.json`
- `smallcap_top_losers.json`
- `high_liquidity_top30.json`

## 📊 Monitoring

### Real-time Monitoring
- **Web Interface**: Live dashboard with real-time updates
- **API Endpoints**: Programmatic access to all data
- **WebSocket**: Real-time data streaming
- **Logs**: Comprehensive logging system

### Performance Metrics
- **Win Rate**: Percentage of profitable trades
- **Average R**: Average risk-reward ratio
- **Sharpe Ratio**: Risk-adjusted returns
- **Maximum Drawdown**: Largest peak-to-trough decline
- **Profit Factor**: Gross profit / gross loss

## 🚨 Troubleshooting

### Port Already in Use
```bash
# Stop all services first
./stop.sh

# Wait a moment
sleep 2

# Start again
./start.sh
```

### Services Not Starting
Check the logs:
```bash
# View API logs
tail -f logs/api.log

# View frontend logs
tail -f logs/frontend.log
```

### Engine in Error State
```bash
# Check engine status
curl http://localhost:8000/api/engine/status

# Try to retry
curl -X POST "http://localhost:8000/api/engine/command?command=retry"
```

## 📁 Project Structure

```
breakout_bot/
├── api/                    # FastAPI web server
├── cli/                    # Command-line interface
├── config/                 # Configuration files
├── core/                   # Core trading engine
├── data/                   # Data models
├── exchange/               # Exchange integration
├── indicators/             # Technical indicators
├── position/               # Position management
├── risk/                   # Risk management
├── scanner/                # Market scanning
├── signals/                # Signal generation
├── tests/                  # Test suite
├── utils/                  # Utility functions
├── frontend/               # React frontend
├── start.sh                # Startup script
├── stop.sh                 # Stop script
├── status.sh               # Status script
└── README.md               # This file
```

## 🧪 Testing

Run the test suite:
```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest breakout_bot/tests/test_engine.py

# Run with coverage
python -m pytest --cov=breakout_bot
```

## 📝 Logs

All logs are stored in the `logs/` directory:
- `logs/api.log` - API server logs
- `logs/frontend.log` - Frontend development server logs

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This software is for educational and research purposes only. Trading cryptocurrencies involves substantial risk of loss and is not suitable for all investors. Past performance is not indicative of future results. Always do your own research and consider your risk tolerance before trading.

## 🆘 Support

For issues or questions:
1. Check the logs first
2. Use `./status.sh` to check system status
3. Restart with `./stop.sh && ./start.sh`
4. Check the API documentation at http://localhost:8000/docs
5. Open an issue on GitHub

---

**🎯 Ready to trade? Run `./start.sh` and start your trading journey!**