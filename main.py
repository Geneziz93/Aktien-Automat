import yfinance as yf
import os
import requests
import pandas as pd
from datetime import datetime

# --- DEIN AKTIEN-TELEFONBUCH ---
MEINE_AKTIEN = {
    'AAPL': 'Apple',
    'TSLA': 'Tesla',
    'MSFT': 'Microsoft',
    'AMZN': 'Amazon',
    'BTC-USD': 'Bitcoin',
    'VOW3.DE': 'VW (Volkswagen)'
}

def telegram_senden(nachricht):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id:
        print("Fehler: Token oder Chat ID fehlen.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    daten = {'chat_id': chat_id, 'text': nachricht, 'parse_mode': 'Markdown'}
    requests.post(url, data=daten)

def strategie_check(symbol, name):
    try:
        # 1. Daten laden (STABILERE METHODE)
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="1y")
        
        # Prüfung: Ist die Tabelle leer?
        if df.empty:
            print(f"Keine Daten für {symbol} erhalten.")
            return None

        preis = round(float(df['Close'].iloc[-1]), 2)
        
        # 2. Berechnungen
        sma_50 = df['Close'].rolling(window=50).mean().iloc[-1]
        sma_200 = df['Close'].rolling(window=200).mean().iloc[-1]
        
        delta = df['Close'].diff()
        gewinn = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        verlust = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gewinn / verlust
        rsi = 100 - (100 / (1 + rs))
        rsi_wert = round(float(rsi.iloc[-1]), 1)

        # 3. Ampel-Logik
        signal = "⚪ HALTEN"
        grund = "Neutral"

        # KAUFEN
        if rsi_wert < 30:
            signal = "🟢 KAUFEN"
            grund = "Stark unterbewertet"
        elif sma_50 > sma_200 and rsi_wert < 50:
            signal = "🟢 KAUFEN"
            grund = "Aufwärtstrend + Guter Preis"

        # VERKAUFEN
        if rsi_wert > 70:
            signal = "🔴 VERKAUFEN"
            grund = "Überhitzt (zu teuer)"
        elif sma_50 < sma_200 and rsi_wert > 50:
            signal = "🔴 VERKAUFEN"
            grund = "Abwärtstrend"

        return f"🏢 *{name}*: {preis} €\n👉 {signal}\n_{grund}_ (RSI: {rsi_wert})\n"

    except Exception as e:
        # Hier drucken wir den WAHREN Fehler ins Protokoll für dich
        print(f"FEHLER bei {name} ({symbol}): {e}")
        return f"⚠️ Fehler bei {name}: Daten konnten nicht berechnet werden.\n"

if __name__ == "__main__":
    datum = datetime.now().strftime('%d.%m.%Y')
    bericht = f"📊 **Marktbericht {datum}** 📊\n\n"
    
    erfolgreich = False
    for symbol, name in MEINE_AKTIEN.items():
        ergebnis = strategie_check(symbol, name)
        if ergebnis:
            bericht += ergebnis + "\n"
            if "Fehler" not in ergebnis:
                erfolgreich = True
    
    # Nur senden, wenn zumindest eine Aktie geklappt hat oder Fehler berichtet werden sollen
    if erfolgreich or len(MEINE_AKTIEN) > 0:
        telegram_senden(bericht)
