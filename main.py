from flask import Flask, request
from binance.client import Client
from binance.enums import *
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)
app = Flask(__name__)

# Define S and A coins only
ALLOWED_TICKERS = [
    "ETHUSDT", "BNBUSDT", "ADAUSDT", "DOGEUSDT", "SOLUSDT",  # S Coins
    "AVAXUSDT", "DOTUSDT", "XRPUSDT", "AAVEUSDT", "UNIUSDT", "TRXUSDT"  # A Coins
]

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "HTML"
    }
    requests.post(url, data=payload)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("Received Alert:", data)

    try:
        symbol = data["ticker"]
        direction = data["dir"]
        qty = float(data["qty"])
        entry = float(data["entry"])
        tp = float(data["tp"])
        sl = float(data["sl"])

        if symbol not in ALLOWED_TICKERS:
            return "Coin not authorized", 403

        side = SIDE_BUY if direction == "LONG" else SIDE_SELL
        opposite = SIDE_SELL if side == SIDE_BUY else SIDE_BUY

        # Place LIMIT order
        order = client.create_order(
            symbol=symbol,
            side=side,
            type=ORDER_TYPE_LIMIT,
            timeInForce=TIME_IN_FORCE_GTC,
            quantity=qty,
            price=str(entry)
        )

        # TP: 50% LIMIT
        tp_qty = round(qty * 0.5, 6)
        client.create_order(
            symbol=symbol,
            side=opposite,
            type=ORDER_TYPE_LIMIT,
            timeInForce=TIME_IN_FORCE_GTC,
            quantity=tp_qty,
            price=str(tp)
        )

        # SL: 100% MARKET via stop-limit
        client.create_order(
            symbol=symbol,
            side=opposite,
            type=ORDER_TYPE_STOP_LOSS_LIMIT,
            quantity=qty,
            price=str(sl),  # limit price
            stopPrice=str(sl),
            timeInForce=TIME_IN_FORCE_GTC
        )

        # Telegram confirmation
        send_telegram(
            f"🚀 <b>{symbol}</b> {direction} Entry placed\n"
            f"• Entry: {entry}\n• SL: {sl}\n• TP: {tp}\n"
            f"• Qty: {qty}\n\n⚠️ TSL starts after TP is hit"
        )

        return "Trade executed", 200

    except Exception as e:
        send_telegram(f"❌ ERROR: {str(e)}")
        return f"Error: {str(e)}", 500

if __name__ == "__main__":
    app.run(port=5000)
