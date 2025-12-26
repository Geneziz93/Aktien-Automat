import yfinance as yf
import os
import requests
import pandas as pd
from datetime import datetime

# --- DEINE AKTIEN ---
MEINE_AKTIEN = {
    'AAPL': 'Apple',
    'TSLA': 'Tesla',
    'MSFT': 'Microsoft',
    'AMZN': 'Amazon',
    'BTC-USD': 'Bitcoin',
    'VOW3.DE': 'VW (Volkswagen)',
    'ALV.DE': 'Allianz',
    'NVDA': 'Nvidia'
}

def telegram_senden(nachricht):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id:
        print("Fehler: Token/Chat ID fehlen.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    # disable_web_page_preview=True sorgt dafür, dass die Nachricht klein bleibt (keine großen Vorschaubilder der Links)
    daten = {'chat_id': chat_id, 'text': nachricht, 'parse_mode': 'HTML', 'disable_web_page_preview': True}
    requests.post(url, data=daten)

def hol_nachrichten(ticker_obj):
    try:
        news = ticker_obj.news
        if news and len(news) > 0:
            titel = news[0].get('title', 'Info')
            link = news[0].get('link', '')
            # Der Link ist jetzt hinter dem Wort "News" oder der Headline versteckt
            return f"<a href='{link}'>{titel}</a>"
    except:
        pass
    return "Keine News"

def strategie_check(symbol, name):
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1y")
        if hist.empty: return None
        
        preis = round(float(hist['Close'].iloc[-1]), 2)
        
        # --- BERECHNUNG (Läuft unsichtbar im Hintergrund) ---
        sma_50 = hist['Close'].rolling(window=50).mean().iloc[-1]
        sma_200 = hist['Close'].rolling(window=200).mean().iloc[-1]
        
        delta = hist['Close'].diff()
        gewinn = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        verlust = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gewinn / verlust
        rsi = 100 - (100 / (1 + rs))
        rsi_wert = round(float(rsi.iloc[-1]), 1)

        # --- SIGNAL GEBUNG ---
        signal = "⚪ Halten" 
        
        # Logik
        if rsi_wert < 30: 
            signal = "🟢 <b>KAUFEN</b> (Billig)"
        elif sma_50 > sma_200 and rsi_wert < 50: 
            signal = "🟢 <b>KAUFEN</b> (Trend)"
            
        if rsi_wert > 70: 
            signal = "🔴 <b>VERKAUFEN</b> (Teuer)"
        elif sma_50 < sma_200: 
            signal = "🔴 <b>VERKAUFEN</b> (Abwärtstrend)"

        # News holen
        news_link = hol_nachrichten(ticker)

        # --- KOMPAKTE AUSGABE ---
        # Nur 3 Zeilen pro Aktie:
        # 1. Name & Preis
        # 2. Signal
        # 3. News Link
        
        text = f"<b>{name}</b>: {preis} €\n"
        text += f"👉 {signal}\n"
        text += f"📰 {news_link}\n\n" 
        
        return text

    except Exception as e:
        print(f"Fehler bei {name}: {e}")
        return None

if __name__ == "__main__":
    datum = datetime.now().strftime('%d.%m')
    # Header noch minimalistischer
    bericht = f"📊 <b>Markt {datum}</b>\n\n"
    
    erfolg = False
    for symbol, name in MEINE_AKTIEN.items():
        block = strategie_check(symbol, name)
        if block:
            bericht += block
            erfolg = True
            
    if erfolg:
        telegram_senden(bericht)
