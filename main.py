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
    'VOW3.DE': 'VW (Volkswagen)',
    'ALV.DE': 'Allianz',
    'NVDA': 'Nvidia'
}

def telegram_senden(nachricht):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id:
        print("Fehler: Token oder Chat ID fehlen.")
        return

    # Telegram hat ein Limit für Nachrichtenlänge, daher splitten wir bei Bedarf
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    # Nachricht senden (Markdown deaktiviert für Links, falls diese Sonderzeichen enthalten)
    # Wir nutzen HTML für fettgedruckten Text und Links
    daten = {'chat_id': chat_id, 'text': nachricht, 'parse_mode': 'HTML', 'disable_web_page_preview': True}
    requests.post(url, data=daten)

def hol_nachrichten(ticker_obj):
    """Holt die aktuellste News-Schlagzeile"""
    try:
        news = ticker_obj.news
        if news and len(news) > 0:
            titel = news[0].get('title', 'Keine Überschrift')
            link = news[0].get('link', '')
            return f"<a href='{link}'>{titel}</a>"
    except:
        pass
    return "Keine aktuellen News gefunden."

def format_number(val, suffix=""):
    """Hilfsfunktion um N/A zu vermeiden"""
    if val is None or val == "N/A":
        return "-"
    try:
        return f"{round(float(val), 2)}{suffix}"
    except:
        return "-"

def strategie_check(symbol, name):
    try:
        ticker = yf.Ticker(symbol)
        
        # 1. Historische Daten für Charttechnik (Preis, RSI, SMA)
        hist = ticker.history(period="1y")
        if hist.empty: return None
        
        preis = round(float(hist['Close'].iloc[-1]), 2)
        
        # --- TECHNISCHE ANALYSE (Charttechnik) ---
        sma_50 = hist['Close'].rolling(window=50).mean().iloc[-1]
        sma_200 = hist['Close'].rolling(window=200).mean().iloc[-1]
        
        delta = hist['Close'].diff()
        gewinn = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        verlust = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gewinn / verlust
        rsi = 100 - (100 / (1 + rs))
        rsi_wert = round(float(rsi.iloc[-1]), 1)

        # Ampel Signal (Technisch)
        signal = "⚪ HALTEN"
        if rsi_wert < 30: signal = "🟢 KAUFEN (Überverkauft)"
        elif sma_50 > sma_200 and rsi_wert < 50: signal = "🟢 KAUFEN (Trend)"
        if rsi_wert > 70: signal = "🔴 VERKAUFEN (Überkauft)"
        elif sma_50 < sma_200: signal = "🔴 VERKAUFEN (Abwärtstrend)"

        # --- FUNDAMENTALE ANALYSE (Kennzahlen) ---
        # info Dictionary abrufen (Kann langsam sein)
        info = ticker.info
        
        # Daten sicher extrahieren (mit Fallback auf None)
        kgv = info.get('trailingPE') # Kurs-Gewinn
        kbv = info.get('priceToBook') # Kurs-Buchwert
        kuv = info.get('priceToSalesTrailing12Months') # Kurs-Umsatz
        div_yield = info.get('dividendYield') # Dividende (kommt als 0.05 für 5%)
        roe = info.get('returnOnEquity') # Eigenkapitalrendite
        peg = info.get('pegRatio') # PEG als Ersatz für DCF (Wachstum vs Bewertung)
        eps = info.get('trailingEps') # Gewinn pro Aktie

        # Formatierung der Kennzahlen
        div_text = f"{round(div_yield * 100, 2)}%" if div_yield else "0%"
        roe_text = f"{round(roe * 100, 2)}%" if roe else "-"
        
        # Bewertungskommentar (Fundamental)
        bewertung = "Fair/Neutral"
        if kgv and kgv < 15 and (peg and peg < 1): bewertung = "🟢 Günstig bewertet"
        if kgv and kgv > 50: bewertung = "🔴 Teuer (Wachstum eingepreist?)"
        if symbol == "BTC-USD": bewertung = "Crypto (Keine Fundamentaldaten)"

        # --- NACHRICHTEN ---
        news_headline = hol_nachrichten(ticker)

        # --- ZUSAMMENBAU DER NACHRICHT ---
        text = f"<b>🏢 {name} ({symbol})</b>: {preis} €\n"
        text += f"Signal: {signal} (RSI: {rsi_wert})\n"
        text += f"<i>Bewertung: {bewertung}</i>\n\n"
        
        # Fundamentaldaten Block (Nur wenn keine Crypto)
        if symbol != "BTC-USD":
            text += f"📊 <b>Kennzahlen:</b>\n"
            text += f"• KGV: {format_number(kgv)} | KBV: {format_number(kbv)}\n"
            text += f"• KUV: {format_number(kuv)} | PEG: {format_number(peg)}\n"
            text += f"• Div: {div_text} | ROE: {roe_text}\n"
            text += f"• EPS: {format_number(eps)} €\n"
        
        text += f"\n📰 <b>News:</b> {news_headline}\n"
        text += "------------------------------\n"
        
        return text

    except Exception as e:
        print(f"Fehler bei {name}: {e}")
        return None

if __name__ == "__main__":
    datum = datetime.now().strftime('%d.%m.%Y')
    bericht = f"📊 <b>Marktbericht {datum}</b> 📊\n\n"
    
    erfolg = False
    for symbol, name in MEINE_AKTIEN.items():
        block = strategie_check(symbol, name)
        if block:
            bericht += block
            erfolg = True
            
    if erfolg:
        telegram_senden(bericht)
    else:
        print("Keine Daten konnten abgerufen werden.")
