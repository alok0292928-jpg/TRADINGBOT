from flask import Flask, request, jsonify
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import os

app = Flask(__name__)
CORS(app)

# --- ENGINE: FAST SCAN ---
def analyze_stock(symbol):
    try:
        stock = yf.Ticker(symbol)
        # 5 Days data to ensure we have candles even on weekends/holidays
        df = stock.history(period="5d", interval="5m")
        
        if len(df) < 20: return None

        # Indicators
        df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        price = df['Close'].iloc[-1]
        ema = df['EMA_200'].iloc[-1]
        curr_rsi = rsi.iloc[-1]

        # --- LOGIC ---
        direction = "WAIT"
        signal = "NEUTRAL"
        color = "#888"
        reason = "Market sideways hai."

        # BUY LOGIC
        if price > ema and curr_rsi < 60:
            direction = "UP 🟢"
            signal = "CALL / BUY"
            color = "#00e676" # Neon Green
            reason = f"Trend UP hai aur RSI ({round(curr_rsi)}) safe hai."
        elif curr_rsi < 30:
            direction = "UP 🟢"
            signal = "STRONG BUY"
            color = "#00e676"
            reason = "Oversold Zone! Pump aayega."

        # SELL LOGIC
        elif price < ema and curr_rsi > 40:
            direction = "DOWN 🔴"
            signal = "PUT / SELL"
            color = "#ff1744" # Neon Red
            reason = f"Trend DOWN hai aur RSI ({round(curr_rsi)}) weak hai."
        elif curr_rsi > 70:
            direction = "DOWN 🔴"
            signal = "STRONG SELL"
            color = "#ff1744"
            reason = "Overbought Zone! Market girega."

        return {
            "price": round(price, 2),
            "signal": signal,
            "direction": direction,
            "reason": reason,
            "color": color,
            "rsi": round(curr_rsi, 2)
        }

    except:
        return None

@app.route('/scan', methods=['POST'])
def scan():
    data = request.json
    symbol = data.get('symbol', 'BTC-USD')
    result = analyze_stock(symbol)
    
    if result: return jsonify({"success": True, "data": result})
    else: return jsonify({"success": False, "error": "Market Closed or No Data"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
