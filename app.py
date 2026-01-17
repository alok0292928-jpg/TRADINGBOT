from flask import Flask, request, jsonify
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import numpy as np
import os
import time

app = Flask(__name__)
CORS(app)

# --- 🌍 EXPANDED ASSET LIST (Sab Kuch Hai) ---
ASSETS = {
    # FOREX
    "EURUSD=X": "EUR/USD",
    "GBPUSD=X": "GBP/USD",
    "JPY=X": "USD/JPY",
    "AUDUSD=X": "AUD/USD",
    "USDINR=X": "USD/INR",
    
    # CRYPTO
    "BTC-USD": "BITCOIN",
    "ETH-USD": "ETHEREUM",
    "SOL-USD": "SOLANA",
    "XRP-USD": "XRP",
    
    # INDICES (INDIAN & US)
    "^NSEI": "NIFTY 50",
    "^NSEBANK": "BANK NIFTY",
    "^BSESN": "SENSEX",
    "^DJI": "DOW JONES",
    "^IXIC": "NASDAQ",

    # COMMODITIES
    "GC=F": "GOLD",
    "SI=F": "SILVER",
    "CL=F": "CRUDE OIL",
    "NG=F": "NATURAL GAS",

    # STOCKS
    "RELIANCE.NS": "RELIANCE",
    "TCS.NS": "TCS",
    "TSLA": "TESLA",
    "AAPL": "APPLE",
    "GOOG": "GOOGLE",
    "AMZN": "AMAZON"
}

def analyze_market(symbol):
    try:
        # 1. Fetch Data (No Cache) - 1 Day history, 1 Minute interval
        stock = yf.Ticker(symbol)
        df = stock.history(period="1d", interval="1m")
        
        if df.empty: return None

        # Last 50 candles for Chart
        chart_data = {
            "times": df.index.strftime('%H:%M').tolist()[-50:],
            "prices": df['Close'].tolist()[-50:]
        }
        
        current_price = df['Close'].iloc[-1]
        
        # 2. PRO INDICATORS (RSI + MACD)
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        curr_rsi = rsi.iloc[-1]

        # MACD
        ema12 = df['Close'].ewm(span=12, adjust=False).mean()
        ema26 = df['Close'].ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal_line = macd.ewm(span=9, adjust=False).mean()
        
        # 3. SIGNAL LOGIC
        signal = "NEUTRAL"
        direction = "WAIT"
        color = "#888"
        strength = 50 # Default %

        # Strong BUY (RSI < 30 AND MACD Cross Up)
        if curr_rsi < 35 or (macd.iloc[-1] > signal_line.iloc[-1] and curr_rsi < 50):
            signal = "STRONG BUY 🟢"
            direction = "UP"
            color = "#00e676"
            strength = 90
        
        # Strong SELL (RSI > 70 AND MACD Cross Down)
        elif curr_rsi > 65 or (macd.iloc[-1] < signal_line.iloc[-1] and curr_rsi > 50):
            signal = "STRONG SELL 🔴"
            direction = "DOWN"
            color = "#ff1744"
            strength = 90

        return {
            "symbol": symbol,
            "price": round(current_price, 2),
            "chart": chart_data,
            "rsi": round(curr_rsi, 2),
            "signal": signal,
            "direction": direction,
            "color": color,
            "strength": strength
        }

    except Exception as e:
        return None

@app.route('/stream', methods=['POST'])
def stream():
    data = request.json
    symbol = data.get('symbol', 'BTC-USD')
    result = analyze_market(symbol)
    
    if result: return jsonify({"success": True, "data": result})
    else: return jsonify({"success": False, "error": "No Data"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
    
