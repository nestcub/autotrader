import pandas as pd
import threading
from app import socketio
import yliveticker
from app.utils import calculate_macd, calculate_rsi, calculate_ema, calculate_support_resistance, determine_action

# List of Indian stocks (NSE)
STOCKS = {
    'RELIANCE.NS': 'Reliance Industries',
    'TCS.NS': 'Tata Consultancy Services',
    'HDFCBANK.NS': 'HDFC Bank',
    'INFY.NS': 'Infosys',
    'WIPRO.NS': 'Wipro',
    'ICICIBANK.NS': 'ICICI Bank',
    'ITC.NS': 'ITC',
    'SBIN.NS': 'State Bank of India'
}

# Global dictionaries to store data
stock_data = {}
user_portfolios = {}
sid_to_session = {}

def on_ticker_update(ws, msg):
    """Callback function for ticker updates with technical indicators"""
    try:
        symbol = msg['id']
        if symbol in STOCKS:
            # Update stock data
            if symbol not in stock_data:
                stock_data[symbol] = {'history': pd.DataFrame(columns=['Close'])}
            stock_data[symbol].update({
                'name': STOCKS[symbol],
                'price': msg['price'],
                'change': msg.get('changePercent', 0),
                'volume': msg.get('dayVolume', 0),
                'timestamp': msg.get('timestamp', '')
            })

            # Append latest price (maintain rolling window of 50 for analysis)
            new_data = pd.DataFrame({'Close': [msg['price']]})
            if stock_data[symbol]['history'].empty:
                stock_data[symbol]['history'] = new_data
            else:
                stock_data[symbol]['history'] = pd.concat([stock_data[symbol]['history'], new_data], ignore_index=True).tail(50)



            # Compute indicators if sufficient data
            if len(stock_data[symbol]['history']) >= 26:  # Ensure enough data for MACD
                data = stock_data[symbol]['history']
                macd, signal = calculate_macd(data)
                rsi = calculate_rsi(data)
                ema_short, ema_long = calculate_ema(data)
                support, resistance = calculate_support_resistance(data)

                # Determine trade action
                entry_price = msg['price']  # Assume entry price is latest price
                action, stop_loss = determine_action(macd, signal, rsi, ema_short, ema_long, entry_price, support)

                # Include trade signals in stock update
                stock_data[symbol]['trade_signal'] = action
                stock_data[symbol]['stop_loss'] = stop_loss

            # Emit stock updates + trade signals to all clients
            # Convert stock_data to JSON-serializable format before emitting
            json_safe_stock_data = {
                symbol: {
                    'name': data['name'],
                    'price': data['price'],
                    'change': data['change'],
                    'volume': data['volume'],
                    'timestamp': data['timestamp'],
                    'trade_signal': data.get('trade_signal', '-'),
                    'stop_loss': data.get('stop_loss', None),
                    'history': data['history']['Close'].tolist() if 'history' in data and not data['history'].empty else []
                }
                for symbol, data in stock_data.items()
            }

            # Emit stock updates + trade signals to all clients
            socketio.emit('updates', {'stocks': json_safe_stock_data})


            # Update portfolios
            for portfolio in user_portfolios.values():
                for holding in portfolio['holdings'].values():
                    if holding['symbol'] in stock_data:
                        current_price = stock_data[holding['symbol']]['price']
                        holding['current_price'] = current_price
                        holding['current_value'] = current_price * holding['quantity']
                        holding['profit_loss'] = (current_price - holding['avg_price']) * holding['quantity']
            socketio.emit('portfolio_update', {'portfolios': user_portfolios})

    except Exception as e:
        print(f"Error processing ticker update: {e}")

def start_ticker():
    """Start the ticker in a separate thread"""
    try:
        yliveticker.YLiveTicker(on_ticker=on_ticker_update,
                                ticker_names=list(STOCKS.keys()))
    except Exception as e:
        print(f"Error starting ticker: {e}")

# Start the ticker in a background thread
ticker_thread = threading.Thread(target=start_ticker)
ticker_thread.daemon = True
ticker_thread.start()