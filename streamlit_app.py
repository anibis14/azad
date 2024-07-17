import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import plotly.express as px
import time
import threading

# Initialisation de la variable globale en haut du fichier
last_transaction_time = datetime.min

# URLs pour les APIs des brokers
APIS = {
    "Binance": "https://api.binance.com/api/v3/ticker/24hr",
    "Coinbase": "https://api.coinbase.com/v2/prices/",
    "Bitfinex": "https://api-pub.bitfinex.com/v2/ticker/",
    "Bittrex": "https://api.bittrex.com/v3/markets/tickers",
    "Huobi": "https://api.huobi.pro/market/tickers"
}

# Frais de transaction par broker (ajusté à 0.3%)
FEES = {
    "Binance": 0.15,  # 0.3%
    "Coinbase": 0.15,  # 0.3%
    "Bitfinex": 0.15,  # 0.3%
    "Bittrex": 0.15,  # 0.3%
    "Huobi": 0.15  # 0.3%
}

# Variables globales pour stocker les données mises à jour
prices_df = pd.DataFrame()
total_gain = 0
transaction_history = []
custom_fees = 0.15
capital_invested = 100
time_between_ops = 30
min_spread_percent = 0.4

# Collecte des données de prix depuis les APIs des brokers
def get_prices(broker):
    try:
        if broker == "Binance":
            response = requests.get(APIS["Binance"])
            data = response.json()
            df = pd.DataFrame(data)
            df = df[df['symbol'].isin(['BTCUSDT', 'ETHUSDT', 'LTCUSDT', 'XRPUSDT', 'BCHUSDT'])]
            df['price'] = df['lastPrice'].astype(float)
            df['symbol'] = df['symbol'].str.replace('USDT', 'USD')
        elif broker == "Coinbase":
            symbols = ['BTC-USD', 'ETH-USD', 'LTC-USD', 'XRP-USD', 'BCH-USD']
            data = []
            for symbol in symbols:
                response = requests.get(f"https://api.coinbase.com/v2/prices/{symbol}/spot")
                price = float(response.json()['data']['amount'])
                data.append({"symbol": symbol.replace('-', ''), "price": price})
            df = pd.DataFrame(data)
        elif broker == "Bitfinex":
            symbols = ['tBTCUSD', 'tETHUSD', 'tLTCUSD', 'tXRPUSD', 'tBCHUSD']
            data = []
            for symbol in symbols:
                response = requests.get(APIS["Bitfinex"] + symbol)
                price = float(response.json()[6])
                data.append({"symbol": symbol[1:], "price": price})
            df = pd.DataFrame(data)
        elif broker == "Bittrex":
            response = requests.get(APIS["Bittrex"])
            data = pd.read_json(io.StringIO(response.content.decode('utf-8-sig')))
            df = data[data['symbol'].isin(['BTC-USD', 'ETH-USD', 'LTC-USD', 'XRP-USD', 'BCH-USD'])]
            df['symbol'] = df['symbol'].str.replace('-', '')
        elif broker == "Huobi":
            response = requests.get(APIS["Huobi"])
            data = response.json()
            df = pd.DataFrame(data['data'])
            df = df[df['symbol'].isin(['btcusdt', 'ethusdt', 'ltcusdt', 'xrpusdt', 'bchusdt'])]
            df['symbol'] = df['symbol'].str.replace('usdt', 'usd').str.upper()
            df['price'] = df['close'].astype(float)
        df['broker'] = broker
        df['timestamp'] = datetime.now()
        return df[['symbol', 'price', 'broker', 'timestamp']]
    except Exception as e:
        st.error(f"Error fetching {broker} prices: {e}")
        return pd.DataFrame()

def collect_all_prices():
    brokers = ["Binance", "Coinbase", "Bitfinex", "Bittrex", "Huobi"]
    prices = pd.concat([get_prices(broker) for broker in brokers], ignore_index=True)
    return prices

def find_arbitrage_opportunities(prices_df):
    opportunities = []
    symbols = prices_df['symbol'].unique()

    for symbol in symbols:
        symbol_prices = prices_df[prices_df['symbol'] == symbol]

        for i, row in symbol_prices.iterrows():
            for j, other_row in symbol_prices.iterrows():
                if row['broker'] != other_row['broker']:
                    buy_broker = row['broker']
                    sell_broker = other_row['broker']

                    buy_price = row['price']
                    sell_price = other_row['price']
                    spread_percent = (sell_price - buy_price) / buy_price * 100

                    # Prendre position si le spread brut est supérieur ou égal au spread minimum défini par l'utilisateur
                    if spread_percent >= min_spread_percent:
                        buy_price_with_fees = buy_price * (1 + custom_fees / 100)
                        sell_price_with_fees = sell_price * (1 - custom_fees / 100)
                        profit = sell_price_with_fees - buy_price_with_fees

                        opportunities.append({
                            "symbol": symbol,
                            "buy_broker": buy_broker,
                            "sell_broker": sell_broker,
                            "buy_price": buy_price,
                            "sell_price": sell_price,
                            "profit": profit,
                            "timestamp": datetime.now()
                        })

    return pd.DataFrame(opportunities)

# Fonction pour exécuter les transactions d'arbitrage
def execute_arbitrage_opportunities(opportunities_df):
    global total_gain, transaction_history, last_transaction_time
    for i, opportunity in opportunities_df.iterrows():
        current_time = datetime.now()
        if (current_time - last_transaction_time).total_seconds() >= time_between_ops:
            net_profit = opportunity['profit']
            total_gain += net_profit
            transaction_history.append({
                "symbol": opportunity['symbol'],
                "buy_broker": opportunity['buy_broker'],
                "sell_broker": opportunity['sell_broker'],
                "profit": net_profit,
                "timestamp": datetime.now()
            })
            st.write(f"Executed arbitrage: Bought {opportunity['symbol']} on {opportunity['buy_broker']} and sold on {opportunity['sell_broker']} for a net profit of {net_profit:.2f} USD")
            last_transaction_time = current_time

# Fonction pour mettre à jour les données globales
def update_data():
    global prices_df
    while True:
        new_data = collect_all_prices()
        prices_df = pd.concat([prices_df, new_data], ignore_index=True)
        opportunities_df = find_arbitrage_opportunities(prices_df)
        execute_arbitrage_opportunities(opportunities_df)
        time.sleep(1)  # Pause de 1 seconde entre chaque mise à jour

# Lancer la mise à jour des données en arrière-plan
data_thread = threading.Thread(target=update_data)
data_thread.start()

st.title('Crypto Prices and Arbitrage Dashboard')

# Interface utilisateur pour les paramètres
st.sidebar.header('Settings')
custom_fees = st.sidebar.number_input('Transaction Fees (%)', value=custom_fees, step=0.01)
capital_invested = st.sidebar.number_input('Capital Invested (USD)', value=capital_invested, step=1)
time_between_ops = st.sidebar.number_input('Time Between Operations (seconds)', value=time_between_ops, step=1)
min_spread_percent = st.sidebar.number_input('Minimum Spread (%)', value=min_spread_percent, step=0.01)

# Affichage des gains totaux
st.header('Total Net Gain')
st.subheader(f'{total_gain:.2f} USD')

# Affichage des transactions
st.header('Transaction History')
for tx in transaction_history:
    st.write(f"{tx['timestamp']} - Bought {tx['symbol']} on {tx['buy_broker']} and sold on {tx['sell_broker']} for a net profit of {tx['profit']} USD")

# Affichage des graphiques
st.header('Price Graphs')
if not prices_df.empty:
    for symbol in prices_df['symbol'].unique():
        symbol_df = prices_df[prices_df['symbol'] == symbol]
        fig = px.line(symbol_df, x='timestamp', y='price', color='broker', title=f"Prices for {symbol}")

        # Calculer l'écart maximum en pourcentage pour ce symbole
        max_spread_info = calculate_max_spread(symbol_df)
        spread_style = {'fontSize': 16}
        if max_spread_info['spread'] >= 0.6:
            spread_style.update({'color': 'green', 'fontWeight': 'bold'})
        max_spread_text = f"Max Spread: {max_spread_info['spread']:.2f}% (Buy on {max_spread_info['buy_broker']}, Sell on {max_spread_info['sell_broker']})"

        st.plotly_chart(fig)
        st.markdown(f"<div style='font-size: 16px; {spread_style}'>{max_spread_text}</div>", unsafe_allow_html=True)

