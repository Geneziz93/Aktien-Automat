import yfinance as yf
import os
import requests
from datetime import datetime

# Deine Aktienliste
MEINE_AKTIEN = ['AAPL', 'TSLA', 'MSFT', 'AMZN', 'BTC-USD', 'VOW3.DE']

def telegram_senden(nachricht):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    print("--- DIAGNOSE START ---")
    
    # Check 1: Wurden die Passwörter gefunden?
    if not token:
        print("FEHLER: Der Token fehlt! Bitte in Settings -> Secrets prüfen.")
        return
    if not chat_id:
        print("FEHLER: Die Chat ID fehlt! Bitte in Settings -> Secrets prüfen.")
        return

    # Check 2: Sieht die Chat ID gut aus?
    print(f"Token gefunden (Länge: {len(token)})")
    print(f"Sende an Chat ID: {chat_id}")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    daten = {'chat_id': chat_id, 'text': nachricht, 'parse_mode': 'Markdown'}
    
    # Check 3: Was antwortet Telegram?
    try:
        antwort = requests.post(url, data=daten)
        print(f"Telegram Status Code: {antwort.status_code}")
        print(f"Telegram Antwort Text: {antwort.text}")
        
        if antwort.status_code == 200:
            print("✅ ERFOLG: Nachricht wurde zugestellt!")
        else:
            print("❌ FEHLER: Telegram hat die Nachricht abgelehnt.")
    except Exception as e:
        print(f"Kritischer Fehler beim Senden: {e}")
    
    print("--- DIAGNOSE ENDE ---")

def strategie_check(symbol):
    try:
        df = yf.download(symbol, period="1y", interval="1d", progress=False)
        if len(df) < 200: return None

        preis = round(float(df['Close'].iloc[-1]), 2)
        # Einfache Indikatoren für den Test
        rsi_aktuell = 50 # Platzhalter, falls Berechnung fehlschlägt
        
        # Versuche echte Berechnung
        try:
            delta = df['Close'].diff()
            gewinn = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            verlust = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gewinn / verlust
            rsi = 100 - (100 / (1 + rs))
            rsi_aktuell = round(float(rsi.iloc[-1]), 2)
        except:
            pass

        return f"*{symbol}*: {preis} € (RSI: {rsi_aktuell})"
    except:
        return None

if __name__ == "__main__":
    print("Starte Aktien-Check...")
    nachricht = f"Test-Nachricht vom {datetime.now().strftime('%H:%M')}\n\n"
    
    for aktie in MEINE_AKTIEN:
        erg = strategie_check(aktie)
        if erg:
            nachricht += erg + "\n"
            print(f"Geprüft: {aktie}")
    
    telegram_senden(nachricht)
