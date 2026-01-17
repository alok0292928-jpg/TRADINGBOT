from flask import Flask, request, jsonify
from flask_cors import CORS
import yfinance as yf
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
import os

app = Flask(__name__)
CORS(app)

def predict_stock(symbol):
    try:
        stock = yf.Ticker(symbol)
        df = stock.history(period="6mo")
        if df.empty: return None

        df['Day'] = np.arange(len(df))
        X = df[['Day']]
        y = df['Close']

        model = LinearRegression()
        model.fit(X, y)

        next_day = np.array([[len(df) + 1]])
        predicted_price = model.predict(next_day)[0]
        current_price = df['Close'].iloc[-1]

        trend = "BULLISH (UP) 🚀" if predicted_price > current_price else "BEARISH (DOWN) 🔻"
        confidence = model.score(X, y) * 100

        return {
            "symbol": symbol.upper(),
            "current_price": round(current_price, 2),
            "predicted_price": round(predicted_price, 2),
            "signal": trend,
            "accuracy": round(confidence, 2),
            "dates": df.index.strftime('%Y-%m-%d').tolist(),
            "prices": df['Close'].tolist()
        }
    except Exception as e:
        return None

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.json
    symbol = data.get('symbol', 'BTC-USD')
    result = predict_stock(symbol)
    if result: return jsonify({"success": True, "data": result})
    else: return jsonify({"success": False, "error": "Invalid Symbol"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
    