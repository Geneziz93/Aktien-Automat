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

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    daten = {'chat_id': chat_id, 'text': nachricht, 'parse_mode': 'HTML', 'disable_web_page_preview': True}
    requests.post(url, data=daten)

def hol_nachrichten(ticker_obj):
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
    if val is None or val == "N/A": return "-"
    try:
        return f"{round(float(val), 2)}{suffix}"
    except:
        return "-"

# --- TEXT-BEWERTUNGSSYSTEM (Details als Text) ---

def bewerte_kgv(kgv):
    if kgv is None: return ""
    if kgv < 20: return "<b>(GÜNSTIG)</b>"
    if kgv < 30: return "(NORMAL)"
    if kgv < 50: return "(TEUER)"
    return "<b>(! SEHR TEUER !)</b>"

def bewerte_rsi(rsi):
    if rsi is None: return ""
    if rsi < 40: return "<b>(KAUFZONE)</b>"
    if rsi < 60: return "(NEUTRAL)"
    if rsi < 75: return "(TEUER)"
    return "<b>(! ÜBERHITZT !)</b>"

def bewerte_peg(peg):
    if peg is None: return ""
    if peg < 1.0: return "<b>(GUT)</b>"
    if peg < 2.0: return "(NEUTRAL)"
    if peg < 3.0: return "(TEUER)"
    return "<b>(! SEHR TEUER !)</b>"

def bewerte_dividende(div):
    if div is None: return ""
    if div > 0.03: return "<b>(TOP)</b>"
    if div > 0.015: return "(OK)"
    if div > 0: return "(WENIG)"
    return "(KEINE)"

def strategie_check(symbol, name):
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1y")
        if hist.empty: return None
        
        preis = round(float(hist['Close'].iloc[-1]), 2)
        
        # --- TECHNIK ---
        sma_50 = hist['Close'].rolling(window=50).mean().iloc[-1]
        sma_200 = hist['Close'].rolling(window=200).mean().iloc[-1]
        
        delta = hist['Close'].diff()
        gewinn = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        verlust = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gewinn / verlust
        rsi = 100 - (100 / (1 + rs))
        rsi_wert = round(float(rsi.iloc[-1]), 1)

        # --- SIGNAL MIT EMOJIS (Hier ist die Änderung) ---
        signal = "⚪ HALTEN" # Standard
        
        # Kaufen
        if rsi_wert < 30: 
            signal = "🟢 <b>KAUFEN</b> (Schnäppchen)"
        elif sma_50 > sma_200 and rsi_wert < 50: 
            signal = "🟢 <b>KAUFEN</b> (Trend)"
            
        # Verkaufen
        if rsi_wert > 70: 
            signal = "🔴 <b>VERKAUFEN</b> (Überhitzt)"
        elif sma_50 < sma_200: 
            signal = "🔴 <b>VERKAUFEN</b> (Abwärtstrend)"

        # --- FUNDAMENTALS ---
        info = ticker.info
        kgv = info.get('trailingPE')
        kbv = info.get('priceToBook')
        kuv = info.get('priceToSalesTrailing12Months')
        div_yield = info.get('dividendYield')
        peg = info.get('pegRatio')
        eps = info.get('trailingEps')

        div_text = f"{round(div_yield * 100, 2)}%" if div_yield else "0%"
        
        # Bewertungen holen
        t_rsi = bewerte_rsi(rsi_wert)
        t_kgv = bewerte_kgv(kgv)
        t_peg = bewerte_peg(peg)
        t_div = bewerte_dividende(div_yield)
        
        # --- OUTPUT DESIGN ---
        text = f"<b>🏢 {name} ({symbol})</b>\n"
        text += f"Preis: {preis} €\n"
        text += f"Signal: {signal}\n" # Hier wird das Emoji-Signal eingefügt
        
        if symbol == "BTC-USD":
            text += f"RSI: {rsi_wert} {t_rsi}\n"
        else:
            text += f"------------------------------\n"
            text += f"RSI: {rsi_wert} {t_rsi}\n"
            text += f"KGV: {format_number(kgv)} {t_kgv}\n"
            text += f"PEG: {format_number(peg)} {t_peg}\n"
            text += f"Div: {div_text} {t_div}\n"
            text += f"KBV: {format_number(kbv)} | KUV: {format_number(kuv)}\n"
        
        news_headline = hol_nachrichten(ticker)
        text += f"\n📰 <b>News:</b> {news_headline}\n"
        text += "==============================\n"
        
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
