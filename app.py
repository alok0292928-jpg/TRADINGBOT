from flask import Flask, request, jsonify
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import numpy as np
import os

app = Flask(__name__)
CORS(app)

def get_live_analysis(symbol):
    try:
        # 1. Fetch Data (1 Minute Interval for Scalping)
        stock = yf.Ticker(symbol)
        df = stock.history(period="1d", interval="1m")
        
        if df.empty: return None

        # 2. Prepare Chart Data (Last 30 points for Graph)
        chart_data = {
            "times": df.index.strftime('%H:%M').tolist()[-30:],
            "prices": df['Close'].tolist()[-30:]
        }

        # 3. Strategy: Bollinger Bands + RSI
        # (Ye strategy 1 Min trades ke liye best hai)
        
        # Calculate RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]
        
        # Calculate Bollinger Bands
        sma = df['Close'].rolling(window=20).mean()
        std = df['Close'].rolling(window=20).std()
        upper_band = sma + (2 * std)
        lower_band = sma - (2 * std)
        
        price = df['Close'].iloc[-1]
        u_band = upper_band.iloc[-1]
        l_band = lower_band.iloc[-1]

        # 4. DECISION LOGIC
        signal = "SCANNING..."
        direction = "NEUTRAL"
        color = "#888"
        
        # Logic: Agar Price Lower Band ko touch kare aur RSI < 30 ho -> BUY
        if price <= l_band or current_rsi < 30:
            signal = "🚀 OPEN UP TRADE"
            direction = "UP"
            color = "#00e676" # Green
            
        # Logic: Agar Price Upper Band ko touch kare aur RSI > 70 ho -> SELL
        elif price >= u_band or current_rsi > 70:
            signal = "🔻 OPEN DOWN TRADE"
            direction = "DOWN"
            color = "#ff1744" # Red

        return {
            "symbol": symbol,
            "current_price": round(price, 4),
            "chart": chart_data,
            "signal": signal,
            "direction": direction,
            "color": color,
            "rsi": round(current_rsi, 2)
        }

    except Exception as e:
        return None

@app.route('/stream', methods=['POST'])
def stream():
    data = request.json
    symbol = data.get('symbol', 'EURUSD=X')
    result = get_live_analysis(symbol)
    
    if result: return jsonify({"success": True, "data": result})
    else: return jsonify({"success": False, "error": "No Data"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
    
