from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timezone

app = Flask(__name__)
CORS(app)

BINANCE_URL = "https://api.binance.com/api/v3/klines"

# -----------------------------
# Indicators
# -----------------------------
def ema(series, period=20):
    return series.ewm(span=period, adjust=False).mean()

def rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / (loss.replace(0, np.nan))
    return 100 - (100 / (1 + rs))

def macd(close, fast=12, slow=26, signal=9):
    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

# -----------------------------
# Candle pattern detection
# -----------------------------
def candle_pattern(o, h, l, c):
    body = abs(c - o)
    upper = h - max(o, c)
    lower = min(o, c) - l

    # Avoid divide by zero
    rng = max(h - l, 1e-9)

    # Doji
    if body <= 0.1 * rng:
        return "Doji", "Neutral candle (indecision)."

    # Hammer / Hanging Man
    if lower > 2 * body and upper < body:
        return "Hammer", "Long lower wick indicates rejection from lows."

    # Shooting Star
    if upper > 2 * body and lower < body:
        return "Shooting Star", "Long upper wick indicates rejection from highs."

    return "Normal", "No strong single-candle pattern."

# -----------------------------
# Fetch data
# -----------------------------
def fetch_klines(symbol="XAUUSDT", interval="1m", limit=120):
    # Binance doesn't have XAUUSDT spot for all regions.
    # You can use BTCUSDT/ETHUSDT or any available symbol.
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    res = requests.get(BINANCE_URL, params=params, timeout=10)
    res.raise_for_status()
    data = res.json()

    df = pd.DataFrame(data, columns=[
        "open_time","open","high","low","close","volume",
        "close_time","qav","trades","tbbav","tbqav","ignore"
    ])
    for col in ["open","high","low","close","volume"]:
        df[col] = df[col].astype(float)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms", utc=True)
    return df

# -----------------------------
# Brain: scoring based signal
# -----------------------------
def analyze(df):
    close = df["close"]
    df["ema20"] = ema(close, 20)
    df["ema50"] = ema(close, 50)
    df["rsi14"] = rsi(close, 14)

    macd_line, signal_line, hist = macd(close)
    df["macd"] = macd_line
    df["macd_signal"] = signal_line
    df["macd_hist"] = hist

    last = df.iloc[-1]
    prev = df.iloc[-2]

    # Pattern
    pat, pat_reason = candle_pattern(
        last["open"], last["high"], last["low"], last["close"]
    )

    # Score system (simple but effective)
    score = 0
    reasons_up = []
    reasons_down = []
    warnings = []

    # EMA trend
    if last["ema20"] > last["ema50"]:
        score += 2
        reasons_up.append("EMA20 above EMA50 (uptrend bias).")
    else:
        score -= 2
        reasons_down.append("EMA20 below EMA50 (downtrend bias).")

    # Price vs EMA20
    if last["close"] > last["ema20"]:
        score += 1
        reasons_up.append("Price above EMA20.")
    else:
        score -= 1
        reasons_down.append("Price below EMA20.")

    # RSI
    r = float(last["rsi14"]) if not np.isnan(last["rsi14"]) else 50
    if r < 30:
        score += 1
        reasons_up.append(f"RSI {r:.1f} (oversold bounce chance).")
    elif r > 70:
        score -= 1
        reasons_down.append(f"RSI {r:.1f} (overbought pullback chance).")

    # MACD histogram direction
    if last["macd_hist"] > prev["macd_hist"]:
        score += 1
        reasons_up.append("MACD momentum increasing.")
    else:
        score -= 1
        reasons_down.append("MACD momentum decreasing.")

    # Pattern effect
    if pat == "Hammer":
        score += 1
        reasons_up.append("Hammer candle → buyers defended lows.")
    elif pat == "Shooting Star":
        score -= 1
        reasons_down.append("Shooting star → sellers defended highs.")
    elif pat == "Doji":
        warnings.append("Doji → indecision, signal weaker.")

    # Volatility filter (avoid choppy)
    recent_range = (df["high"].tail(10) - df["low"].tail(10)).mean()
    if recent_range / last["close"] < 0.0005:
        warnings.append("Low volatility → sideways/chop risk.")
    if recent_range / last["close"] > 0.01:
        warnings.append("High volatility → risky entries.")

    # Signal
    if score >= 2:
        signal = "UP"
        confidence = min(90, 55 + score * 10)
        reason_list = reasons_up + (reasons_down[:1] if reasons_down else [])
    elif score <= -2:
        signal = "DOWN"
        confidence = min(90, 55 + abs(score) * 10)
        reason_list = reasons_down + (reasons_up[:1] if reasons_up else [])
    else:
        signal = "NO TRADE"
        confidence = 50
        reason_list = ["Mixed signals / choppy market."]

    return {
        "signal": signal,
        "confidence": int(confidence),
        "pattern": pat,
        "pattern_note": pat_reason,
        "reasons": reason_list[:5],
        "warnings": warnings[:3],
        "price": float(last["close"]),
        "time_utc": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/predict")
def predict():
    symbol = request.args.get("symbol", "BTCUSDT")   # Change default if needed
    interval = request.args.get("interval", "1m")
    df = fetch_klines(symbol=symbol, interval=interval, limit=120)
    out = analyze(df)
    out["symbol"] = symbol
    out["interval"] = interval
    return jsonify(out)

if __name__ == "__main__":
    # Run:
    # python backend.py
    app.run(host="0.0.0.0", port=5000, debug=True)
