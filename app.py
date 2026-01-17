from flask import Flask, request, jsonify
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import os
import random

app = Flask(__name__)
CORS(app)

# --- TRADING LOGIC (Sirf tab chalega jab maanga jayega) ---
def analyze_market(symbol):
    try:
        stock = yf.Ticker(symbol)
        df = stock.history(period="2d", interval="5m")
        if len(df) < 20: return None
        
        # Calculations
        df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        price = df['Close'].iloc[-1]
        curr_rsi = rsi.iloc[-1]
        ema = df['EMA_200'].iloc[-1]
        trend = "UP" if price > ema else "DOWN"
        
        return {"price": round(price,2), "rsi": round(curr_rsi,2), "trend": trend}
    except:
        return None

@app.route('/chat', methods=['POST'])
def chat_bot():
    data = request.json
    raw_msg = data.get('message', '')
    user_msg = raw_msg.upper() # Sab capital mein convert taaki samajhne me aasaani ho

    # --- 1. CONVERSATIONAL LOGIC (Baat-Cheet) ---
    
    # Greetings
    if any(x in user_msg for x in ["HI", "HELLO", "HEY", "NAMASTE", "KAISE HO", "SUP"]):
        return jsonify({"reply": "Bhai main badhiya hu! 😎<br>Aaj market mein aag lagani hai ya bas timepass karna hai?<br><br>Tum kisi bhi coin ka naam likho (jaise **BTC**, **Gold**) main bata dunga kya karna hai."})

    # Identity
    if any(x in user_msg for x in ["KON HAI", "NAAM KYA", "KYA KARTA HAI"]):
        return jsonify({"reply": "Main tera **Personal Trading Assistant** hu. 🤖<br>Mera kaam hai tujhe loss se bachana aur profit karwana.<br>Koi trade lene ka mann hai?"})

    # Empathy (Loss/Profit talk)
    if "LOSS" in user_msg:
        return jsonify({"reply": "Arey yar, tension mat le. Loss trading ka hissa hai. 📉<br>Chill maar, agla trade soch samajh kar lenge. Bata kisme trade karna hai?"})
    
    if "PROFIT" in user_msg:
        return jsonify({"reply": "Wah bhai! Party kab de raha hai? 🤑<br>Zyaada hawa mein mat udna, discipline banaye rakhna."})

    # Abuse/Angry (Handling Gussa)
    if any(x in user_msg for x in ["PAGAL", "BEKAR", "CHUP", "BHAAG"]):
        return jsonify({"reply": "Shaant gadadhaari Bheem, shaant! 🧘‍♂️<br>Gussa side mein rakh aur bata market kaisa chal raha hai?"})

    # --- 2. TRADING LOGIC (Jab Asset ka naam aaye) ---
    
    symbol = None
    asset_name = ""

    if "BTC" in user_msg or "BITCOIN" in user_msg: symbol = "BTC-USD"; asset_name="Bitcoin"
    elif "ETH" in user_msg: symbol = "ETH-USD"; asset_name="Ethereum"
    elif "GOLD" in user_msg: symbol = "GC=F"; asset_name="Gold"
    elif "EUR" in user_msg: symbol = "EURUSD=X"; asset_name="EUR/USD"
    elif "SOL" in user_msg: symbol = "SOL-USD"; asset_name="Solana"

    # Agar koi Asset mention nahi kiya, to pucho
    if not symbol:
        return jsonify({"reply": "Bhai mujhe samajh nahi aaya kya check karna hai. 🤔<br>Coin ka naam likho (jaise <b>BTC</b>, <b>ETH</b>, <b>Gold</b>) tabhi main chart dekh paunga."})

    # Agar Asset mil gaya, to Analyze karo
    market = analyze_market(symbol)
    
    if not market:
        return jsonify({"reply": f"⚠️ **{asset_name}** ka data load nahi ho raha. Shayad market band hai."})

    # AI RESPONSE GENERATION
    reply = ""
    trend_icon = "🟢" if market['trend'] == "UP" else "🔴"
    
    # User ne pucha "Buy karu?"
    if any(x in user_msg for x in ["BUY", "LE LU", "UP", "CALL"]):
        if market['trend'] == "UP" and market['rsi'] < 60:
            reply = f"✅ **Haan bhai, le sakte ho!**<br>{asset_name} ka Trend UP hai {trend_icon} aur RSI {market['rsi']} hai.<br>Accha mauka hai. 🚀"
        else:
            reply = f"🛑 **Nahi bhai, ruk ja!**<br>Tum Buy karna chahte ho par market {market['trend']} hai ya RSI High ({market['rsi']}) hai.<br>Abhi entry risky hai."
            
    # User ne pucha "Sell karu?"
    elif any(x in user_msg for x in ["SELL", "BECH", "DOWN", "PUT"]):
        if market['trend'] == "DOWN" or market['rsi'] > 70:
            reply = f"✅ **Sahi pakde ho!**<br>{asset_name} girne wala lag raha hai. Short/Put le sakte ho. 📉"
        else:
            reply = f"🛑 **Galti mat karna!**<br>{asset_name} abhi Strong hai (Trend UP). Sell karoge to fas jaoge."
            
    # General Analysis
    else:
        reply = f"📊 **{asset_name} Report:**<br>• Price: ${market['price']}<br>• Trend: <b>{market['trend']}</b> {trend_icon}<br>• RSI: {market['rsi']}<br><br>Kuch puchna hai iske baare mein? (Jaise 'Buy karu?')"

    return jsonify({"reply": reply})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
        
