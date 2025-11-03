import requests
import yfinance as yf
import pandas as pd
import time  # Для задержек
from datetime import datetime

# Конфиг Telegram
BOT_TOKEN = '8442392037:AAEiM_b4QfdFLqbmmc1PXNvA99yxmFVLEp8'  # Твой токен
CHAT_ID = '350766421'      # Твой chat_id

def format_number(number):
    """Форматирует число с пробелами между тысячами"""
    if number is None:
        return "N/A"
    try:
        return f"{number:,.0f}".replace(",", " ")
    except:
        return str(number)

def get_trading_signal(rsi, fear_greed_index):
    """
    Генерирует торговый сигнал на основе RSI (1D) и Crypto Fear & Greed Index.
    
    Args:
        rsi (float): Значение RSI (0-100).
        fear_greed_index (float): Значение Fear & Greed Index (0-100).
    
    Returns:
        str: Один из сигналов: 'STRONG BUY', 'BUY', 'NEUTRAL', 'SELL', 'STRONG SELL'.
    """
    if rsi is None or fear_greed_index is None:
        return "N/A"
    
    rsi = float(rsi)
    fear_greed_index = float(fear_greed_index)
    
    # Определяем категории RSI
    if rsi < 30:
        rsi_cat = 'under_30'
    elif 30 <= rsi <= 45:
        rsi_cat = '30_45'
    elif 45 < rsi < 55:
        rsi_cat = '45_55'
    elif 55 <= rsi <= 70:
        rsi_cat = '55_70'
    else:  # > 70
        rsi_cat = 'over_70'
    
    # Определяем категории Fear & Greed
    if fear_greed_index < 25:
        fg_cat = 'extreme_fear'
    elif 25 <= fear_greed_index <= 45:
        fg_cat = 'fear'
    elif 45 < fear_greed_index < 55:
        fg_cat = 'neutral'
    elif 55 <= fear_greed_index <= 75:
        fg_cat = 'greed'
    else:  # > 75
        fg_cat = 'extreme_greed'
    
    # Матрица решений (как в таблице)
    matrix = {
        'extreme_fear': {
            'under_30': 'STRONG BUY',
            '30_45': 'STRONG BUY',
            '45_55': 'BUY',
            '55_70': 'NEUTRAL',
            'over_70': 'NEUTRAL'
        },
        'fear': {
            'under_30': 'STRONG BUY',
            '30_45': 'BUY',
            '45_55': 'NEUTRAL',
            '55_70': 'NEUTRAL',
            'over_70': 'SELL'
        },
        'neutral': {
            'under_30': 'BUY',
            '30_45': 'NEUTRAL',
            '45_55': 'NEUTRAL',
            '55_70': 'NEUTRAL',
            'over_70': 'SELL'
        },
        'greed': {
            'under_30': 'NEUTRAL',
            '30_45': 'NEUTRAL',
            '45_55': 'NEUTRAL',
            '55_70': 'SELL',
            'over_70': 'STRONG SELL'
        },
        'extreme_greed': {
            'under_30': 'NEUTRAL',
            '30_45': 'SELL',
            '45_55': 'SELL',
            '55_70': 'STRONG SELL',
            'over_70': 'STRONG SELL'
        }
    }
    
    return matrix[fg_cat][rsi_cat]

def calculate_rsi(prices, period=14):
    """Расчёт RSI на основе pandas"""
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

def get_rsi(coin_id, days=30):
    """RSI для монеты из CoinGecko (days=30 для дневного, 365 для недельного — больше данных)"""
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days={days}&interval=daily"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'prices' in data and len(data['prices']) >= 14:
                prices = pd.DataFrame(data['prices'], columns=['timestamp', 'price'])
                return calculate_rsi(prices['price'], 14)
            else:
                print(f"Недостаточно данных для {coin_id} (days={days}): {len(data.get('prices', []))}")
                return None
        else:
            print(f"API RSI error для {coin_id}: status {response.status_code}, text: {response.text[:100]}")
            return None
    except Exception as e:
        print(f"Ошибка RSI для {coin_id}: {e}")
        return None

def get_top_cryptos():
    """Топ-4 крипто из CoinGecko (исключая USDT и XRP) + RSI"""
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
            symbol_upper = coin.get('symbol', '').upper()
            if symbol_upper in ['USDT', 'XRP']:  # Пропускаем USDT и XRP
                continue
            cryptos.append({
                'id': coin.get('id', ''),
                'name': coin.get('name', 'Unknown'),
                'symbol': symbol_upper,
                'price': coin.get('current_price', 0),
                'change_24h': coin.get('price_change_percentage_24h', 0)
            })
            if len(cryptos) == 4:  # Берем ровно 4
                break
        
        # Добавляем RSI для каждой с большей задержкой (rate limit fix)
        for i, crypto in enumerate(cryptos):
            print(f"Получаем RSI для {crypto['id']}...")
            crypto['rsi_daily'] = get_rsi(crypto['id'], 30)
            time.sleep(3)  # Увеличенная задержка 3 сек
            crypto['rsi_weekly'] = get_rsi(crypto['id'], 365)  # Больше дней для weekly
            time.sleep(3)
            if i < len(cryptos) - 1:
                time.sleep(2)  # Пауза между монетами
        
        return cryptos
    except Exception as e:
        print(f"Ошибка получения крипто: {e}")
        return []

def get_btc_dominance():
    """Bitcoin Dominance из CoinGecko Global"""
    url = "https://api.coingecko.com/api/v3/global"
    try:
        time.sleep(2)  # Задержка перед вызовом
        response = requests.get(url, timeout=10)
        print(f"Dominance response status: {response.status_code}")  # Debug
        if response.status_code != 200:
            print(f"API Global error status: {response.status_code}, text: {response.text}")
            return None
        data = response.json()
        print(f"Dominance data keys: {list(data.keys())}")  # Debug
        if 'data' not in data:
            print(f"API Global missing 'data' key, full response: {data}")
            return None
        global_data = data['data']
        print(f"Global data keys: {list(global_data.keys())}")  # Debug
        if 'market_cap_percentage' not in global_data:
            print(f"API Global missing 'market_cap_percentage', full global_data keys: {list(global_data.keys())}")
            return None
        dominance = global_data['market_cap_percentage'].get('btc', None)
        print(f"BTC Dominance raw: {dominance}")  # Debug
        return dominance
    except Exception as e:
        print(f"Ошибка получения BTC Dominance: {e}")
        return None

def get_sp500():
    """S&P 500 из yfinance"""
    try:
        ticker = yf.Ticker("^GSPC")
        hist = ticker.history(period="5d")  # Увеличили период для большего количества данных
        if len(hist) < 2:
            current = hist['Close'].iloc[-1] if len(hist) > 0 else None
            return current, 0.0 if current else None
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
        ticker = yf.Ticker("USDRUB=X")
        hist = ticker.history(period="5d")  # Увеличили период для большего количества данных
        if len(hist) < 2:
            current = hist['Close'].iloc[-1] if len(hist) > 0 else None
            return current, 0.0 if current else None
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
        value_change = latest.get('value_change_percent', 0)
        return float(latest.get('value', 0)), latest.get('value_classification', 'Unknown'), value_change
    except Exception as e:
        print(f"Ошибка получения Fear & Greed: {e}")
        return None, None, None

def format_message():
    """Формирует сообщение"""
    now = datetime.now()
    weekday_num = now.weekday()
    days_ru = {0: 'понедельник', 1: 'вторник', 2: 'среда', 3: 'четверг', 4: 'пятница', 5: 'суббота', 6: 'воскресенье'}
    day_name = days_ru[weekday_num]
    timestamp = now.strftime('%d.%m.%Y %H:%M')
    full_date = f"{day_name}, {timestamp}"
    hour = now.hour
    
    # Определяем приветствие по времени
    if hour < 12:
        greeting = "🌅 Доброе утро!"
    elif hour < 18:
        greeting = "☀️ Добрый день!"
    else:
        greeting = "🌆 Добрый вечер!"
    
    message = f"{greeting} Рынки на {full_date}\n\n"
    
    # S&P 500
    sp_price, sp_change = get_sp500()
    if sp_price:
        message += f"📊 S&P 500: {format_number(sp_price)} {sp_change:+.0f}%\n"
    else:
        message += "📊 S&P 500: Нет данных\n"

    # USD/RUB
    rub_price, rub_change = get_usd_rub()
    if rub_price:
        message += f"💵 USD/RUB: {format_number(rub_price)} {rub_change:+.0f}%\n"
    else:
        message += "💵 USD/RUB: Нет данных\n"

    # Fear & Greed
    fg_value, fg_class, fg_change = get_fear_greed()
    if fg_value:
        message += f"😱 Crypto Fear & Greed: {fg_value:.0f} ({fg_class})\n"
    else:
        message += "😱 Crypto Fear & Greed: Нет данных\n"

    # BTC Dominance
    btc_dom = get_btc_dominance()
    if btc_dom:
        message += f"₿ BTC Dominance: {btc_dom:.0f}%\n\n"
    else:
        message += "₿ BTC Dominance: Нет данных\n\n"

    # Топ-4 крипто + RSI (без XRP)
    cryptos = get_top_cryptos()
    message += "📈 Топ Крипто (USD):\n\n"
    if cryptos and fg_value is not None:
        max_sym_len = max(len(c['symbol']) for c in cryptos) + 1  # +1 для пробела
        max_price_len = max(len(f"${format_number(c['price'])}") for c in cryptos)
        for crypto in cryptos:
            change_emoji = "🟢" if crypto['change_24h'] >= 0 else "🔴"
            sym_padded = f"{crypto['symbol']} ".ljust(max_sym_len)
            price_padded = f"${format_number(crypto['price'])}".ljust(max_price_len)
            change_str = f"{crypto['change_24h']:+.0f}%"
            rsi_d_str = f"{crypto['rsi_daily']:.0f}" if crypto['rsi_daily'] is not None else "N/A"
            rsi_w_str = f"{crypto['rsi_weekly']:.0f}" if crypto['rsi_weekly'] is not None else "N/A"
            signal = get_trading_signal(crypto['rsi_daily'], fg_value)
            # RSI меньшим шрифтом с использованием HTML тегов
            message += f"{change_emoji} {sym_padded}: {price_padded} {change_str} | <code>RSI (1D/W): {rsi_d_str}/{rsi_w_str} {signal}</code>\n"
    else:
        message += "Нет данных\n"

    return message

def send_telegram_message():
    """Отправляет сообщение в Telegram"""
    message = format_message()
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'HTML'
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
