import hmac
import hashlib
import requests
import sys
import time
import base64
import json
from collections import OrderedDict
from Data import *
from fc_config import *

class Api():
    def __init__(self,base_url = 'https://api.fcoin.com/v2/'):
        self.base_url = base_url
        self.key = bytes(Ath['key'], 'utf-8')
        self.secret = bytes(Ath['secret'], 'utf-8')

    def public_request(self, method, api_url, **payload):
        """request public url"""
        r_url = self.base_url + api_url
        try:
            r = requests.request(method, r_url, params=payload)
            r.raise_for_status()
        except requests.exceptions.HTTPError as err:
            print(err)
        if r.status_code == 200:
            return r.json()

    def get_signed(self, sig_str):
        """signed params use sha512"""
        sig_str = base64.b64encode(sig_str)
        signature = base64.b64encode(hmac.new(self.secret, sig_str, digestmod=hashlib.sha1).digest())
        return signature


    def signed_request(self, method, api_url, **payload):
        """request a signed url"""

        param=''
        if payload:
            sort_pay = sorted(payload.items())
            #sort_pay.sort()
            for k in sort_pay:
                param += '&' + str(k[0]) + '=' + str(k[1])
            param = param.lstrip('&')
        timestamp = str(int(time.time() * 1000))
        full_url = self.base_url + api_url

        if method == 'GET':
            if param:
                full_url = full_url + '?' + param
            sig_str = method + full_url + timestamp
        elif method == 'POST':
            sig_str = method + full_url + timestamp + param

        signature = self.get_signed(bytes(sig_str, 'utf-8'))

        headers = {
            'FC-ACCESS-KEY': self.key,
            'FC-ACCESS-SIGNATURE': signature,
            'FC-ACCESS-TIMESTAMP': timestamp
        }

        r = {}
        try:
            r = requests.request(method, full_url, headers=headers, json=payload, timeout=2)
            # r.raise_for_status()
        except requests.exceptions.HTTPError as err:
            # print(err)
            print(r.text)
        finally:
            pass

        if r.status_code == 200:
            return r.json()

    def get_server_time(self):
        """Get server time"""
        return self.public_request('GET','public/server-time')['data']


    def get_currencies(self):
        """get all currencies"""
        return self.public_request('GET', 'public/currencies')['data']

    def get_symbols(self):
        """get all symbols"""
        return self.public_request('GET', 'public/symbols')['data']

    def get_market_ticker(self, symbol):
        """get market ticker"""
        result = self.public_request('GET', 'market/ticker/{symbol}'.format(symbol=symbol))
        if result == None:
            return None
        ticker = Ticker()
        if  'data' not in result:
            return  None
        ticker.last = float(result['data']['ticker'][0])
        ticker.symbol = symbol
        return  ticker

    def get_market_depth(self, level, symbol):
        """get market depth"""
        return self.public_request('GET', 'market/depth/{level}/{symbol}'.format(level=level, symbol=symbol))

    def get_trades(self,symbol):
        """get detail trade"""
        return self.public_request('GET', 'market/trades/{symbol}'.format(symbol=symbol))

    def get_balance(self):
        """get user balance"""
        json = self.signed_request('GET', 'accounts/balance')
        if json == None:
            return None
        result={}
        if 'data' not in json:
            return None
        json=json['data']
        if len(json) ==0:
            return None
        for b in json:
            balance = Balance()
            balance.available = float(b['available'])
            balance.currency = b['currency'].lower()
            balance.frozen = float(b['frozen'])
            balance.balance = float(b['balance'])
            result[balance.currency] = balance
            #print(balance)
        return result

    def list_orders(self, **payload):
        """get orders"""

        json = self.signed_request('GET','orders', **payload)
        if json == None:
            return None
        order_list = []
        json = json['data']
        if json == None:
            return None
        if len(json) == 0 :
            return None
        for t in json:
            order=Order()
            order.id = t['id']
            order.price = float(t['price'])
            order.amount = float(t['amount'])
            order.created_at = int(t['created_at'])
            if t['side'] == 'buy':
                order.side = Side.buy
            else:
                order.side = Side.sell
            if t['state'] == 'filled':
                order.state = State.filled
            elif t['state'] == 'submitted':
                order.state = State.submitted
            order_list.append(order)
            #print(order)
        return order_list

    def create_order(self, **payload):
        """create order"""
        return self.signed_request('POST','orders', **payload)

    def buy(self,symbol, price, amount):
        """buy someting"""
        return self.create_order(symbol=symbol, side='buy', type='limit', price=str(price), amount=amount)

    def buy_market(self,symbol, amount):
        """buy someting"""
        return self.create_order(symbol=symbol, side='buy',  amount=str(amount),type='market')

    def sell(self, symbol, price, amount):
        """buy someting"""
        return self.create_order(symbol=symbol, side='sell', type='limit', price=str(price), amount=amount)

    def sell_market(self, symbol, amount):
        """buy someting"""
        return self.create_order(symbol=symbol, side='sell',  amount=str(amount),type='market')

    def get_order(self,order_id):
        """get specfic order"""
        return self.signed_request('GET', 'orders/{order_id}'.format(order_id=order_id))

    def cancel_order(self,order_id):
        """cancel specfic order"""
        return self.signed_request('POST', 'orders/{order_id}/submit-cancel'.format(order_id=order_id))

    def order_result(self, order_id):
        """check order result"""
        return self.signed_request('GET', 'orders/{order_id}/match-results'.format(order_id=order_id))
    def get_candle(self,resolution, symbol, **payload):
        """get candle data"""
        return self.public_request('GET', 'market/candles/{resolution}/{symbol}'.format(resolution=resolution, symbol=symbol), **payload)

# 守护进程
if __name__ == '__main__':
    api = Api()
    #print(api.get_market_ticker('btcusdt'))
    print(api.get_balance())
    print(api.buy('btcusdt',6400,0.01))
    print(api.list_orders(symbol='btcusdt',state=State.filled))

