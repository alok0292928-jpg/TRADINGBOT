from flask import Flask, request, jsonify
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import os
import random

app = Flask(__name__)
CORS(app)

# --- THE TRADING BRAIN ---
def analyze_market_data(symbol):
    try:
        # 1. Fetch Data
        stock = yf.Ticker(symbol)
        df = stock.history(period="2d", interval="5m")
        if len(df) < 50: return None

        # 2. Indicators Calculation
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # EMA Trend
        df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
        
        # Current Values
        price = df['Close'].iloc[-1]
        curr_rsi = rsi.iloc[-1]
        ema = df['EMA_200'].iloc[-1]

        # 3. Determine Logic
        trend = "UP" if price > ema else "DOWN"
        
        status = "NEUTRAL"
        if trend == "UP" and curr_rsi < 45: status = "BULLISH (UP)"
        elif trend == "DOWN" and curr_rsi > 55: status = "BEARISH (DOWN)"
        elif curr_rsi > 70: status = "OVERBOUGHT (Risk of Drop)"
        elif curr_rsi < 30: status = "OVERSOLD (Chance of Pump)"

        return {
            "price": round(price, 2),
            "rsi": round(curr_rsi, 2),
            "trend": trend,
            "status": status
        }
    except:
        return None

@app.route('/chat', methods=['POST'])
def chat_bot():
    data = request.json
    user_msg = data.get('message', '').upper()

    # 1. DETECT ASSET (Kaunsa Coin/Stock?)
    symbol = "BTC-USD" # Default
    asset_name = "Bitcoin"
    
    if "ETH" in user_msg: symbol = "ETH-USD"; asset_name="Ethereum"
    elif "GOLD" in user_msg: symbol = "GC=F"; asset_name="Gold"
    elif "EUR" in user_msg: symbol = "EURUSD=X"; asset_name="EUR/USD"
    elif "SOL" in user_msg: symbol = "SOL-USD"; asset_name="Solana"

    # 2. DETECT USER INTENT (Kya karna chahta hai?)
    user_intent = "ASKING" # Sirf puch raha hai
    if any(x in user_msg for x in ["BUY", "UP", "CALL", "LUN", "LE LU", "KHAREED"]): user_intent = "WANTS_UP"
    if any(x in user_msg for x in ["SELL", "DOWN", "PUT", "GIRA", "BECH", "SHORT"]): user_intent = "WANTS_DOWN"

    # 3. GET REAL DATA
    market = analyze_market_data(symbol)

    if not market:
        return jsonify({"reply": "⚠️ Market Data connect nahi ho raha. Shayad Market band hai (Crypto try karo like BTC)."})

    # 4. GENERATE AI RESPONSE (The "ChatGPT" Feel)
    reply = ""

    # SCENARIO A: User wants to BUY (UP)
    if user_intent == "WANTS_UP":
        if "UP" in market['status'] or "OVERSOLD" in market['status']:
            reply = f"✅ **Haan Bhai, Sahi Soch Rahe Ho!**\n\n{asset_name} ka Trend **UP** hai aur RSI ({market['rsi']}) bhi support kar raha hai.\nYeh ek **Strong Buying Zone** hai. 🚀"
        elif "DOWN" in market['status'] or "OVERBOUGHT" in market['status']:
            reply = f"🛑 **RUKO! Galti Mat Karna!**\n\nTum Buy karna chahte ho, lekin Data keh raha hai ki {asset_name} **GIRNE WALA** hai.\nRSI {market['rsi']} hai (Bahut High). **Loss ho jayega, mat lo.** ⚠️"
        else:
            reply = f"⚠️ **Abhi Risk Hai.**\n\nMarket thoda confuse hai. RSI {market['rsi']} hai. Confirm hone ka wait karo."

    # SCENARIO B: User wants to SELL (DOWN)
    elif user_intent == "WANTS_DOWN":
        if "DOWN" in market['status'] or "OVERBOUGHT" in market['status']:
            reply = f"✅ **Bilkul Sahi Pakde Ho!**\n\n{asset_name} weak lag raha hai (RSI: {market['rsi']}).\nYeh **Selling/Short** karne ka sahi time hai. 📉"
        elif "UP" in market['status'] or "OVERSOLD" in market['status']:
            reply = f"🛑 **NAHI BHAI! Mat Becho!**\n\nMarket **UP** trend mein hai. RSI {market['rsi']} hai (Low).\nYahan se market **Pump** karega, Dump nahi. Call side dekho. 🟢"
        else:
            reply = f"⚠️ **Thoda Wait Karo.**\n\nTrend clear nahi hai. Zabardasti trade mat lo."

    # SCENARIO C: General Question (Kaisa hai market?)
    else:
        trend_emoji = "🟢" if market['trend'] == "UP" else "🔴"
        reply = f"🤖 **Analysis for {asset_name}:**\n\n• Price: ${market['price']}\n• Trend: **{market['trend']}** {trend_emoji}\n• RSI: **{market['rsi']}**\n\n👉 **AI Verdict:** Abhi Market **{market['status']}** lag raha hai."

    return jsonify({"reply": reply})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
                
