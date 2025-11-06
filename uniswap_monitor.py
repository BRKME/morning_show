import requests
import pandas as pd
import time
from datetime import datetime
import random
import yfinance as yf  # pip install yfinance

# Конфиг Telegram
BOT_TOKEN = '8442392037:AAEiM_b4QfdFLqbmmc1PXNvA99yxmFVLEp8'
CHAT_ID = '350766421'

# Список мудростей дня
WISDOMS = [
    "Единственный приоритет - защита капитала, только потом умножение. (Без фундамента небоскрёб рухнет.)",
    "Не будь дураком (Проверь: нет ли здесь «быстрой наживы» или сомнительных обещаний)",
    "Играй в долгую (Мои инвестиции соответствует моему плану на годы, а не на день.)",
    "Дисциплина > эмоции (Решение всегда основано на стратегии, а не на страхе или жадности.)",
    "Риски под контролем (Я понимаю, что могу потерять, и готов к этому.)"
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

def get_coingecko_historical(coin_id, days=30, interval='daily'):
    """Получение исторических цен с CoinGecko - возвращает список цен закрытия"""
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        params = {
            'vs_currency': 'usd',
            'days': days,
            'interval': interval
        }
        
        print(f"Запрос CoinGecko: {coin_id}, days={days}, interval={interval}")
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            # Извлекаем цены (prices: [timestamp, price])
            prices = [price for timestamp, price in data['prices']]
            print(f"Получено {len(prices)} цен для {coin_id}")
            return prices
        else:
            print(f"Ошибка CoinGecko API: {response.status_code} - {response.text[:100]}")
            return None
    except Exception as e:
        print(f"Ошибка CoinGecko для {coin_id}: {e}")
        return None

def get_rsi_2h_coingecko(coin_id):
    """RSI 2H - используем hourly данные и resample to 2H"""
    try:
        # Берем hourly данные за 7 дней (для ~84 hourly points, enough for RSI14 on 2h)
        hourly_prices = get_coingecko_historical(coin_id, days=7, interval='hourly')
        if not hourly_prices or len(hourly_prices) < 20:
            return None
        
        # Resample to 2H
        df = pd.DataFrame({'price': hourly_prices})
        # Assume timestamps are sequential hourly, generate timestamps for resample
        start_time = pd.Timestamp.now() - pd.Timedelta(hours=len(hourly_prices))
        df['timestamp'] = pd.date_range(start=start_time, periods=len(df), freq='H')
        df.set_index('timestamp', inplace=True)
        df_2h = df['price'].resample('2H').last().dropna()  # Last price in 2h bin
        
        if len(df_2h) < 15:
            return None
        
        rsi = calculate_rsi(df_2h.tolist(), 14)
        print(f"RSI 2H для {coin_id}: {rsi}")
        return rsi
    except Exception as e:
        print(f"Ошибка RSI 2H для {coin_id}: {e}")
        return None

def get_rsi_daily_coingecko(coin_id):
    """RSI Daily - дневные данные"""
    try:
        prices = get_coingecko_historical(coin_id, days=50, interval='daily')
        if prices and len(prices) >= 15:
            rsi = calculate_rsi(prices, 14)
            print(f"RSI Daily для {coin_id}: {rsi}")
            return rsi
        return None
    except Exception as e:
        print(f"Ошибка RSI Daily для {coin_id}: {e}")
        return None

def get_sp500_yfinance():
    """S&P 500 через yfinance"""
    try:
        ticker = yf.Ticker("^GSPC")
        info = ticker.info
        current = info.get('regularMarketPrice')
        prev_close = info.get('previousClose')
        
        if current and prev_close:
            change = ((current - prev_close) / prev_close) * 100
            print(f"S&P 500: {current}, change: {change:.2f}%")
            return round(current, 2), round(change, 2)
        print("Не удалось извлечь данные из yfinance info")
        return None, None
    except Exception as e:
        print(f"Ошибка yfinance S&P 500: {e}")
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
    """Топ-4 крипты с CoinGecko + RSI с CoinGecko"""
    url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=10&page=1&sparkline=false&price_change_percentage=24h"
    
    try:
        print("Получение топ криптовалют...")
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            print(f"API ошибка: {response.status_code}")
            return []
            
        data = response.json()
        cryptos = []
        
        # Маппинг для CoinGecko IDs
        coingecko_map = {
            'BTC': {'symbol': 'BTC', 'id': 'bitcoin'},
            'ETH': {'symbol': 'ETH', 'id': 'ethereum'},
            'BNB': {'symbol': 'BNB', 'id': 'binancecoin'},
            'SOL': {'symbol': 'SOL', 'id': 'solana'}
        }
        
        for coin in data:
            symbol_upper = coin.get('symbol', '').upper()
            if symbol_upper in ['USDT', 'XRP', 'USDC']:
                continue
            
            if symbol_upper not in coingecko_map:
                continue
                
            mapped = coingecko_map[symbol_upper]
            cryptos.append({
                'id': mapped['id'],
                'name': coin.get('name', 'Unknown'),
                'symbol': mapped['symbol'],
                'price': coin.get('current_price', 0),
                'change_24h': coin.get('price_change_percentage_24h', 0)
            })
            
            if len(cryptos) == 4:
                break
        
        print(f"Найдено {len(cryptos)} криптовалют")
        
        # Получаем RSI с CoinGecko
        for crypto in cryptos:
            print(f"\n--- Обработка {crypto['symbol']} ---")
            
            # RSI 2H
            crypto['rsi_2h'] = get_rsi_2h_coingecko(crypto['id'])
            time.sleep(1.0)  # Задержка для rate limit CoinGecko (~50 calls/min)
            
            # RSI Daily
            crypto['rsi_daily'] = get_rsi_daily_coingecko(crypto['id'])
            time.sleep(1.0)
                
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
    sp_price, sp_change = get_sp500_yfinance()
    
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
            
            signal = get_trading_signal(crypto['rsi_2h'], fg_value) if fg_value is not None else "N/A"
            
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
            print(f"Отправленное сообщение:\n{message[:500]}...")  # Лог для отладки
        else:
            print(f"Ошибка отправки: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Исключение при отправке: {e}")

if __name__ == "__main__":
    send_telegram_message()
