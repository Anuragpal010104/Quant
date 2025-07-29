import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from typing import Tuple, Any
import matplotlib.pyplot as plt
import os

try:
    from arch import arch_model
    HAS_ARCH = True
except ImportError:
    HAS_ARCH = False

# --- 1. Historical Volatility Dataset Preparation ---
def prepare_volatility_dataset(price_series: pd.Series, window: int = 10) -> pd.DataFrame:
    """
    Prepare features for volatility forecasting.
    Computes realized volatility, lagged returns, momentum, and technical indicators.
    """
    df = pd.DataFrame({'price': price_series})
    df['log_return'] = np.log(df['price']).diff()
    df['realized_vol'] = df['log_return'].rolling(window).std() * np.sqrt(365)
    df['lagged_return'] = df['log_return'].shift(1)
    df['ema_10'] = df['price'].ewm(span=10).mean()
    df['ema_20'] = df['price'].ewm(span=20).mean()
    df['momentum'] = df['price'] - df['price'].shift(window)
    # RSI
    delta = df['price'].diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    roll_up = up.rolling(window).mean()
    roll_down = down.rolling(window).mean()
    rs = roll_up / (roll_down + 1e-8)
    df['rsi'] = 100 - (100 / (1 + rs))
    # MACD
    ema12 = df['price'].ewm(span=12).mean()
    ema26 = df['price'].ewm(span=26).mean()
    df['macd'] = ema12 - ema26
    # ATR
    df['high'] = df['price']
    df['low'] = df['price']
    df['close'] = df['price']
    df['tr'] = df['high'] - df['low']
    df['atr'] = df['tr'].rolling(window).mean()
    # Bollinger Band width
    ma = df['price'].rolling(window).mean()
    std = df['price'].rolling(window).std()
    df['bb_width'] = (ma + 2*std - (ma - 2*std)) / ma
    # Label: next-day realized volatility
    df['target_vol'] = df['realized_vol'].shift(-1)
    df = df.dropna()
    return df

# --- 2. ML Models for Volatility Forecasting ---
def train_vol_model(X_train: pd.DataFrame, y_train: pd.Series, model_type: str = 'rf') -> Any:
    """
    Train a volatility forecasting model. model_type: 'lr', 'rf', or 'garch'.
    """
    if model_type == 'lr':
        model = LinearRegression()
        model.fit(X_train, y_train)
        return model
    elif model_type == 'rf':
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)
        return model
    elif model_type == 'garch' and HAS_ARCH:
        am = arch_model(y_train, vol='Garch', p=1, q=1)
        res = am.fit(disp='off')
        return res
    else:
        raise ValueError('Unknown or unavailable model_type')

def predict_volatility(model: Any, X_test: pd.DataFrame, model_type: str = 'rf') -> np.ndarray:
    if model_type in ['lr', 'rf']:
        return model.predict(X_test)
    elif model_type == 'garch' and HAS_ARCH:
        return model.forecast(horizon=len(X_test)).variance.values[-1] ** 0.5
    else:
        raise ValueError('Unknown or unavailable model_type')

# --- 3. Hedge Timing Optimization ---
def should_hedge(vol_forecast: float, delta_exposure: float, threshold: float) -> bool:
    """
    Decide whether to hedge based on forecasted volatility and delta exposure.
    """
    risk_metric = abs(delta_exposure) * vol_forecast
    return risk_metric > threshold

# --- 4. Evaluation Metrics ---
def evaluate_vol_model(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    mae = mean_absolute_error(y_true, y_pred)
    rmse = mean_squared_error(y_true, y_pred, squared=False)
    direction_acc = np.mean((np.diff(y_true) > 0) == (np.diff(y_pred) > 0))
    return {'MAE': mae, 'RMSE': rmse, 'Directional_Accuracy': direction_acc}

# --- 5. Backtesting Integration ---
def backtest_hedge_strategy(price_series: pd.Series, delta_series: pd.Series, threshold: float, model_type: str = 'rf') -> dict:
    """
    Backtest hedge strategy using vol forecast + delta exposure.
    Returns performance metrics and comparison to naive strategy.
    """
    df = prepare_volatility_dataset(price_series)
    X = df.drop(['price', 'target_vol'], axis=1)
    y = df['target_vol']
    split = int(0.7 * len(df))
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]
    model = train_vol_model(X_train, y_train, model_type)
    y_pred = predict_volatility(model, X_test, model_type)
    # Align delta_series
    delta_test = delta_series.iloc[-len(y_pred):]
    # Strategy: hedge if should_hedge
    hedge_signals = [should_hedge(v, d, threshold) for v, d in zip(y_pred, delta_test)]
    naive_signals = [abs(d) > threshold for d in delta_test]
    # Performance: count hedges, compare to naive
    perf = {
        'hedge_count': sum(hedge_signals),
        'naive_hedge_count': sum(naive_signals),
        'model_metrics': evaluate_vol_model(y_test.values, y_pred),
    }
    return perf

# --- 6. Telegram Command (Optional) ---
def format_vol_forecast_message(asset: str, forecast: float, model_name: str, action: str) -> str:
    return f"\U0001F52E Predicted 1d Volatility for {asset}: {forecast:.2%} | Model: {model_name} | Action: {action}"

# --- 7. Unit Test ---
def _unit_test():
    np.random.seed(42)
    n = 400
    price = pd.Series(np.cumprod(1 + 0.01 * np.random.randn(n)) * 30000)
    delta = pd.Series(np.random.randn(n))
    df = prepare_volatility_dataset(price)
    X = df.drop(['price', 'target_vol'], axis=1)
    y = df['target_vol']
    split = int(0.7 * len(df))
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]
    model = train_vol_model(X_train, y_train, 'rf')
    y_pred = predict_volatility(model, X_test, 'rf')
    assert (y_pred > 0).all(), "Predicted volatility must be positive"
    metrics = evaluate_vol_model(y_test.values, y_pred)
    print("Unit test metrics:", metrics)
    perf = backtest_hedge_strategy(price, delta, threshold=0.5, model_type='rf')
    print("Backtest performance:", perf)

if __name__ == "__main__":
    _unit_test()
