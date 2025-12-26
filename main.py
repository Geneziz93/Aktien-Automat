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

# --- DAS FARB-SYSTEM (Vereinfacht: Ohne Hellgrün) ---
# 🟢 = Gut | 🔵 = Neutral | 🟠 = Schlecht/Teuer | 🔴 = Sehr schlecht

def bewerte_kgv(kgv):
    if kgv is None: return ""
    if kgv < 20: return "🟢"      # Günstig (Zusammengefasst)
    if kgv < 30: return "🔵"      # Normal
    if kgv < 50: return "🟠"      # Teuer
    return "🔴"                   # Sehr teuer

def bewerte_rsi(rsi):
    if rsi is None: return ""
    if rsi < 40: return "🟢"      # Kaufzone (Erweitert)
    if rsi < 60: return "🔵"      # Neutral
    if rsi < 75: return "🟠"      # Eher teuer
    return "🔴"                   # Überkauft

def bewerte_peg(peg):
    if peg is None: return ""
    if peg < 1.0: return "🟢"     # Gut
    if peg < 2.0: return "🔵"     # Neutral
    if peg < 3.0: return "🟠"     # Teuer
    return "🔴"                   # Sehr teuer

def bewerte_dividende(div):
    if div is None: return ""
    if div > 0.03: return "🟢"    # Gut (über 3%)
    if div > 0.015: return "🔵"   # Okay
    if div > 0: return "🟠"       # Wenig
    return "🔴"                   # Keine

def strategie_check(symbol, name):
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1y")
        if hist.empty: return None
        
        preis = round(float(hist['Close'].iloc[-1]), 2)
        
        # --- TECHNISCHE DATEN ---
        sma_50 = hist['Close'].rolling(window=50).mean().iloc[-1]
        sma_200 = hist['Close'].rolling(window=200).mean().iloc[-1]
        delta = hist['Close'].diff()
        gewinn = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        verlust = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gewinn / verlust
        rsi = 100 - (100 / (1 + rs))
        rsi_wert = round(float(rsi.iloc[-1]), 1)

        # Ampel Signal (Gesamt)
        signal = "⚪ HALTEN"
        if rsi_wert < 30: signal = "🟢 KAUFEN (Schnäppchen)"
        elif sma_50 > sma_200 and rsi_wert < 50: signal = "🟢 KAUFEN (Trend)"
        if rsi_wert > 70: signal = "🔴 VERKAUFEN (Überhitzt)"
        elif sma_50 < sma_200: signal = "🔴 VERKAUFEN (Abwärtstrend)"

        # --- FUNDAMENTALE DATEN ---
        info = ticker.info
        kgv = info.get('trailingPE')
        kbv = info.get('priceToBook')
        kuv = info.get('priceToSalesTrailing12Months')
        div_yield = info.get('dividendYield')
        peg = info.get('pegRatio')
        eps = info.get('trailingEps')

        # Formatierung
        div_text = f"{round(div_yield * 100, 2)}%" if div_yield else "0%"
        
        # Farben holen
        c_rsi = bewerte_rsi(rsi_wert)
        c_kgv = bewerte_kgv(kgv)
        c_peg = bewerte_peg(peg)
        c_div = bewerte_dividende(div_yield)
        
        # --- ZUSAMMENBAU ---
        text = f"<b>🏢 {name} ({symbol})</b>: {preis} €\n"
        text += f"Signal: {signal}\n"
        
        if symbol == "BTC-USD":
            text += f"RSI: {rsi_wert} {c_rsi}\n"
        else:
            text += f"📊 <b>Kennzahlen Check:</b>\n"
            text += f"• RSI: {rsi_wert} {c_rsi}\n"
            text += f"• KGV: {format_number(kgv)} {c_kgv} | PEG: {format_number(peg)} {c_peg}\n"
            text += f"• Div: {div_text} {c_div} | KBV: {format_number(kbv)}\n"
            text += f"• KUV: {format_number(kuv)} | EPS: {format_number(eps)} €\n"
        
        news_headline = hol_nachrichten(ticker)
        text += f"\n📰 <b>News:</b> {news_headline}\n"
        text += "------------------------------\n"
        
        return text

    except Exception as e:
        print(f"Fehler bei {name}: {e}")
        return None

if __name__ == "__main__":
    datum = datetime.now().strftime('%d.%m.%Y')
    bericht = f"📊 <b>Farb-Analyse {datum}</b> 📊\n\n"
    bericht += "Legende: 🟢=Gut 🔵=Neutral 🟠=Vorsicht 🔴=Schlecht\n\n"
    
    erfolg = False
    for symbol, name in MEINE_AKTIEN.items():
        block = strategie_check(symbol, name)
        if block:
            bericht += block
            erfolg = True
            
    if erfolg:
        telegram_senden(bericht)
