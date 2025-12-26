import yfinance as yf
import os
import requests
from datetime import datetime

MEINE_AKTIEN = ['AAPL', 'TSLA', 'MSFT', 'AMZN', 'BTC-USD', 'VOW3.DE']

def telegram_senden(nachricht):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    # Prüfung 1: Sind die Zugangsdaten überhaupt da?
    if not token:
        print("FEHLER: 'TELEGRAM_TOKEN' wurde in den Secrets nicht gefunden!")
        return
    if not chat_id:
        print("FEHLER: 'TELEGRAM_CHAT_ID' wurde in den Secrets nicht gefunden!")
        return

    print(f"Versuche Nachricht zu senden an ID: {chat_id[:3]}***") # Zeigt den Anfang der ID zur Kontrolle

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    daten = {'chat_id': chat_id, 'text': nachricht, 'parse_mode': 'Markdown'}
    
    # Prüfung 2: Was sagt der Telegram-Server?
    antwort = requests.post(url, data=daten)
    
    if antwort.status_code == 200:
        print("ERFOLG: Nachricht wurde laut Telegram zugestellt!")
    else:
        print(f"FEHLER von Telegram (Code {antwort.status_code}):")
        print(antwort.text) # Hier steht der genaue Grund (z.B. 'Chat not found')

def strategie_check(symbol):
    try:
        df = yf.download(symbol, period="1y", interval="1d", progress=False)
        if len(df) < 200: return None

        preis = round(float(df['Close'].iloc[-1]), 2)
        sma_50 = df['Close'].rolling(window=50).mean().iloc[-1]
        sma_200 = df['Close'].rolling(window=200).mean().iloc[-1]
        
        delta = df['Close'].diff()
        gewinn = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        verlust = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gewinn / verlust
        rsi = 100 - (100 / (1 + rs))
        rsi_aktuell = round(float(rsi.iloc[-1]), 2)

        signal = "⚪ HALTEN"
        if rsi_aktuell < 30: signal = "🟢 KAUFEN (RSI < 30)"
        elif sma_50 > sma_200 and rsi_aktuell < 50: signal = "🟢 KAUFEN (Trend)"
        if rsi_aktuell > 70: signal = "🔴 VERKAUFEN (RSI > 70)"
        elif sma_50 < sma_200: signal = "🔴 VORSICHT (Trendbruch)"

        return f"*{symbol}*: {preis} €\n{signal} (RSI: {rsi_aktuell})\n"
    except Exception as e:
        print(f"Fehler bei {symbol}: {e}")
        return None

if __name__ == "__main__":
    nachricht = f"📅 **Check vom {datetime.now().strftime('%d.%m.%Y')}**\n\n"
    for aktie in MEINE_AKTIEN:
        ergebnis = strategie_check(aktie)
        if ergebnis: nachricht += ergebnis + "\n"
    telegram_senden(nachricht)
