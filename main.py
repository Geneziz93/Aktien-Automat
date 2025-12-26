import yfinance as yf
import os
import requests
from datetime import datetime

# --- DEIN AKTIEN-TELEFONBUCH ---
# Links: Das Kürzel für den Computer
# Rechts: Der Name für dich (in Anführungszeichen)
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
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    daten = {'chat_id': chat_id, 'text': nachricht, 'parse_mode': 'Markdown'}
    requests.post(url, data=daten)

def strategie_check(symbol, name):
    try:
        # Daten laden
        df = yf.download(symbol, period="1y", interval="1d", progress=False)
        if len(df) < 200: return None

        preis = round(float(df['Close'].iloc[-1]), 2)
        
        # --- BERECHNUNGEN ---
        sma_50 = df['Close'].rolling(window=50).mean().iloc[-1]
        sma_200 = df['Close'].rolling(window=200).mean().iloc[-1]
        
        delta = df['Close'].diff()
        gewinn = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        verlust = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gewinn / verlust
        rsi = 100 - (100 / (1 + rs))
        rsi_wert = round(float(rsi.iloc[-1]), 1)

        # --- AMPEL SYSTEM ---
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

        # Hier nutzen wir jetzt DEINEN Namen
        return f"🏢 *{name}* ({symbol}): {preis} €\n👉 {signal}\n_{grund}_ (RSI: {rsi_wert})\n"

    except Exception as e:
        return f"⚠️ Fehler bei {name}: Daten nicht verfügbar.\n"

if __name__ == "__main__":
    datum = datetime.now().strftime('%d.%m.%Y')
    bericht = f"📊 **Marktbericht {datum}** 📊\n\n"
    
    # Wir gehen durch das Telefonbuch (Kürzel UND Name)
    for symbol, name in MEINE_AKTIEN.items():
        ergebnis = strategie_check(symbol, name)
        if ergebnis:
            bericht += ergebnis + "\n"
    
    telegram_senden(bericht)
