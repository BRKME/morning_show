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
    # ... остальные цитаты без изменений
]

def get_daily_wisdom():
    """Возвращает случайную мудрость дня"""
    return random.choice(WISDOMS)

def get_coin_id(symbol):
    """Получает правильный coin_id для CoinGecko API"""
    coin_mapping = {
        'BTC': 'bitcoin',
        'ETH': 'ethereum', 
        'BNB': 'binancecoin',
        'SOL': 'solana',
        'USDT': 'tether',
        'XRP': 'ripple'
    }
    return coin_mapping.get(symbol, symbol.lower())

def format_number(number):
    """Форматирует число с пробелами между тысячами"""
    if number is None:
        return "N/A"
    try:
        return f"{number:,.0f}".replace(",", " ")
    except:
        return str(number)

def get_trading_signal(rsi, fear_greed_index):
    """Генерирует торговый сигнал на основе RSI и Fear & Greed Index"""
    if rsi is None or fear_greed_index is None:
        return "N/A"
    
    try:
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
        
        # Матрица решений
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
    except Exception as e:
        print(f"Ошибка в trading signal: {e}")
        return "N/A"

def calculate_rsi(prices, period=14):
    """Расчёт RSI на основе pandas"""
    try:
        if len(prices) < period + 1:
            return None
            
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        # Избегаем деления на ноль
        loss = loss.replace(0, float('nan'))
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else None
    except Exception as e:
        print(f"Ошибка расчета RSI: {e}")
        return None

def get_rsi(coin_id, days=30):
    """RSI для монеты из CoinGecko с улучшенной обработкой ошибок"""
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days={days}&interval=daily"
    
    try:
        print(f"Запрос RSI для {coin_id} (days={days})...")
        response = requests.get(url, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            if 'prices' in data and len(data['prices']) >= 15:  # Минимум 15 точек
                prices_df = pd.DataFrame(data['prices'], columns=['timestamp', 'price'])
                rsi_value = calculate_rsi(prices_df['price'], 14)
                print(f"RSI для {coin_id}: {rsi_value}")
                return rsi_value
            else:
                print(f"Недостаточно данных для {coin_id}: {len(data.get('prices', []))} точек")
                return None
        elif response.status_code == 429:
            print(f"Rate limit для {coin_id}, ждем...")
            time.sleep(10)
            return None
        else:
            print(f"API ошибка для {coin_id}: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Ошибка получения RSI для {coin_id}: {e}")
        return None

def get_top_cryptos():
    """Топ-4 крипто из CoinGecko (исключая USDT и XRP) + RSI с улучшенной логикой"""
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
        
        # Добавляем RSI для каждой монеты с улучшенной обработкой
        for i, crypto in enumerate(cryptos):
            print(f"Обработка {crypto['symbol']} ({crypto['id']})...")
            
            # Daily RSI
            crypto['rsi_daily'] = get_rsi(crypto['id'], 30)
            time.sleep(2)  # Увеличиваем задержку
            
            # Weekly RSI - используем больше дней для надежности
            crypto['rsi_weekly'] = get_rsi(crypto['id'], 90)  # 90 дней для weekly
            time.sleep(2)
            
            # Дополнительная пауза между монетами
            if i < len(cryptos) - 1:
                time.sleep(3)
                
        return cryptos
        
    except Exception as e:
        print(f"Ошибка получения крипто: {e}")
        return []

# Остальные функции (get_btc_dominance, get_sp500, get_usd_rub, get_fear_greed) остаются без изменений

def format_message():
    """Формирует сообщение с улучшенным форматированием"""
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
            
            # Безопасное форматирование RSI
            rsi_d_str = f"{crypto['rsi_daily']:.0f}" if crypto['rsi_daily'] is not None else "N/A"
            rsi_w_str = f"{crypto['rsi_weekly']:.0f}" if crypto['rsi_weekly'] is not None else "N/A"
            
            signal = get_trading_signal(crypto['rsi_daily'], fg_value) if fg_value else "N/A"
            
            message += f"{change_emoji} {sym_padded}: {price_padded} {change_str} | <code>RSI (1D/W): {rsi_d_str}/{rsi_w_str} {signal}</code>\n"
    else:
        message += "Нет данных\n"
    
    # Добавляем мудрость дня
    message += f"\n💭 Мудрость дня:\n{get_daily_wisdom()}"

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
