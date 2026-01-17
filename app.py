from flask import Flask, request, jsonify
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import numpy as np
import os

app = Flask(__name__)
CORS(app)

def deepseek_algo(df):
    # 1. Calculate Indicators
    # EMA 200 (Long Term Trend)
    df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
    
    # RSI (14)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    # MACD (12, 26, 9)
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal_line = macd.ewm(span=9, adjust=False).mean()

    # Current Values
    price = df['Close'].iloc[-1]
    curr_ema = df['EMA_200'].iloc[-1]
    curr_rsi = rsi.iloc[-1]
    curr_macd = macd.iloc[-1]
    curr_sig = signal_line.iloc[-1]

    # --- DEEPSEEK LOGIC SCORING (0 to 100) ---
    score = 0
    decision = "WAIT"
    direction = "NEUTRAL"
    reason = "Analyzing Market Structure..."
    color = "#888"

    # RULE 1: TREND FILTER (Nadi ke saath baho)
    trend = "UP" if price > curr_ema else "DOWN"
    
    if trend == "UP":
        score += 20 # Points for Uptrend
        
        # RULE 2: RSI OVERSOLD (Sasta kharido)
        if curr_rsi < 40: score += 30
        if curr_rsi < 30: score += 10 # Extra points for extreme oversold

        # RULE 3: MACD CROSSOVER (Green Signal)
        if curr_macd > curr_sig: score += 40

        if score >= 80:
            decision = "DEEPSEEK BUY 🚀"
            direction = "UP"
            color = "#00e676"
            reason = "Uptrend + Dip Buying + MACD Cross"

    elif trend == "DOWN":
        score += 20 # Points for Downtrend

        # RULE 2: RSI OVERBOUGHT (Mehnga becho)
        if curr_rsi > 60: score += 30
        if curr_rsi > 70: score += 10

        # RULE 3: MACD CROSSOVER (Red Signal)
        if curr_macd < curr_sig: score += 40

        if score >= 80:
            decision = "DEEPSEEK SELL 🔻"
            direction = "DOWN"
            color = "#ff1744"
            reason = "Downtrend + Rally Sell + MACD Cross"

    # Chart Data Preparation
    chart_data = {
        "times": df.index.strftime('%H:%M').tolist()[-40:],
        "prices": df['Close'].tolist()[-40:]
    }

    return {
        "symbol": df.attrs.get('symbol', 'Unknown'),
        "price": round(price, 2),
        "decision": decision,
        "direction": direction,
        "score": score,
        "reason": reason,
        "color": color,
        "chart": chart_data,
        "rsi": round(curr_rsi, 2),
        "trend": trend
    }

@app.route('/deepseek', methods=['POST'])
def analyze():
    data = request.json
    symbol = data.get('symbol', 'BTC-USD')
    
    try:
        stock = yf.Ticker(symbol)
        df = stock.history(period="5d", interval="5m") # 5 Days data for accurate EMA 200
        df.attrs['symbol'] = symbol
        
        if len(df) < 200:
            return jsonify({"success": False, "error": "Not enough data for DeepSeek Logic"})

        result = deepseek_algo(df)
        return jsonify({"success": True, "data": result})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
