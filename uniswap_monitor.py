import requests
import yfinance as yf
import pandas as pd
import time
from datetime import datetime
import random

# Конфиг Telegram
BOT_TOKEN = '8442392037:AAEiM_b4QfdFLqbmmc1PXNvA99yxmFVLEp8'
CHAT_ID = '350766421'

# Список мудростей дня
WISDOMS = [
    "Жадность — это чума.",
    "New Day — New Opportunity.",
    "Ты — раб. Либо своих страхов, либо своей дисциплины.",
    "Сосредоточься на том, что ты можешь изменить (мысли, действия), а не на внешнем.",
    "Принятие судьбы (Amor Fati): принимай всё, что происходит, как полезный урок.",
]

def get_daily_wisdom():
    return random.choice(WISDOMS)

def format_number(number):
    if number is None:
        return "N/A"
    try:
        return f"{number:,.0f}".replace(",", " ")
    except:
        return str(number)

def get_trading_signal(rsi, fear_greed_index):
    if rsi is None or fear_greed_index is None:
        return "N/A"
    
    try:
        rsi = float(rsi)
        fear_greed_index = float(fear_greed_index)
        
        if rsi < 30:
            rsi_cat = 'under_30'
        elif 30 <= rsi <= 45:
            rsi_cat = '30_45'
        elif 45 < rsi < 55:
            rsi_cat = '45_55'
        elif 55 <= rsi <= 70:
            rsi_cat = '55_70'
        else:
            rsi_cat = 'over_70'
        
        if fear_greed_index < 25:
            fg_cat = 'extreme_fear'
        elif 25 <= fear_greed_index <= 45:
            fg_cat = 'fear'
        elif 45 < fear_greed_index < 55:
            fg_cat = 'neutral'
        elif 55 <= fear_greed_index <= 75:
            fg_cat = 'greed'
        else:
            fg_cat = 'extreme_greed'
        
        matrix = {
            'extreme_fear': {
                'under_30': 'STRONG BUY', '30_45': 'STRONG BUY', '45_55': 'BUY', '55_70': 'NEUTRAL', 'over_70': 'NEUTRAL'
            },
            'fear': {
                'under_30': 'STRONG BUY', '30_45': 'BUY', '45_55': 'NEUTRAL', '55_70': 'NEUTRAL', 'over_70': 'SELL'
            },
            'neutral': {
                'under_30': 'BUY', '30_45': 'NEUTRAL', '45_55': 'NEUTRAL', '55_70': 'NEUTRAL', 'over_70': 'SELL'
            },
            'greed': {
                'under_30': 'NEUTRAL', '30_45': 'NEUTRAL', '45_55': 'NEUTRAL', '55_70': 'SELL', 'over_70': 'STRONG SELL'
            },
            'extreme_greed': {
                'under_30': 'NEUTRAL', '30_45': 'SELL', '45_55': 'SELL', '55_70': 'STRONG SELL', 'over_70': 'STRONG SELL'
            }
        }
        
        return matrix[fg_cat][rsi_cat]
    except Exception as e:
        print(f"Ошибка в trading signal: {e}")
        return "N/A"

def calculate_rsi(prices, period=14):
    try:
        if len(prices) < period + 1:
            return None
            
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        loss = loss.replace(0, float('nan'))
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else None
    except Exception as e:
        print(f"Ошибка расчета RSI: {e}")
        return None

def get_rsi_2h_yfinance(symbol):
    """Получение RSI 2H через yfinance"""
    try:
        ticker_map = {
            'BTC': 'BTC-USD',
            'ETH': 'ETH-USD', 
            'BNB': 'BNB-USD',
            'SOL': 'SOL-USD'
        }
        
        ticker_symbol = ticker_map.get(symbol)
        if not ticker_symbol:
            return None
            
        ticker = yf.Ticker(ticker_symbol)
        # Получаем данные за 5 дней с интервалом 1 час
        hist = ticker.history(period="5d", interval="1h")
        
        if len(hist) < 15:
            return None
        
        # Группируем по 2 часа
        hist_2h = hist.resample('2H').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()
        
        if len(hist_2h) < 15:
            return None
            
        return calculate_rsi(hist_2h['Close'], 14)
        
    except Exception as e:
        print(f"Ошибка yfinance RSI 2H для {symbol}: {e}")
        return None

def get_rsi_yfinance(symbol, days=30):
    """Альтернативный способ получения RSI через yfinance"""
    try:
        ticker_map = {
            'BTC': 'BTC-USD',
            'ETH': 'ETH-USD', 
            'BNB': 'BNB-USD',
            'SOL': 'SOL-USD'
        }
        
        ticker_symbol = ticker_map.get(symbol)
        if not ticker_symbol:
            return None
            
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period=f"{days+14}d")
        
        if len(hist) < 15:
            return None
            
        return calculate_rsi(hist['Close'], 14)
        
    except Exception as e:
        print(f"Ошибка yfinance RSI для {symbol}: {e}")
        return None

def get_top_cryptos():
    url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=10&page=1&sparkline=false&price_change_percentage=24h"
    
    try:
        print("Получение топ криптовалют...")
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            print(f"API ошибка: {response.status_code}")
            return []
            
        data = response.json()
        cryptos = []
        
        for coin in data:
            symbol_upper = coin.get('symbol', '').upper()
            if symbol_upper in ['USDT', 'XRP']:
                continue
                
            cryptos.append({
                'id': coin.get('id', ''),
                'name': coin.get('name', 'Unknown'),
                'symbol': symbol_upper,
                'price': coin.get('current_price', 0),
                'change_24h': coin.get('price_change_percentage_24h', 0)
            })
            
            if len(cryptos) == 4:
                break
        
        print(f"Найдено {len(cryptos)} криптовалют")
        
        for i, crypto in enumerate(cryptos):
            print(f"Обработка {crypto['symbol']}...")
            
            # RSI 2H
            crypto['rsi_2h'] = get_rsi_2h_yfinance(crypto['symbol'])
            time.sleep(1)
            
            # Weekly RSI
            crypto['rsi_weekly'] = get_rsi_yfinance(crypto['symbol'], 90)
            time.sleep(1)
            
            if i < len(cryptos) - 1:
                time.sleep(2)
                
        return cryptos
        
    except Exception as e:
        print(f"Ошибка получения крипто: {e}")
        return []

def get_btc_dominance():
    url = "https://api.coingecko.com/api/v3/global"
    try:
        time.sleep(2)
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return None
        data = response.json()
        if 'data' not in data:
            return None
        global_data = data['data']
        if 'market_cap_percentage' not in global_data:
            return None
        dominance = global_data['market_cap_percentage'].get('btc', None)
        return dominance
    except Exception as e:
        print(f"Ошибка получения BTC Dominance: {e}")
        return None

def get_sp500():
    """S&P 500 из yfinance с улучшенной обработкой"""
    try:
        ticker = yf.Ticker("^GSPC")
        # Получаем последние 5 дней для надежности
        hist = ticker.history(period="5d")
        
        if hist.empty or len(hist) < 1:
            print("S&P 500: нет данных в истории")
            return None, None
            
        current = hist['Close'].iloc[-1]
        
        # Пытаемся найти предыдущее значение
        if len(hist) >= 2:
            prev = hist['Close'].iloc[-2]
            change_24h = ((current - prev) / prev) * 100
        else:
            change_24h = 0
            
        return round(current, 2), round(change_24h, 2)
    except Exception as e:
        print(f"Ошибка получения S&P 500: {e}")
        return None, None

def get_usd_rub():
    """USD/RUB из yfinance с улучшенной обработкой"""
    try:
        ticker = yf.Ticker("USDRUB=X")
        # Получаем последние 5 дней
        hist = ticker.history(period="5d")
        
        if hist.empty or len(hist) < 1:
            print("USD/RUB: нет данных в истории")
            return None, None
            
        current = hist['Close'].iloc[-1]
        
        # Пытаемся найти предыдущее значение
        if len(hist) >= 2:
            prev = hist['Close'].iloc[-2]
            change_24h = ((current - prev) / prev) * 100
        else:
            change_24h = 0
            
        return round(current, 2), round(change_24h, 2)
    except Exception as e:
        print(f"Ошибка получения USD/RUB: {e}")
        return None, None

def get_fear_greed():
    url = "https://api.alternative.me/fng/?limit=0"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return None, None, None
        data = response.json()
        if 'data' not in data or not data['data']:
            return None, None, None
        latest = data['data'][0]
        value_change = latest.get('value_change_percent', 0)
        return float(latest.get('value', 0)), latest.get('value_classification', 'Unknown'), value_change
    except Exception as e:
        print(f"Ошибка получения Fear & Greed: {e}")
        return None, None, None

def format_message():
    now = datetime.now()
    
    # Форматирование даты в нужном формате
    days_ru = {
        'Monday': 'понедельник',
        'Tuesday': 'вторник',
        'Wednesday': 'среда',
        'Thursday': 'четверг',
        'Friday': 'пятница',
        'Saturday': 'суббота',
        'Sunday': 'воскресенье'
    }
    months_ru = {
        1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
        5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
        9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
    }
    
    day_name = days_ru.get(now.strftime('%A'), 'день')
    day_num = now.day
    month_name = months_ru.get(now.month, '')
    week_num = now.isocalendar()[1]
    
    # Заголовок
    header = f"#Крипта #Crypto\n{day_name.capitalize()} {day_num} {month_name}, неделя {week_num}"
    
    message = f"<b>{header}</b>\n\n"
    
    # S&P 500
    sp_price, sp_change = get_sp500()
    if sp_price:
        message += f"📊 S&P 500: {format_number(sp_price)} {sp_change:+.2f}%\n"
    else:
        message += "📊 S&P 500: Нет данных\n"

    # USD/RUB
    rub_price, rub_change = get_usd_rub()
    if rub_price:
        message += f"💵 USD/RUB: {rub_price:.2f} {rub_change:+.2f}%\n"
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

    # Топ-4 крипто + RSI
    cryptos = get_top_cryptos()
    message += "📈 Топ Крипто (USD):\n\n"
    
    if cryptos:
        max_sym_len = max(len(c['symbol']) for c in cryptos) + 1
        max_price_len = max(len(f"${format_number(c['price'])}") for c in cryptos)
        
        for crypto in cryptos:
            change_emoji = "🟢" if crypto['change_24h'] >= 0 else "🔴"
            sym_padded = f"{crypto['symbol']} ".ljust(max_sym_len)
            price_padded = f"${format_number(crypto['price'])}".ljust(max_price_len)
            change_str = f"{crypto['change_24h']:+.0f}%"
            
            rsi_2h_str = f"{crypto['rsi_2h']:.0f}" if crypto['rsi_2h'] is not None else "N/A"
            rsi_w_str = f"{crypto['rsi_weekly']:.0f}" if crypto['rsi_weekly'] is not None else "N/A"
            
            signal = get_trading_signal(crypto['rsi_2h'], fg_value) if fg_value else "N/A"
            
            message += f"{change_emoji} {sym_padded}: {price_padded} {change_str} | <code>RSI (2H/W): {rsi_2h_str}/{rsi_w_str} {signal}</code>\n"
    else:
        message += "Нет данных\n"
    
    # Мудрость дня
    message += f"\n💭 Мудрость дня:\n{get_daily_wisdom()}"

    return message

def send_telegram_message():
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
