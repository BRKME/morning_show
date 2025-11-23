import requests
import pandas as pd
import time
from datetime import datetime
import random
import yfinance as yf  # pip install yfinance
from bs4 import BeautifulSoup  # pip install beautifulsoup4

# Конфиг Telegram
BOT_TOKEN = '8442392037:AAEiM_b4QfdFLqbmmc1PXNvA99yxmFVLEp8'
CHAT_ID = '350766421'

# Список мудростей дня
WISDOMS = [
  """Когда цена растет, ты жалеешь, что не купил больше.
     Когда цена падает, ты ненавидишь быть в минусе.
     Когда цена идет вбок, тебе безумно скучно. Прими эту боль. Крипта SCAM""",
     
  """We have a 2030 BTC target; 
     in our base case, it's around $650,000, 
     and in our bull case, it's between $1 million and $1.5 million"""
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

def get_cryptocompare_historical(symbol, timeframe='hour', limit=100):
    """Получение исторических цен с CryptoCompare"""
    try:
        url = f"https://min-api.cryptocompare.com/data/v2/histo{timeframe}"
        params = {
            'fsym': symbol,
            'tsym': 'USD',
            'limit': limit
        }
        
        print(f"Запрос CryptoCompare: {symbol}, timeframe={timeframe}")
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if (data['Response'] == 'Success' and
                    'Data' in data and 'Data' in data['Data']):
                historical = data['Data']['Data']
                prices = [candle['close'] for candle in historical
                          if candle['close'] > 0]
                print(f"Получено {len(prices)} цен для {symbol}")
                return prices
            else:
                print(f"Ошибка данных CryptoCompare для {symbol}")
                return None
        else:
            print(f"Ошибка CryptoCompare API: {response.status_code}")
            return None
    except Exception as e:
        print(f"Ошибка CryptoCompare для {symbol}: {e}")
        return None

def get_rsi_1h_cryptocompare(symbol):
    """RSI 1H с CryptoCompare hourly"""
    try:
        prices = get_cryptocompare_historical(symbol, timeframe='hour',
                                             limit=100)
        if prices and len(prices) >= 15:
            rsi = calculate_rsi(prices, 14)
            print(f"RSI 1H для {symbol}: {rsi}")
            return rsi
        return None
    except Exception as e:
        print(f"Ошибка RSI 1H для {symbol}: {e}")
        return None

def get_rsi_daily_cryptocompare(symbol):
    """RSI Daily с CryptoCompare daily"""
    try:
        prices = get_cryptocompare_historical(symbol, timeframe='day',
                                             limit=50)
        if prices and len(prices) >= 15:
            rsi = calculate_rsi(prices, 14)
            print(f"RSI Daily для {symbol}: {rsi}")
            return rsi
        return None
    except Exception as e:
        print(f"Ошибка RSI Daily для {symbol}: {e}")
        return None

def get_sp500_yfinance():
    """S&P 500 через yfinance"""
    try:
        ticker = yf.Ticker("^GSPC")
        hist = ticker.history(period="2d")
        if len(hist) >= 2:
            current = hist['Close'].iloc[-1]
            prev_close = hist['Close'].iloc[-2]
            change = ((current - prev_close) / prev_close) * 100
            print(f"S&P 500 yfinance: {current}, change: {change:.2f}%")
            return round(current, 2), round(change, 2)
        print("Не удалось получить историю из yfinance")
        return None, None
    except Exception as e:
        print(f"Ошибка yfinance S&P 500: {e}")
        return None, None

def get_sp500_scrape():
    """Fallback scraping S&P 500 с Yahoo Finance"""
    try:
        url = "https://finance.yahoo.com/quote/%5EGSPC"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            price_elem = soup.find(
                'fin-streamer',
                {'data-symbol': '^GSPC',
                 'data-field': 'regularMarketPrice'}
            )
            change_elem = soup.find(
                'fin-streamer',
                {'data-symbol': '^GSPC',
                 'data-field': 'regularMarketChangePercent'}
            )
            if price_elem and change_elem:
                current_str = price_elem.text.replace(',', '')
                current = float(current_str) if current_str else None
                ch_str = (change_elem.text.strip('() %')
                         .replace('%', '').replace('(', '').replace(')', ''))
                ch = float(ch_str) if ch_str else 0
                print(f"S&P 500 scrape: {current}, change: {ch:.2f}%")
                return round(current, 2), round(ch, 2)
        return None, None
    except Exception as e:
        print(f"Ошибка scraping S&P 500: {e}")
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
    """Топ-4 крипты с CoinGecko + RSI с CryptoCompare"""
    url = (
        "https://api.coingecko.com/api/v3/coins/markets?"
        "vs_currency=usd&order=market_cap_desc&per_page=10&page=1&"
        "sparkline=false&price_change_percentage=24h"
    )
    
    try:
        print("Получение топ криптовалют...")
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            print(f"API ошибка: {response.status_code}")
            return []
            
        data = response.json()
        cryptos = []
        
        # Маппинг для символов
        symbol_map = {
            'BTC': 'BTC',
            'ETH': 'ETH',
            'BNB': 'BNB',
            'SOL': 'SOL'
        }
        
        for coin in data:
            symbol_upper = coin.get('symbol', '').upper()
            if symbol_upper in ['USDT', 'XRP', 'USDC']:
                continue
            
            if symbol_upper not in symbol_map:
                continue
                
            cryptos.append({
                'symbol': symbol_upper,
                'price': coin.get('current_price', 0),
                'change_24h': coin.get('price_change_percentage_24h', 0)
            })
            
            if len(cryptos) == 4:
                break
        
        print(f"Найдено {len(cryptos)} криптовалют")
        
        # Получаем RSI с CryptoCompare
        for crypto in cryptos:
            print(f"\n--- Обработка {crypto['symbol']} ---")
            
            # RSI 1H
            crypto['rsi_1h'] = get_rsi_1h_cryptocompare(crypto['symbol'])
            time.sleep(0.5)
            
            # RSI Daily
            crypto['rsi_daily'] = get_rsi_daily_cryptocompare(
                crypto['symbol']
            )
            time.sleep(0.5)
                
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
        return (float(latest.get('value', 0)),
                latest.get('value_classification', 'Unknown'),
                value_change)
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
    header = (f"#Крипта #Crypto\n{day_name.capitalize()} {day_num} "
              f"{month_name}, неделя {week_num}")
    
    # Основной контент (в spoiler)
    main_content = f"<b>{header}</b>\n\n"
    
    # S&P 500 with fallback
    sp_price, sp_change = get_sp500_yfinance()
    if not sp_price:
        sp_price, sp_change = get_sp500_scrape()
    
    if sp_price:
        main_content += (f"📊 S&P 500: {format_number(sp_price)} "
                        f"{sp_change:+.2f}%\n")
    else:
        main_content += "📊 S&P 500: Нет данных\n"

    # USD/RUB
    rub_price, rub_change = get_usd_rub_cbr()
    if not rub_price:
        rub_price, rub_change = get_usd_rub_coingecko()
    
    if rub_price:
        main_content += f"💵 USD/RUB: {rub_price:.2f} {rub_change:+.2f}%\n"
    else:
        main_content += "💵 USD/RUB: Нет данных\n"

    # Fear & Greed
    fg_value, fg_class, fg_change = get_fear_greed()
    if fg_value:
        main_content += (f"😱 Crypto Fear & Greed: {fg_value:.0f} "
                        f"({fg_class})\n")
    else:
        main_content += "😱 Crypto Fear & Greed: Нет данных\n"

    # BTC Dominance
    btc_dom = get_btc_dominance()
    if btc_dom:
        main_content += f"₿ BTC Dominance: {btc_dom:.0f}%\n\n"
    else:
        main_content += "₿ BTC Dominance: Нет данных\n\n"

    # Топ-4 крипто + RSI
    cryptos = get_top_cryptos()
    main_content += "📈 Топ Крипто (USD):\n\n"
    
    if cryptos:
        max_sym_len = max(len(c['symbol']) for c in cryptos) + 1
        max_price_len = max(
            len(f"${format_number(c['price'])}") for c in cryptos
        )
        
        for crypto in cryptos:
            change_emoji = "🟢" if crypto['change_24h'] >= 0 else "🔴"
            sym_padded = f"{crypto['symbol']} ".ljust(max_sym_len)
            price_padded = (f"${format_number(crypto['price'])}"
                           .ljust(max_price_len))
            change_str = f"{crypto['change_24h']:+.0f}%"
            
            rsi_1h_str = (f"{crypto['rsi_1h']:.0f}"
                         if crypto['rsi_1h'] is not None else "N/A")
            rsi_d_str = (f"{crypto['rsi_daily']:.0f}"
                        if crypto['rsi_daily'] is not None else "N/A")
            
            # Используем rsi_1h для сигнала, fallback на rsi_daily
            signal_rsi = (crypto['rsi_1h']
                         if crypto['rsi_1h'] is not None
                         else crypto['rsi_daily'])
            signal = (get_trading_signal(signal_rsi, fg_value)
                     if fg_value is not None else "N/A")
            
            main_content += (f"{change_emoji} {sym_padded}: {price_padded} "
                            f"{change_str} | <code>RSI (1H/D): "
                            f"{rsi_1h_str}/{rsi_d_str} {signal}</code>\n")
    else:
        main_content += "Нет данных\n"
    
    # Финальное сообщение со spoiler
    message = f"<tg-spoiler>{main_content}</tg-spoiler>"
    
    # Мудрость дня (вне spoiler)
    message += f"\n\n💭 Мудрость дня:\n{get_daily_wisdom()}"

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
            print(f"Отправленное сообщение:\n{message[:500]}...")
        else:
            print(f"Ошибка отправки: {response.status_code} - "
                  f"{response.text}")
    except Exception as e:
        print(f"Исключение при отправке: {e}")

if __name__ == "__main__":
    send_telegram_message()
