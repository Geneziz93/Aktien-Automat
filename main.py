import yfinance as yf
import os
import requests
import pandas as pd
from datetime import datetime

# --- DEIN NEUES HIGH-GROWTH PORTFOLIO ---
MEINE_AKTIEN = [
    # 🚀 High Growth (KI & Tech)
    {"symbol": "NVDA",    "name": "Nvidia",             "sector": "🚀 High Growth (KI & Tech)"},
    {"symbol": "MSFT",    "name": "Microsoft",          "sector": "🚀 High Growth (KI & Tech)"},
    {"symbol": "PLTR",    "name": "Palantir",           "sector": "🚀 High Growth (KI & Tech)"},
    {"symbol": "ASML",    "name": "ASML",               "sector": "🚀 High Growth (KI & Tech)"},
    {"symbol": "PANW",    "name": "Palo Alto Networks", "sector": "🚀 High Growth (KI & Tech)"},
    {"symbol": "TSM",     "name": "TSMC",               "sector": "🚀 High Growth (KI & Tech)"},

    # 🌌 Space Economy
    {"symbol": "RKLB",    "name": "Rocket Lab USA",     "sector": "🌌 Space Economy"},
    {"symbol": "NOC",     "name": "Northrop Grumman",   "sector": "🌌 Space Economy"},

    # 💊 Gesundheit & Demografie
    {"symbol": "NVO",     "name": "Novo Nordisk",       "sector": "💊 Gesundheit & Demografie"},
    {"symbol": "ISRG",    "name": "Intuitive Surgical", "sector": "💊 Gesundheit & Demografie"},
    {"symbol": "UNH",     "name": "UnitedHealth Grp",   "sector": "💊 Gesundheit & Demografie"},

    # 🛍️ Konsum & Dienstleistungen
    {"symbol": "AMZN",    "name": "Amazon",             "sector": "🛍️ Konsum & Services"},
    {"symbol": "RACE",    "name": "Ferrari",            "sector": "🛍️ Konsum & Services"},
    {"symbol": "COST",    "name": "Costco Wholesale",   "sector": "🛍️ Konsum & Services"},
    {"symbol": "GOOGL",   "name": "Alphabet (Google)",  "sector": "🛍️ Konsum & Services"},
    {"symbol": "V",       "name": "Visa",               "sector": "🛍️ Konsum & Services"},

    # 🏭 Industrie & Infrastruktur
    {"symbol": "RHM.DE",  "name": "Rheinmetall",        "sector": "🏭 Industrie & Infra"},
    {"symbol": "SU.PA",   "name": "Schneider Electric", "sector": "🏭 Industrie & Infra"},
    {"symbol": "LIN",     "name": "Linde",              "sector": "🏭 Industrie & Infra"},
    {"symbol": "FCX",     "name": "Freeport-McMoRan",   "sector": "🏭 Industrie & Infra"},

    # ⚡ Versorger & Substanz
    {"symbol": "NEE",     "name": "NextEra Energy",     "sector": "⚡ Versorger & Substanz"},
    {"symbol": "EQIX",    "name": "Equinix (REIT)",     "sector": "⚡ Versorger & Substanz"},
    {"symbol": "BLK",     "name": "BlackRock",          "sector": "⚡ Versorger & Substanz"},

    # 🪙 Krypto
    {"symbol": "BTC-USD", "name": "Bitcoin",            "sector": "🪙 Krypto"},
    {"symbol": "SOL-USD", "name": "Solana",             "sector": "🪙 Krypto"}
]

def get_usd_to_eur_rate():
    """Holt den aktuellen Umrechnungskurs von Dollar zu Euro"""
    try:
        # Wir holen uns das Paar EURUSD=X (1 Euro = x Dollar)
        ticker = yf.Ticker("EURUSD=X")
        hist = ticker.history(period="1d")
        if not hist.empty:
            rate = float(hist['Close'].iloc[-1])
            return 1 / rate # Umkehrung: 1 Dollar = x Euro
    except:
        pass
    return 0.95 # Fallback

# Den Kurs holen wir nur 1x am Anfang
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
        
        # Währung prüfen
        try:
            currency = ticker.fast_info['currency']
        except:
            currency = "USD" # Annahme bei Fehler

        hist = ticker.history(period="1y")
        if hist.empty: return None
        
        raw_price = float(hist['Close'].iloc[-1])
        
        # --- WÄHRUNGSUMRECHNUNG ---
        if currency == "USD":
            preis_in_euro = raw_price * AKTUELLER_USD_EUR_KURS
        else:
            # Falls Aktie schon in EUR (z.B. Rheinmetall)
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
        
        # Kaufen
        if rsi_wert < 30: 
            signal = "🟢 <b>KAUFEN</b> (Billig)"
        elif sma_50 > sma_200 and rsi_wert < 50: 
            signal = "🟢 <b>KAUFEN</b> (Trend)"
            
        # Verkaufen
        if rsi_wert > 70: 
            signal = "🔴 <b>VERKAUFEN</b> (Teuer)"
        elif sma_50 < sma_200: 
            signal = "🔴 <b>VERKAUFEN</b> (Abwärtstrend)"

        # --- KOMPAKTE AUSGABE ---
        text = f"<b>{name}</b>: {preis_anzeige} €\n"
        text += f"{signal}\n\n" 
        
        return text

    except Exception as e:
        print(f"Fehler bei {name}: {e}")
        return None

if __name__ == "__main__":
    datum = datetime.now().strftime('%d.%m')
    bericht = f"📊 <b>Future Depot {datum}</b>\n\n"
    
    sektor_ergebnisse = {}
    
    print(f"Starte Analyse (Wechselkurs: {round(AKTUELLER_USD_EUR_KURS, 2)})...")
    
    for aktie in MEINE_AKTIEN:
        ergebnis = strategie_check(aktie)
        if ergebnis:
            sektor = aktie["sector"]
            if sektor not in sektor_ergebnisse:
                sektor_ergebnisse[sektor] = ""
            sektor_ergebnisse[sektor] += ergebnis
            print(f"✅ {aktie['name']} fertig.")

    # Bericht sortiert zusammenbauen
    # Damit die Reihenfolge genau wie in deiner Liste ist, nutzen wir die Liste zum Sortieren der Keys
    reihenfolge = []
    for a in MEINE_AKTIEN:
        if a["sector"] not in reihenfolge:
            reihenfolge.append(a["sector"])

    has_content = False
    for sektor in reihenfolge:
        if sektor in sektor_ergebnisse:
            bericht += f"<b>--- {sektor} ---</b>\n"
            bericht += sektor_ergebnisse[sektor]
            has_content = True

    if has_content:
        telegram_senden(bericht)
        print("Nachricht gesendet.")
    else:
        print("Keine Daten verfügbar.")
