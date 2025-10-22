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
        hist = ticker.history(period="2d")
        current = hist['Close'].iloc[-1]
        prev = hist['Close'].iloc[-2]
        change_24h = ((current - prev) / prev) * 100
        return current, change_24h
    except Exception as e:
        print(f"Ошибка получения USD/RUB: {e}")
        return None, None

def get_fear_greed():
    """Crypto Fear & Greed Index"""
    url = "https://api.alternative.me/fng/?limit=0"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            print(f"API Fear&Greed error status: {response.status_code}, text: {response.text}")
            return None, None, None
        data = response.json()
        if 'data' not in data or not data['data']:
            print(f"API Fear&Greed missing 'data', full response: {data}")
            return None, None, None
        latest = data['data'][0]
        value_change = latest.get('value_change_percent', 0)  # Безопасный доступ, дефолт 0 если нет
        return latest.get('value'), latest.get('value_classification', 'Unknown'), value_change
    except Exception as e:
        print(f"Ошибка получения Fear & Greed: {e}")
        return None, None, None

def format_message():
    """Формирует сообщение"""
    message = f"🌅 Доброе утро! Ничего не бойся и не сдавайся! Отчет на {datetime.now().strftime('%d.%m.%Y %H:%M')} 🌅\n\n"

    # Погода в СПб (Россия)
    weather_spb = get_weather_spb()
    message += f"🌤️ Погода в СПб: {weather_spb}\n\n"

    # Топ-5 крипто (без USDT), выровненные с эмодзи перед тикером
    cryptos = get_top_cryptos()
    message += "📈 Топ-5 Крипто (USD):\n"
    if cryptos:
        max_sym_len = max(len(c['symbol']) for c in cryptos)
        max_price_len = max(len(f"${c['price']:,.2f}") for c in cryptos)
        for crypto in cryptos:
            change_emoji = "🟢" if crypto['change_24h'] >= 0 else "🔴"
            sym_padded = crypto['symbol'].ljust(max_sym_len)
            price_padded = f"${crypto['price']:,.2f}".ljust(max_price_len)
            change_str = f"{crypto['change_24h']:+.2f}%"
            message += f"{change_emoji} {sym_padded}: {price_padded} {change_str}\n"
    else:
        message += "Нет данных\n"

    # BTC Dominance
    btc_dom = get_btc_dominance()
    if btc_dom:
        message += f"\n₿ BTC Dominance: {btc_dom:.2f}%\n"
    else:
        message += "\n₿ BTC Dominance: Нет данных\n"

    # S&P 500 без эмодзи перед
    sp_price, sp_change = get_sp500()
    if sp_price:
        message += f"\n📊 S&P 500: {sp_price:,.2f} {sp_change:+.2f}%\n"
    else:
        message += "\n📊 S&P 500: Нет данных\n"

    # USD/RUB без эмодзи перед
    rub_price, rub_change = get_usd_rub()
    if rub_price:
        message += f"\n💵 USD/RUB: {rub_price:.4f} {rub_change:+.2f}%\n"
    else:
        message += "\n💵 USD/RUB: Нет данных\n"

    # Fear & Greed без эмодзи перед
    fg_value, fg_class, fg_change = get_fear_greed()
    if fg_value:
        message += f"\n😱 Crypto Fear & Greed: {fg_value} ({fg_class}) {fg_change:+.1f}%"
    else:
        message += "\n😱 Crypto Fear & Greed: Нет данных"

    return message

def send_telegram_message():
    """Отправляет сообщение в Telegram"""
    message = format_message()
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'HTML'  # Для эмодзи и форматирования
    }
    try:
        response = requests.post(url, data=payload, timeout=10)
        if response.status_code == 200:
            print("Сообщение отправлено успешно!")
        else:
            print(f"Ошибка отправки: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Исключение при отправке: {e}")

if __name__ == "__main__":
    send_telegram_message()
