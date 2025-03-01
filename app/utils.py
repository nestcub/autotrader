def get_default_portfolio():
    return {
        'balance': 100000,
        'holdings': {}, 
        'transactions': []  
    } 

import pandas as pd
# Calculate MACD
def calculate_macd(data):
    short_window = 12
    long_window = 26
    signal_window = 9
    
    
    close_prices = data['Close'].values
    exp1 = pd.Series(close_prices).ewm(span=short_window, adjust=False).mean()
    exp2 = pd.Series(close_prices).ewm(span=long_window, adjust=False).mean()
    macd = exp1 - exp2
    signal = pd.Series(macd).ewm(span=signal_window, adjust=False).mean()
    
    return macd, signal

# Calculate RSI
def calculate_rsi(data, window=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    # Fill NaN values with 50 (neutral RSI)
    rsi = rsi.fillna(50)
    
    return rsi

# Calculate EMA
def calculate_ema(data, short_window=9, long_window=20):
    ema_short = data['Close'].ewm(span=short_window, adjust=False).mean()
    ema_long = data['Close'].ewm(span=long_window, adjust=False).mean()
    
    # Fill NaN values with the first available value
    ema_short = ema_short.bfill().ffill()
    ema_long = ema_long.bfill().ffill()
    
    return ema_short, ema_long

# Calculate Support and Resistance
def calculate_support_resistance(data, window=20):
    rolling_high = data['Close'].rolling(window=window).max()
    rolling_low = data['Close'].rolling(window=window).min()
    support = rolling_low.iloc[-1]
    resistance = rolling_high.iloc[-1]
    return support, resistance

# Determine Buy/Sell/Hold action
def determine_action(macd, signal, rsi, ema_short, ema_long, entry_price, support):
    # Get the latest values
    current_macd = macd.iloc[-1]
    current_signal = signal.iloc[-1]
    current_rsi = rsi.iloc[-1]
    current_ema_short = ema_short.iloc[-1]
    current_ema_long = ema_long.iloc[-1]
    
    # Define oversold/overbought levels
    oversold_rsi = 30
    overbought_rsi = 70
    
    # Buy conditions
    if (current_ema_short > current_ema_long and  # Golden cross
        current_macd > current_signal and         # MACD crossover
        current_rsi < overbought_rsi):           # Not overbought
        return "BUY", max(support, entry_price * 0.98)
    
    # Sell conditions
    elif (current_ema_short < current_ema_long and  # Death cross
          current_macd < current_signal and         # MACD crossunder
          current_rsi > oversold_rsi):             # Not oversold
        return "SELL", support * 0.98
    
    # Hold conditions
    return "HOLD", support