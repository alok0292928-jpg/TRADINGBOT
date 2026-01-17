from flask import Flask, request, jsonify
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import numpy as np
import os
import time

app = Flask(__name__)
CORS(app)

# --- EXPANDED ASSET LIST ---
ASSETS = {
    "EURUSD=X": "EUR/USD",
    "GBPUSD=X": "GBP/USD",
    "JPY=X": "USD/JPY",
    "BTC-USD": "BITCOIN",
    "ETH-USD": "ETHEREUM",
    "GC=F": "GOLD",
    "CL=F": "CRUDE OIL",
    "^NSEI": "NIFTY 50",
    "RELIANCE.NS": "RELIANCE"
}

def calculate_indicators(df):
    # 1. RSI (14)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    # 2. Bollinger Bands (For Volatility/Sideways detect)
    sma20 = df['Close'].rolling(window=20).mean()
    std = df['Close'].rolling(window=20).std()
    upper = sma20 + (2 * std)
    lower = sma20 - (2 * std)
    bandwidth = (upper - lower) / sma20 * 100  # Squeeze Detector

    # 3. EMA 50 (Trend Filter)
    ema50 = df['Close'].ewm(span=50, adjust=False).mean()

    # 4. Support & Resistance (Recent 50 candles)
    support = df['Low'].rolling(window=50).min()
    resistance = df['High'].rolling(window=50).max()

    return rsi, bandwidth, ema50, support, resistance

def analyze_market(symbol, mode="SAFE"):
    try:
        stock = yf.Ticker(symbol)
        df = stock.history(period="1d", interval="1m")
        if df.empty: return None

        # Data Setup
        rsi, bandwidth, ema50, support, resistance = calculate_indicators(df)
        
        current_price = df['Close'].iloc[-1]
        curr_rsi = rsi.iloc[-1]
        curr_bw = bandwidth.iloc[-1]
        curr_ema = ema50.iloc[-1]
        curr_supp = support.iloc[-1]
        curr_res = resistance.iloc[-1]

        # Chart Data
        chart_data = {
            "times": df.index.strftime('%H:%M').tolist()[-50:],
            "prices": df['Close'].tolist()[-50:]
        }

        # --- INTELLIGENT LOGIC ---
        signal = "WAIT ✋"
        direction = "NEUTRAL"
        reason = "Scanning..."
        confidence = 0
        status = "NORMAL" # Trend or Choppy
        color = "#888"

        # 1. DETECT SIDEWAYS (CHOPPY MARKET)
        if curr_bw < 0.10:  # Bandwidth very low = Squeeze
            status = "⚠️ CHOPPY / SIDEWAYS"
            signal = "NO TRADE ❌"
            reason = "Market is sleeping (Low Volatility)"
            direction = "AVOID"
            color = "#ff9800" # Orange
        
        else:
            # 2. TREND DETECTION
            trend = "UP" if current_price > curr_ema else "DOWN"
            status = f"TRENDING {trend} 🌊"

            # 3. SIGNAL GENERATION
            
            # --- CALL (UP) SCENARIO ---
            if (curr_rsi < 35) or (current_price <= curr_supp * 1.0005):
                score = 50
                reasons = []
                
                if trend == "UP": 
                    score += 20; reasons.append("Trend Aligned")
                if curr_rsi < 30: 
                    score += 15; reasons.append("Oversold RSI")
                if abs(current_price - curr_supp) < 0.5: 
                    score += 15; reasons.append("Support Bounce")
                
                if score >= 60:
                    signal = "CALL (BUY) 🟢"
                    direction = "UP"
                    color = "#00e676"
                    confidence = score
                    reason = " + ".join(reasons)

            # --- PUT (DOWN) SCENARIO ---
            elif (curr_rsi > 65) or (current_price >= curr_res * 0.9995):
                score = 50
                reasons = []

                if trend == "DOWN": 
                    score += 20; reasons.append("Trend Aligned")
                if curr_rsi > 70: 
                    score += 15; reasons.append("Overbought RSI")
                if abs(current_price - curr_res) < 0.5: 
                    score += 15; reasons.append("Resistance Rejection")

                if score >= 60:
                    signal = "PUT (SELL) 🔴"
                    direction = "DOWN"
                    color = "#ff1744"
                    confidence = score
                    reason = " + ".join(reasons)

        # Mode Filter (If User wants Safe Mode, ignore weak signals)
        if mode == "SAFE" and confidence < 75 and direction != "AVOID":
            signal = "WEAK SIGNAL ⚠️"
            reason = "Confidence too low for Safe Mode"
            color = "#aaa"

        return {
            "symbol": symbol,
            "price": round(current_price, 2),
            "chart": chart_data,
            "rsi": round(curr_rsi, 2),
            "signal": signal,
            "direction": direction,
            "reason": reason,
            "confidence": confidence,
            "status": status,
            "color": color,
            "support": round(curr_supp, 2),
            "resistance": round(curr_res, 2)
        }

    except Exception as e:
        print(e)
        return None

@app.route('/stream', methods=['POST'])
def stream():
    data = request.json
    symbol = data.get('symbol', 'BTC-USD')
    mode = data.get('mode', 'SAFE') # User can choose SAFE or AGGRESSIVE
    result = analyze_market(symbol, mode)
    
    if result: return jsonify({"success": True, "data": result})
    else: return jsonify({"success": False, "error": "No Data"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
                
