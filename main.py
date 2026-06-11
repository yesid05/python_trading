import time
import pandas as pd
from binance.client import Client
from ta.momentum import RSIIndicator
from telegram import Bot
import requests
from decouple import config

# Credenciales Binance

API_KEY = config("API_KEY")
API_SECRET = config("API_SECRET")
SYMBOL = "BTCUSDC"
INTERVAL = Client.KLINE_INTERVAL_1MINUTE
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
    return df
def detectar_tendencia(df):
    
    ultimo = df.iloc[-1]
    ma9 = ultimo['MA9']
    ma48 = ultimo['MA48']
    rsi = ultimo['RSI10']
    
    #and float(ultimo['volume']) > float(ultimo['VOL_MA20'])
    #and float(ultimo['volume']) < float(ultimo['VOL_MA20'])
    
    
    if ma9 > ma48 and rsi > 50 :
        return "ALCISTA", ma9, ma48, rsi
    elif ma9 < ma48 and rsi < 50 :
        return "BAJISTA", ma9, ma48, rsi
    return "NEUTRAL", ma9, ma48, rsi


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

def senal_compra(ma9, ma48, rsi):    
    return ma9 > ma48 and rsi > 55 and rsi < 65

def senal_venta(ma9, ma48, rsi):
    return ma9 < ma48 or rsi < 45 and rsi > 60

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
    
    distancia_al_stop_loss = precio_actual * 0.0015
    
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

while True:
    try:
        
        print(f"Balance USDC {balance_usdc()}")
        print(f"Balance CRYPTO {balance_crypto()}")
        
        df = obtener_datos(SYMBOL, INTERVAL)
        df = calcular_indicadores(df)
        tendencia, ma9, ma48, rsi = detectar_tendencia(df)
        print(
            f"[{pd.Timestamp.now()}] "
            f"Tendencia: {tendencia} | "
            f"MA9={ma9:.2f} | "
            f"MA48={ma48:.2f} | "
            f"RSI10={rsi:.2f}"
        )
        
        if ma9 < ma48 and venta_realizada == True:
            venta_realizada = False
            compra_realizada = False
        
        precio_ahora = precio_actual(df)
        
        if tendencia == "ALCISTA" and compra_realizada == False:
            
            if senal_compra(ma9, ma48, rsi) == True:
                
                print(f"Precio actual {precio_ahora}")
                
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
        
        else:
            print(f"Compra realizada {compra_realizada}")
            print(f"Señal de venta {senal_venta(ma9, ma48, rsi)}")
            print(f"Vanta realizada {venta_realizada}")
            if compra_realizada == True and senal_venta(ma9, ma48, rsi) == True and venta_realizada == False:
                
                if precio_ahora >= precio_equilibrio:
                    
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
                    
                else:
                    print(f"Precio objetivo de venta no alcanzado: Precio actual {precio_ahora} Precio Objetivo {precio_equilibrio}")
                
    except Exception as e:
        print("Error:", e.with_traceback())
    time.sleep(20)