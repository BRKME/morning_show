import requests
import yfinance as yf
from datetime import datetime

# Конфиг Telegram
BOT_TOKEN = '8442392037:AAEiM_b4QfdFLqbmmc1PXNvA99yxmFVLEp8'  # Твой токен
CHAT_ID = '350766421'      # Твой chat_id

def get_weather_spb():
    """Погода в Санкт-Петербурге (Россия) из wttr.in (в Цельсиях, с инфо о дожде)"""
    try:
        # Уточняем локацию для России: Saint_Petersburg_RU
        response = requests.get('http://wttr.in/Saint_Petersburg_RU?format=%C+%t+%p&M', timeout=10)
        if response.status_code == 200:
            weather_str = response.text.strip()
            parts = weather_str.split('+')
            if len(parts) >= 2:
                condition = parts[0].strip()
                temp = parts[1].strip()  # Уже в °C благодаря &M
                precip = parts[2].strip() if len(parts) > 2 else "0 mm"
                
                # Проверка на дождь
                rain_keywords = ['rain', 'shower', 'drizzle', 'дождь']
                has_rain = any(keyword in condition.lower() for keyword in rain_keywords)
                rain_info = "с дождём" if has_rain else "без дождя"
                
                return f"{condition} {temp}, {rain_info}"
            return weather_str
        else:
            return "Нет данных"
    except Exception as e:
        print(f"Ошибка получения погоды: {e}")
        return "Нет данных"

def get_top_cryptos():
    """Топ-5 крипто из CoinGecko (исключая USDT)"""
    url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=6&page=1&sparkline=false&price_change_percentage=24h"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            print(f"API Crypto error status: {response.status_code}, text: {response.text}")
            return []
        data = response.json()
        if not isinstance(data, list):
            print(f"API Crypto unexpected data type: {type(data)}, content: {data}")
            return []
        cryptos = []
        for coin in data:
            if not isinstance(coin, dict):
                print(f"Unexpected coin format: {coin}")
                continue
            if coin.get('symbol', '').upper() == 'USDT':  # Пропускаем USDT
                continue
            cryptos.append({
                'name': coin.get('name', 'Unknown'),
                'symbol': coin.get('symbol', 'UNK').upper(),
                'price': coin.get('current_price', 0),
                'change_24h': coin.get('price_change_percentage_24h', 0)
            })
            if len(cryptos) == 5:  # Берем ровно 5
                break
        return cryptos
    except Exception as e:
        print(f"Ошибка получения крипто: {e}")
        return []

def get_btc_dominance():
    """Bitcoin Dominance из CoinGecko Global"""
    url = "https://api.coingecko.com/api/v3/global"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            print(f"API Global error status: {response.status_code}, text: {response.text}")
            return None
        data = response.json()
        if 'data' not in data:
            print(f"API Global missing 'data' key, full response: {data}")
            return None
        global_data = data['data']
        if 'market_cap_percentage' not in global_data:
            print(f"API Global missing 'market_cap_percentage', full global_data: {global_data}")
            return None
        dominance = global_data['market_cap_percentage'].get('btc', None)
        return dominance
    except Exception as e:
        print(f"Ошибка получения BTC Dominance: {e}")
        return None

def get_sp500():
    """S&P 500 из yfinance"""
    try:
        ticker = yf.Ticker("^GSPC")
        hist = ticker.history(period="2d")
        current = hist['Close'].iloc[-1]
        prev = hist['Close'].iloc[-2]
        change_24h = ((current - prev) / prev) * 100
        return current, change_24h
    except Exception as e:
        print(f"Ошибка получения S&P 500: {e}")
        return None, None

def get_usd_rub():
    """USD/RUB из yfinance"""
    try:
        ticker = yf.Ticker("RUB=X")  # USD/RUB
        hist = ticker.history(period="
