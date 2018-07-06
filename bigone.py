# coding=utf-8

import hmac
import hashlib
import requests
import sys
import time
import base64
import json
from collections import OrderedDict
from Data import *
from bigone_config import *
import pycurl
import urllib
from io import StringIO
from io import BytesIO
import certifi
import jwt

class Api():
    def __init__(self,base_url = 'https://big.one/api/v2'):
        self.base_url = base_url
        self.account = Ath['account']
        self.key = Ath['key']
        self.secret = Ath['secret']
        self.session = self._init_session()

    def _init_session(self):
        session = requests.session()
        headers = {'Accept': 'application/json',
                       'User-Agent': 'python-bigone'}
        session.headers.update(headers)
        return session

    def create_uri(self, path):
        return '{}/{}'.format(self.base_url, path)

    def create_signature(self ):

        headers = {'typ': 'JWT', 'alg': 'HS256'}
        payload = {
            'type': 'OpenAPI',
            'sub': self.key,
            'nonce': int(time.time() * 1000000000)  # convert to nanoseconds
        }
        sig = jwt.encode(payload, self.secret, algorithm='HS256', headers=headers)
        return sig.decode("utf-8")

    def request(self, method, path, signed, **kwargs):

        data = kwargs.get('data', None)

        if signed:
            kwargs['headers'] = {
                'Authorization': 'Bearer {}'.format(self.create_signature())
            }

        uri = self.create_uri(path)

        if method == 'get' and data:
            kwargs['params'] = kwargs['data']
            del(kwargs['data'])

        if method == 'post' and data:
            kwargs['json'] = kwargs['data']
            del(kwargs['data'])

        response = getattr(self.session, method)(uri, **kwargs)
        if str(response.status_code).startswith('2'):
            return response.json()
        return None

    def norm_symbol(self,this_symbol):
        this_symbol = str(this_symbol).lower()
        if this_symbol.find('-') == -1:
            l = len(this_symbol)
            if this_symbol.endswith('btc') or this_symbol.endswith('eth'):
                this_symbol = this_symbol[0:l-3] + "-" + this_symbol[-3:]
            elif this_symbol.endswith('usdt'):
                this_symbol = this_symbol[0:l - 4] + "-" + this_symbol[-4:]
        return this_symbol.upper()

    def _get(self, path, signed=False, **kwargs):
        return self.request('get', path, signed, **kwargs)

    def _post(self, path, signed=False, **kwargs):
        return self.request('post', path, signed, **kwargs)

    def get_market_ticker(self, this_symbol):
        """get market ticker"""
        this_symbol = self.norm_symbol(this_symbol)
        info = self._get('markets/{}/ticker'.format(this_symbol))
        if info is None:
            # print("err1")
            return None
        elif 'data' in info:
            item_info = info['data']
            ticker = Ticker()
            ticker.symbol = this_symbol
            ticker.last = float(item_info['close'])
            return ticker
        else:
            # print("err2")
            return None
        return None

    def get_balance(self):
        """get user balance"""
        json = self._get('viewer/accounts', True)

        if json == None:
            return None
        result = {}
        if 'data' not in json:
            return None
        json = json['data']
        if len(json) == 0:
            return None
        for b in json:
            balance = Balance()
            balance.available = float(b['balance'])
            balance.currency = b['asset_id'].lower()
            balance.frozen = float(b['locked_balance'])
            balance.balance = float(balance.available + balance.frozen)
            #print(balance)
            result[balance.currency] = balance
        return result

    def list_orders(self, this_symbol,state):
        this_symbol = self.norm_symbol(this_symbol)
        data = {
            'market_id': this_symbol
        }
        data['state'] = state
        json = self._get('viewer/orders', True, data=data)
        if json == None:
            return None
        order_list = []
        json = json['data']
        if json == None:
            return None
        json = json['edges']
        if json == None:
            return None
        if len(json) == 0:
            return None
        for t in json:
            t = t['node']
            state = t['state']
            if state != state:
                continue
            order = Order()
            order.symbol = this_symbol
            order.id = t['id']
            order.price = float(t['price'])
            order.amount = float(t['amount'])
            order.created_at = int(time.mktime(time.strptime(t['updated_at'], '%Y-%m-%dT%H:%M:%SZ')))
            if t['side'] == 'BID':
                order.side = Side.buy
            else:
                order.side = Side.sell
            order.state = State.filled
            order_list.append(order)
            #print(order)
        return order_list

    def list_history_orders(self, this_symbol):
        return self.list_orders(this_symbol, 'FILLED')

    def list_pending_orders(self, this_symbol):
        """get orders"""
        return self.list_orders(this_symbol,'PENDING')

    def buy(self,symbol, price, amount):
        """buy someting"""
        symbol = self.norm_symbol(symbol)
        data = {
            'market_id': symbol,
            'side': 'BID',
            'price': price,
            'amount': amount
        }
        result = self._post('viewer/orders', True, data=data)
        if result == None:
            return None
        if 'data' not in result:
            return None
        return result['data']['id']

    def sell(self, symbol, price, amount):
        """buy someting"""
        symbol = self.norm_symbol(symbol)
        data = {
            'market_id': symbol,
            'side': 'ASK',
            'price': price,
            'amount': amount
        }
        result = self._post('viewer/orders', True, data=data)
        if result == None:
            return None
        if 'data' not in result:
            return None
        return result['data']['id']

    def cancel_order(self,order_id):
        """cancel specfic order"""
        return self._post('viewer/orders/{}/cancel'.format(order_id), True)

# 守护进程
if __name__ == '__main__':

    t = Api()
    print(t.get_market_ticker('ethusdt'))
    print(t.get_balance())
    #print(t.sell('ethusdt',460,0.05))
    #print(t.list_pending_orders('ethusdt'))
    print(t.list_history_orders('ethusdt'))

    print(t.cancel_order('66547114'))