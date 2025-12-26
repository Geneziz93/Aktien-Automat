import yfinance as yf
import os
import requests
from datetime import datetime

# --- HIER DEINE AKTIEN EINTRAGEN ---
# Kürzel findest du auf Yahoo Finance (z.B. VOW3.DE für VW, MSFT für Microsoft)
MEINE_AKTIEN = ['AAPL', 'TSLA', 'MSFT', 'AMZN', 'BTC-USD', 'VOW3.DE']

def telegram_senden(nachricht):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    daten = {'chat_id': chat_id, 'text': nachricht, 'parse_mode': 'Markdown'}
    requests.post(url, data=daten)

def strategie_check(symbol):
    try:
        # Daten laden (letztes Jahr)
        df = yf.download(symbol, period="1y", interval="1d", progress=False)
        if len(df) < 200: return None # Zu wenig Daten

        preis = round(float(df['Close'].iloc[-1]), 2)
        
        # Indikatoren berechnen
        sma_50 = df['Close'].rolling(window=50).mean().iloc[-1]
        sma_200 = df['Close'].rolling(window=200).mean().iloc[-1]
        
        # RSI Berechnung
        delta = df['Close'].diff()
        gewinn = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        verlust = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gewinn / verlust
        rsi = 100 - (100 / (1 + rs))
        rsi_aktuell = round(float(rsi.iloc[-1]), 2)

        # Entscheidung
        signal = "⚪ HALTEN"
        detail = "Kein klares Signal."

        # KAUF LOGIK
        if rsi_aktuell < 30:
            signal = "🟢 KAUFEN (Schnäppchen)"
            detail = "RSI unter 30 (Überverkauft)."
        elif sma_50 > sma_200 and rsi_aktuell < 50:
            signal = "🟢 KAUFEN (Trend)"
            detail = "Aufwärtstrend + guter Preis."

        # VERKAUF LOGIK
        if rsi_aktuell > 70:
            signal = "🔴 VERKAUFEN (Teuer)"
            detail = "RSI über 70 (Überkauft)."
        elif sma_50 < sma_200:
            signal = "🔴 VORSICHT (Abwärtstrend)"
            detail = "50-Tage Linie unter 200-Tage Linie."

        return f"*{symbol}*: {preis} €\nSignal: {signal}\nInfo: {detail} (RSI: {rsi_aktuell})\n"
    
    except Exception as e:
        return None

if __name__ == "__main__":
    nachricht = f"📅 **Check vom {datetime.now().strftime('%d.%m.%Y')}**\n\n"
    for aktie in MEINE_AKTIEN:
        ergebnis = strategie_check(aktie)
        if ergebnis:
            nachricht += ergebnis + "\n"
    
    telegram_senden(nachricht)
