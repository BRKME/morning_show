import requests
import pandas as pd
import time
from datetime import datetime
import random

# Конфиг Telegram
BOT_TOKEN = '8442392037:AAEiM_b4QfdFLqbmmc1PXNvA99yxmFVLEp8'
CHAT_ID = '350766421'

# Список мудростей дня
WISDOMS = [
"Единственный приоритет - защита капитала, только потом умножение. ( Без фундамента небоскрёб рухнет.)",
"Не будь дураком ( Проверь: нет ли здесь «быстрой наживы» или сомнительных обещаний )",
"Играй в долгую  (Мои инвестиции соответствует моему плану на годы, а не на день.)",
"Дисциплина > эмоции ( Решение всегда основано на стратегии, а не на страхе или жадности.)",
"Риски под контролем» ( Я понимаю, что могу потерять, и готов к этому." 
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
    """Расчет RSI из списка цен"""
    try:
        if len(prices) < period + 1:
            print(f"Недостаточно данных для RSI: {len(prices)} < {period + 1}")
            return None
        
        # Преобразуем в pandas Series если это список
        if isinstance(prices, list):
            prices = pd.Series(prices)
            
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        # Защита от деления на ноль
        rs = gain / loss.replace(0, 0.0001)
        rsi = 100 - (100 / (1 + rs))
        
        result = rsi.iloc[-1]
        if pd.isna(result):
            return None
        return result
    except Exception as e:
        print(f"Ошибка расчета RSI: {e}")
        return None

def get_binance_klines(symbol, interval='1h', limit=100):
    """Получение свечей с Binance - возвращает список цен закрытия"""
    try:
        url = "https://api.binance.com/api/v3/klines"
        params = {
            'symbol': f"{symbol}USDT",
            'interval': interval,
            'limit': limit
        }
        
        print(f"Запрос Binance: {symbol}USDT, interval={interval}, limit={limit}")
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            # Извлекаем цены закрытия (индекс 4 в каждой свече)
            prices = [float(candle[4]) for candle in data]
            print(f"Получено {len(prices)} свечей для {symbol}")
            return prices
        else:
            print(f"Ошибка Binance API: {response.status_code}")
            return None
    except Exception as e:
        print(f"Ошибка Binance для {symbol}: {e}")
        return None

def get_rsi_2h_binance(symbol):
    """RSI 2H - берем 2-часовые свечи напрямую"""
    try:
        # Берем 2h свечи напрямую (Binance поддерживает этот интервал)
        prices = get_binance_klines(symbol, '2h', 50)
        if prices and len(prices) >= 15:
            rsi = calculate_rsi(prices, 14)
            print(f"RSI 2H для {symbol}: {rsi}")
            return rsi
        return None
    except Exception as e:
        print(f"Ошибка RSI 2H для {symbol}: {e}")
        return None

def get_rsi_daily_binance(symbol):
    """RSI Daily - дневные свечи"""
    try:
        prices = get_binance_klines(symbol, '1d', 50)
        if prices and len(prices) >= 15:
            rsi = calculate_rsi(prices, 14)
            print(f"RSI Daily для {symbol}: {rsi}")
            return rsi
        return None
    except Exception as e:
        print(f"Ошибка RSI Daily для {symbol}: {e}")
        return None

def get_sp500_investing():
    """S&P 500 через Investing.com API (неофициальный но работает)"""
    try:
        # Используем публичный API который парсит Investing.com
        url = "https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC"
        params = {
            'interval': '1d',
            'range': '2d'
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'chart' in data and 'result' in data['chart']:
                result = data['chart']['result'][0]
                if 'meta' in result and 'indicators' in result:
                    meta = result['meta']
                    current = meta.get('regularMarketPrice')
                    prev_close = meta.get('chartPreviousClose')
                    
                    if current and prev_close:
                        change = ((current - prev_close) / prev_close) * 100
                        return round(current, 2), round(change, 2)
        return None, None
    except Exception as e:
        print(f"Ошибка S&P 500: {e}")
        return None, None

def get_usd_rub_cbr():
    """USD/RUB через ЦБ РФ"""
    try:
        url = "https://www.cbr-xml-daily.ru/daily_json.js"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'Valute' in data and 'USD' in data['Valute']:
                usd_data = data['Valute']['USD']
                current = usd_data['Value']
                prev = usd_data['Previous']
                change = ((current - prev) / prev) * 100
                return round(current, 2), round(change, 2)
        return None, None
    except Exception as e:
        print(f"Ошибка USD/RUB (ЦБ): {e}")
        return None, None

def get_usd_rub_coingecko():
    """USD/RUB через CoinGecko (через стейблкоины)"""
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            'ids': 'tether',
            'vs_currencies': 'rub',
            'include_24hr_change': 'true'
        }
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'tether' in data and 'rub' in data['tether']:
                price = data['tether']['rub']
                change = data['tether'].get('rub_24h_change', 0)
                return round(price, 2), round(change, 2)
        return None, None
    except Exception as e:
        print(f"Ошибка USD/RUB (CoinGecko): {e}")
        return None, None

def get_top_cryptos():
    """Топ-4 крипты с CoinGecko + RSI с Binance"""
    url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=10&page=1&sparkline=false&price_change_percentage=24h"
    
    try:
        print("Получение топ криптовалют...")
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            print(f"API ошибка: {response.status_code}")
            return []
            
        data = response.json()
        cryptos = []
        
        # Маппинг для Binance символов
        binance_map = {
            'BTC': 'BTC',
            'ETH': 'ETH',
            'BNB': 'BNB',
            'SOL': 'SOL'
        }
        
        for coin in data:
            symbol_upper = coin.get('symbol', '').upper()
            if symbol_upper in ['USDT', 'XRP']:
                continue
            
            if symbol_upper not in binance_map:
                continue
                
            cryptos.append({
                'id': coin.get('id', ''),
                'name': coin.get('name', 'Unknown'),
                'symbol': symbol_upper,
                'binance_symbol': binance_map[symbol_upper],
                'price': coin.get('current_price', 0),
                'change_24h': coin.get('price_change_percentage_24h', 0)
            })
            
            if len(cryptos) == 4:
                break
        
        print(f"Найдено {len(cryptos)} криптовалют")
        
        # Получаем RSI с Binance
        for crypto in cryptos:
            print(f"\n--- Обработка {crypto['symbol']} ---")
            
            # RSI 2H
            crypto['rsi_2h'] = get_rsi_2h_binance(crypto['binance_symbol'])
            time.sleep(0.3)
            
            # RSI Daily
            crypto['rsi_daily'] = get_rsi_daily_binance(crypto['binance_symbol'])
            time.sleep(0.3)
                
        return cryptos
        
    except Exception as e:
        print(f"Ошибка получения крипто: {e}")
        return []

def get_btc_dominance():
    """BTC Dominance"""
    url = "https://api.coingecko.com/api/v3/global"
    try:
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

def get_fear_greed():
    """Fear & Greed Index"""
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
    
    # Форматирование даты
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
    sp_price, sp_change = get_sp500_investing()
    
    if sp_price:
        message += f"📊 S&P 500: {format_number(sp_price)} {sp_change:+.2f}%\n"
    else:
        message += "📊 S&P 500: Нет данных\n"

    # USD/RUB
    rub_price, rub_change = get_usd_rub_cbr()
    if not rub_price:
        rub_price, rub_change = get_usd_rub_coingecko()
    
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
            rsi_d_str = f"{crypto['rsi_daily']:.0f}" if crypto['rsi_daily'] is not None else "N/A"
            
            signal = get_trading_signal(crypto['rsi_2h'], fg_value) if fg_value else "N/A"
            
            message += f"{change_emoji} {sym_padded}: {price_padded} {change_str} | <code>RSI (2H/D): {rsi_2h_str}/{rsi_d_str} {signal}</code>\n"
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
