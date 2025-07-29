# Quant Crypto Risk Management & Hedging Bot

## Overview
This project is a comprehensive crypto risk management and automated hedging system with multi-exchange support, real-time analytics, and a Telegram bot interface. It is designed for professional portfolio management, risk monitoring, and compliance reporting.

---

## Features
- **Multi-exchange support:** OKX, Bybit, Deribit APIs
- **Risk analytics:** Real-time and historical risk metrics (Delta, Gamma, Vega, Theta, VaR)
- **Automated hedging:** Perpetual futures and options-based strategies
- **Telegram bot:** Interactive commands, risk alerts, and reporting
- **Performance tracking:** Hedge logs, P&L attribution, analytics charts
- **Compliance reporting:** Regulatory risk reports, threshold monitoring
- **Machine Learning Volatility Forecasting:** ML-based volatility prediction and optimal hedge timing
- **Multi-Asset Portfolio Hedging:** Cross-asset correlation analysis and coordinated hedging for complex portfolios
- **Advanced Options Strategies:** Iron condors, butterfly spreads, straddles, and more
- **Backtesting Framework:** Validate hedging strategies with historical simulations
- **Performance Attribution:** Detailed analysis of hedging effectiveness and cost-benefit

---

## Setup & Installation
1. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```
2. **Configure environment:**
   - Copy `.env.local` and fill in your API keys and Telegram bot token.
   - Example:
     ```env
     OKX_API_KEY=your_okx_key
     OKX_API_SECRET=your_okx_secret
     BYBIT_API_KEY=your_bybit_key
     BYBIT_API_SECRET=your_bybit_secret
     DERIBIT_API_KEY=your_deribit_key
     DERIBIT_API_SECRET=your_deribit_secret
     TELEGRAM_BOT_TOKEN=your_telegram_token
     ```
3. **Run the Telegram bot:**
   ```sh
   python telegram_bot.py
   ```

---

## Usage
Interact with the bot via Telegram using commands:
- `/start` — Welcome message
- `/health` — Check API connectivity
- `/risk_summary` — Portfolio risk metrics
- `/monitor_risk <symbol> <size> <threshold>` — Start monitoring
- `/stop_risk_monitoring` — Stop monitoring
- `/hedge_now <asset> <size> <side>` — Execute hedge
- `/hedge_status <asset>` — Last hedge info
- `/vol_forecast <asset>` — ML volatility forecast and hedge timing
- `/hedge_portfolio` — Multi-asset portfolio hedging
- `/strategy_payoff <iron_condor|butterfly|straddle>` — Advanced options strategy payoff
- `/backtest` — Backtesting framework for strategies
- `/risk_report` — Regulatory compliance risk report
- `/performance_report` — Hedge effectiveness and cost-benefit analysis
- `/help` — List available commands

Inline buttons allow for quick hedging, threshold adjustment, and stopping monitoring.

---

## Code Structure
- `telegram_bot.py` — Main bot logic and command handlers
- `exchange_api/` — API integrations for OKX, Bybit, Deribit
- `risk_engine/` — Risk models and analytics
- `hedging/` — Hedging logic and advanced strategies
- `analytics/` — Performance tracking and attribution
- `compliance/` — Regulatory reporting
- `ml/` — Machine learning volatility models
- `portfolio/` — Multi-asset hedging
- `backtesting/` — Backtesting framework

---

## Documentation & Support
- See the included documentation for risk model details, usage instructions, and optimization tips.
- For questions or feedback, contact Anurag Pal or open an issue on GitHub.

---

## Risk Management Documentation
- **Models:** Black-Scholes, VaR, correlation, delta/gamma/vega/theta
- **Assumptions:** Market liquidity, API reliability, model limitations
- **Performance:** Logs, analytics charts, recommendations for optimization

---

## Bonus Features
- ML volatility forecasting (`ml/volatility_model.py`)
- Multi-asset hedging (`portfolio/multi_asset_hedging.py`)
- Advanced options strategies (`hedging/advanced_strategies.py`)

---

