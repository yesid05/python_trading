import time
import pandas as pd
from binance.client import Client
from binance import ThreadedWebsocketManager
from ta.momentum import RSIIndicator
from ta.trend import MACD
from telegram import Bot
import requests
from decouple import config

# Credenciales Binance

API_KEY = config("API_KEY")
API_SECRET = config("API_SECRET")
SYMBOL = "BTCUSDC"
INTERVAL = Client.KLINE_INTERVAL_5MINUTE
usdc = 50
crypto = 0
precio_equilibrio = 0
precio_perdida = 0
precio_venta = 0


TOKEN_TELEGRAM = config("TOKEN_TELEGRAM")
CHAT_ID_TELEGRAM = config("CHAT_ID_TELEGRAM")


def enviar_alerta(mensaje):
    
    url = f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendMessage"

    

    requests.post(url, json={
        "chat_id": CHAT_ID_TELEGRAM,
        "text": mensaje
    })
    
client = Client(API_KEY, API_SECRET)
def obtener_datos(symbol, interval, limit=100):
    klines = client.get_klines(
        symbol=symbol,
        interval=interval,
        limit=limit
    )
    df = pd.DataFrame(
        klines,
        columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base', 'taker_buy_quote', 'ignore'
        ]
    )
    df['close'] = df['close'].astype(float)
    return df
def calcular_indicadores(df):
    df['MA9'] = df['close'].rolling(9).mean()
    df['MA48'] = df['close'].rolling(48).mean()
    
    rsi = RSIIndicator(close=df['close'], window=10)
    df['RSI10'] = rsi.rsi()
    
    df['VOL_MA20'] = df['volume'].rolling(20).mean()
    
    macd = MACD(
        close=df['close'],
        window_slow=26,
        window_fast=12,
        window_sign=9
    )
    
    df['macd'] = macd.macd()
    df['signal'] = macd.macd_signal()
    df['histogram'] = macd.macd_diff()
    
    return df

def detectar_tendencia(df):
    
    ultimo = df.iloc[-1]
    ma9 = ultimo['MA9']
    ma48 = ultimo['MA48']
    rsi = ultimo['RSI10']
    histogram = ultimo['histogram']
    
    #and float(ultimo['volume']) > float(ultimo['VOL_MA20'])
    #and float(ultimo['volume']) < float(ultimo['VOL_MA20'])
    
    
    if ma9 > ma48 and rsi > 50 :
        return "ALCISTA", ma9, ma48, rsi, histogram
    elif ma9 < ma48 and rsi < 50 :
        return "BAJISTA", ma9, ma48, rsi, histogram
    return "NEUTRAL", ma9, ma48, rsi, histogram


RISK_PER_TRADE = 0.01      # 1%
STOP_LOSS_PCT = 0.005      # 0.5%
TAKE_PROFIT_PCT = 0.01     # 1%Precio

def calcular_crypto_comprar(balance_usdt, precio):
    
    dinero_para_comprar = balance_usdt - calcular_comision(balance_usdt)
    
    return float(dinero_para_comprar / precio)
    
    """
    riesgo_usdt = balance_usdt * RISK_PER_TRADE
    perdida_por_unidad = precio * STOP_LOSS_PCT
    cantidad = riesgo_usdt / perdida_por_unidad
    return round(cantidad, 5)
    """
def calcular_usdc_comprar(balance_cripto, precio):
    
    dinero_bruto_venta = balance_cripto * precio
    
    return float(dinero_bruto_venta - calcular_comision(dinero_bruto_venta))

def calcular_precio_equilibrio(precio):
    return precio / (1 - 0.001)**2

def senal_compra(ma9, ma48, rsi, histogram):
    
    """
    # Compra: MACD cruza por encima de la señal
df['buy_signal'] = (
    (df['macd'].shift(1) < df['signal'].shift(1)) &
    (df['macd'] > df['signal'])
)

# Venta: MACD cruza por debajo de la señal
df['sell_signal'] = (
    (df['macd'].shift(1) > df['signal'].shift(1)) &
    (df['macd'] < df['signal'])
)
rsi > 50 and rsi < 80
    """
    return ma9 < ma48 and histogram > 0

def senal_venta(precio_cierre, precio_compra, histogram):
    return precio_cierre >= (precio_compra + 131) and histogram < 0

def precio_actual(df):
    return float(df.iloc[-1]["close"])

def balance_usdc():
    return float(usdc)
    """
    return float(
            client.get_asset_balance(asset="USDT")["free"]
        )
    """
def balance_crypto():
    return float(crypto)

def calcular_comision(balance):
    return float(balance * 0.001)

def cantidad_comprar(precio_actual):
    
    return calcular_crypto_comprar(
            balance_usdc(),
            precio_actual
        )

def cantidad_vender(precio_actual):
    return calcular_usdc_comprar(
        balance_crypto(),
        precio_actual
    )
    
def stop_loss(precio_actual):
    
    distancia_al_stop_loss = precio_actual * 0.003
    
    return precio_actual - distancia_al_stop_loss

def take_profit(precio_actual):
    return precio_actual * (1 + TAKE_PROFIT_PCT)

def comprar(precio_actual, cantidad, stop_loss, take_profit):
    
    print("COMPRA EJECUTADA")
    print("Entrada:", precio_actual)
    print("Comisión:", calcular_comision(usdc))
    print("SL:", stop_loss)
    print("TP:", take_profit)
    
    return {"symbolo":"BTCUSDC","quantity":cantidad}

def vender(precio_actual, cantidad, stop_loss, take_profit):
    
    print("VENTA EJECUTADA")
    print("Entrada:", precio_actual)
    print("Comisión:", calcular_comision(usdc))
    print("SL:", stop_loss)
    print("TP:", take_profit)
    
    return {"symbolo":"BTCUSDC","quantity":cantidad}

"""
def venta(precio_actual,cantidad,stop_loss,take_profit):
    
    if precio_actual <= stop_loss:
        vender(cantidad,stop_loss,take_profit,precio_ahora=precio_actual)
        print("STOP LOSS")
    elif precio_actual >= take_profit:
        venta(precio_actual,cantidad)
        print("TAKE PROFIT")
    else:
orden = client.order_market_buy(
    symbol="BTCUSDT",
    quantity=cantidad
)

client.order_market_sell(
            symbol="BTCUSDT",
            quantity=cantidad
        )
"""

stop_loss_compra = 0
take_profit_compra = 0
compra_realizada = False
venta_realizada = False
vender_bajo_precio = False
precio_de_compra = 0

def ejecutar_estrategia():
    try:
                
        global compra_realizada
        global venta_realizada
        global vender_bajo_precio
        global precio_de_compra
        global precio_equilibrio
        global precio_perdida
        global cantidad_comprada
        global crypto
        global usdc
        
        print(f"Balance USDC {balance_usdc()}")
        print(f"Balance CRYPTO {balance_crypto()}")
        
        df = obtener_datos(SYMBOL, INTERVAL)
        df = calcular_indicadores(df)
        
        print(df)
        
        tendencia, ma9, ma48, rsi, histogram = detectar_tendencia(df)
        print(
            f"[{pd.Timestamp.now()}] "
            f"Tendencia: {tendencia} | "
            f"MA9={ma9:.2f} | "
            f"MA48={ma48:.2f} | "
            f"RSI10={rsi:.2f}"
            f"HISTOGRAM={histogram:.2f}"
        )
        
        if ma9 < ma48 and venta_realizada == True:
            venta_realizada = False
            compra_realizada = False
        
        if ma9 > ma48 and compra_realizada == True:
            vender_bajo_precio = True
        
        precio_ahora = precio_actual(df)
        
        if tendencia == "BAJISTA" and compra_realizada == False:
            
            if senal_compra(ma9, ma48, rsi, histogram) == True:
                
                print(f"Precio actual {precio_ahora}")
                
                precio_de_compra = precio_ahora
                
                cantidad_comprada = cantidad_comprar(precio_ahora)
                crypto = cantidad_comprada
                print(f"Cantidad comprar {cantidad_comprada} BTC")
                
                precio_equilibrio = calcular_precio_equilibrio(precio=precio_ahora)
                print(f"Precio equilibrio {precio_equilibrio} USD")
                
                precio_perdida = stop_loss(precio_actual=precio_ahora)
                print(f"Precio perdida {precio_perdida} USD")
                
                comprar(precio_ahora,cantidad_comprada,stop_loss=stop_loss_compra,take_profit=take_profit_compra)
                
                enviar_alerta(
                    f"[{pd.Timestamp.now()}] \n"
                    f"===COMPRA REALIZADA=== \n "
                    f"Precio de compra: {precio_ahora} \n "
                    f"Precio equilibrio {precio_equilibrio} USD \n"
                    f"Cantidad comprar {cantidad_comprada} BTC \n "
                )
                
                compra_realizada = True
                vender_bajo_precio = False
        
        else:
            print(f"Compra realizada {compra_realizada}")
            print(f"Señal de venta {senal_venta(precio_cierre=precio_ahora,precio_compra=precio_de_compra,histogram=histogram)}")
            print(f"Vanta realizada {venta_realizada}")
            if compra_realizada == True and venta_realizada == False:
                
                if senal_venta(precio_cierre=precio_ahora,precio_compra=precio_de_compra, histogram=histogram) == True:
                    
                    cantidad_vendida = cantidad_vender(precio_actual=precio_ahora)
                    usdc = cantidad_vendida
                    print(f"Cantidad vender {cantidad_vendida} USDC")
                    
                    vender(precio_ahora,cantidad_vendida,stop_loss_compra,take_profit_compra)
                    
                    enviar_alerta(
                        f"[{pd.Timestamp.now()}] \n"
                        f"===VENTA REALIZADA=== \n "
                        f"Precio de venta: {precio_ahora} USDC \n "
                        f"Precio equilibrio {precio_equilibrio} USDC \n "
                        f"Cantidad vender {cantidad_vendida} USDC \n "
                        f"Balance {usdc}"
                    )
                    
                    venta_realizada = True
                    
                elif ma9 <= ma48 and vender_bajo_precio == True:
                    
                    cantidad_vendida = cantidad_vender(precio_actual=precio_ahora)
                    usdc = cantidad_vendida
                    print(f"Cantidad vender {cantidad_vendida} USDC")
                    
                    vender(precio_ahora,cantidad_vendida,stop_loss_compra,take_profit_compra)
                    
                    enviar_alerta(
                        f"[{pd.Timestamp.now()}] \n"
                        f"===VENTA REALIZADA=== \n "
                        f"Precio de venta: {precio_ahora} USDC \n "
                        f"Precio equilibrio {precio_equilibrio} USDC \n "
                        f"Cantidad vender {cantidad_vendida} USDC \n "
                        f"Balance {usdc}"
                    )
                    
                    venta_realizada = True
                
                elif precio_ahora <= precio_perdida:
                    
                    cantidad_vendida = cantidad_vender(precio_actual=precio_ahora)
                    usdc = cantidad_vendida
                    print(f"Cantidad vender precio perdida {cantidad_vendida} USDC")
                    
                    vender(precio_ahora,cantidad_vendida,stop_loss_compra,take_profit_compra)
                    
                    enviar_alerta(
                        f"[{pd.Timestamp.now()}] \n"
                        f"===VENTA REALIZADA=== \n "
                        f"Precio de venta: {precio_ahora} USDC \n "
                        f"Precio equilibrio {precio_equilibrio} USDC \n "
                        f"Cantidad vender {cantidad_vendida} USDC \n "
                        f"Balance {usdc}"
                    )
                    
                    venta_realizada = True
                                        
                else:
                    print(f"Precio objetivo de venta no alcanzado: Precio actual {precio_ahora} Precio Objetivo {precio_equilibrio}")
                
    except Exception as e:
        print("Error:", e.with_traceback())
  
def manejar_mensaje(msg):

    kline = msg['k']

    if kline['x']:  # vela cerrada
        print(
            f"Vela 5m cerrada - Close: {kline['c']}"
        )

        # Ejecutar estrategia
        ejecutar_estrategia()

twm = ThreadedWebsocketManager(
    api_key=API_KEY,
    api_secret=API_SECRET
)

twm.start()

twm.start_kline_socket(
    callback=manejar_mensaje,
    symbol=SYMBOL,
    interval=INTERVAL
)

twm.join()