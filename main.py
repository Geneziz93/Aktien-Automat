import yfinance as yf
import os
import requests
import pandas as pd
from datetime import datetime

# --- DEIN AKTIEN-PORTFOLIO MIT SEKTOREN ---
# Wir nutzen jetzt eine Liste, damit wir Sektoren zuordnen können.
# GICS Sektoren (vereinfacht): Technologie, Zykl. Konsum, Finanzen, Industrie, Krypto etc.
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

def telegram_senden(nachricht):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id:
        print("Fehler: Token/Chat ID fehlen.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    daten = {'chat_id': chat_id, 'text': nachricht, 'parse_mode': 'HTML', 'disable_web_page_preview': True}
    requests.post(url, data=daten)

def hol_nachrichten(ticker_obj):
    try:
        news = ticker_obj.news
        if news and len(news) > 0:
            # Wir nehmen die aktuellste News
            titel = news[0].get('title', 'Info')
            link = news[0].get('link', '')
            return f"<a href='{link}'>{titel}</a>"
    except:
        pass
    return None # WICHTIG: Gibt None zurück, wenn nichts gefunden wurde

def strategie_check(stock_data):
    symbol = stock_data["symbol"]
    name = stock_data["name"]
    
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1y")
        if hist.empty: return None
        
        preis = round(float(hist['Close'].iloc[-1]), 2)
        
        # --- BERECHNUNG (Hintergrund) ---
        sma_50 = hist['Close'].rolling(window=50).mean().iloc[-1]
        sma_200 = hist['Close'].rolling(window=200).mean().iloc[-1]
        
        delta = hist['Close'].diff()
        gewinn = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        verlust = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gewinn / verlust
        rsi = 100 - (100 / (1 + rs))
        rsi_wert = round(float(rsi.iloc[-1]), 1)

        # --- SIGNAL ---
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
        text = f"<b>{name}</b>: {preis} €\n"
        text += f"👉 {signal}\n"
        
        # News nur anzeigen, wenn vorhanden
        news_link = hol_nachrichten(ticker)
        if news_link:
            text += f"📰 {news_link}\n"
        
        text += "\n" # Leerzeile für Abstand
        
        return text

    except Exception as e:
        print(f"Fehler bei {name}: {e}")
        return None

if __name__ == "__main__":
    datum = datetime.now().strftime('%d.%m')
    bericht = f"📊 <b>Portfolio {datum}</b>\n\n"
    
    # Ergebnisse sammeln und nach Sektoren ordnen
    sektor_ergebnisse = {}
    
    print("Starte Analyse...")
    
    for aktie in MEINE_AKTIEN:
        ergebnis = strategie_check(aktie)
        if ergebnis:
            sektor = aktie["sector"]
            if sektor not in sektor_ergebnisse:
                sektor_ergebnisse[sektor] = ""
            sektor_ergebnisse[sektor] += ergebnis
            print(f"✅ {aktie['name']} analysiert.")

    # Bericht zusammenbauen (Sektor für Sektor)
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
