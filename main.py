import yfinance as yf
import os
import requests
import pandas as pd
from datetime import datetime

# --- DEIN AKTIEN-PORTFOLIO ---
MEINE_AKTIEN = [
    {"symbol": "AAPL",    "name": "Apple",           "sector": "📱 Technologie"},
    {"symbol": "MSFT",    "name": "Microsoft",       "sector": "📱 Technologie"},
    {"symbol": "NVDA",    "name": "Nvidia",          "sector": "📱 Technologie"},
    
    {"symbol": "TSLA",    "name": "Tesla",           "sector": "🚗 Konsum & Auto"},
    {"symbol": "AMZN",    "name": "Amazon",          "sector": "🚗 Konsum & Auto"},
    {"symbol": "VOW3.DE", "name": "VW",              "sector": "🚗 Konsum & Auto"},
    
    {"symbol": "ALV.DE",  "name": "Allianz",         "sector": "💰 Finanzen"},
    
    {"symbol": "BTC-USD", "name": "Bitcoin",         "sector": "🪙 Krypto-Assets"}
]

def get_usd_to_eur_rate():
    """Holt den aktuellen Umrechnungskurs von Dollar zu Euro"""
    try:
        # Wir holen uns das Paar EURUSD=X (Wie viel Dollar ist 1 Euro wert?)
        # Beispiel: Kurs 1.05 bedeutet 1€ = 1.05$
        ticker = yf.Ticker("EURUSD=X")
        hist = ticker.history(period="1d")
        if not hist.empty:
            rate = float(hist['Close'].iloc[-1])
            return 1 / rate # Umkehrung: Wie viel Euro ist 1 Dollar wert?
    except:
        pass
    return 0.95 # Fallback (Notfallwert), falls API streikt

# Den Kurs holen wir nur 1x am Anfang, um Zeit zu sparen
AKTUELLER_USD_EUR_KURS = get_usd_to_eur_rate()

def telegram_senden(nachricht):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id:
        print("Fehler: Token/Chat ID fehlen.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    daten = {'chat_id': chat_id, 'text': nachricht, 'parse_mode': 'HTML'}
    requests.post(url, data=daten)

def strategie_check(stock_data):
    symbol = stock_data["symbol"]
    name = stock_data["name"]
    
    try:
        ticker = yf.Ticker(symbol)
        
        # Währung prüfen (USD oder EUR?)
        # fast_info ist schneller als info
        try:
            currency = ticker.fast_info['currency']
        except:
            currency = "USD" # Annahme bei Fehler

        hist = ticker.history(period="1y")
        if hist.empty: return None
        
        raw_price = float(hist['Close'].iloc[-1])
        
        # --- WÄHRUNGSUMRECHNUNG ---
        if currency == "USD":
            # Wenn Aktie in Dollar ist, rechnen wir in Euro um
            preis_in_euro = raw_price * AKTUELLER_USD_EUR_KURS
        else:
            # Wenn Aktie schon in EUR ist (z.B. VW), lassen wir es so
            preis_in_euro = raw_price

        preis_anzeige = round(preis_in_euro, 2)
        
        # --- BERECHNUNG ---
        sma_50 = hist['Close'].rolling(window=50).mean().iloc[-1]
        sma_200 = hist['Close'].rolling(window=200).mean().iloc[-1]
        
        delta = hist['Close'].diff()
        gewinn = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        verlust = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gewinn / verlust
        rsi = 100 - (100 / (1 + rs))
        rsi_wert = round(float(rsi.iloc[-1]), 1)

        # --- SIGNAL LOGIK ---
        signal = "⚪ Halten" 
        
        if rsi_wert < 30: 
            signal = "🟢 <b>KAUFEN</b> (Billig)"
        elif sma_50 > sma_200 and rsi_wert < 50: 
            signal = "🟢 <b>KAUFEN</b> (Trend)"
            
        if rsi_wert > 70: 
            signal = "🔴 <b>VERKAUFEN</b> (Teuer)"
        elif sma_50 < sma_200: 
            signal = "🔴 <b>VERKAUFEN</b> (Abwärtstrend)"

        # --- OUTPUT ---
        text = f"<b>{name}</b>: {preis_anzeige} €\n"
        text += f"{signal}\n\n" 
        
        return text

    except Exception as e:
        print(f"Fehler bei {name}: {e}")
        return None

if __name__ == "__main__":
    datum = datetime.now().strftime('%d.%m')
    bericht = f"📊 <b>Portfolio {datum}</b>\n\n"
    
    sektor_ergebnisse = {}
    
    print(f"Starte Analyse (Wechselkurs genutz: {round(AKTUELLER_USD_EUR_KURS, 2)})...")
    
    for aktie in MEINE_AKTIEN:
        ergebnis = strategie_check(aktie)
        if ergebnis:
            sektor = aktie["sector"]
            if sektor not in sektor_ergebnisse:
                sektor_ergebnisse[sektor] = ""
            sektor_ergebnisse[sektor] += ergebnis
            print(f"✅ {aktie['name']} fertig.")

    # Bericht zusammenbauen
    has_content = False
    for sektor, inhalt in sektor_ergebnisse.items():
        bericht += f"<b>--- {sektor} ---</b>\n"
        bericht += inhalt
        has_content = True

    if has_content:
        telegram_senden(bericht)
        print("Nachricht gesendet.")
    else:
        print("Keine Daten verfügbar.")
