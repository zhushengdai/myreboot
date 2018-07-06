import hmac
import hashlib
import requests
import sys
import time
import base64
import json
from collections import OrderedDict
from Data import *
from allcoin_config import *
import pycurl
import urllib
from io import StringIO
from io import BytesIO
import certifi
import copy
import operator

class Api():
    def __init__(self,base_url = 'https://www.allcoin.ca'):
        self.base_url = base_url
        self.account = Ath['account']
        self.key = Ath['key']
        self.secret = Ath['secret']

    def create_uri(self, path):
        return '{}/{}'.format(self.base_url, path)

    def public_request(self, method, api_url, **payload):
        """request public url"""
        r_url =self.create_uri(api_url)
        try:
            param = ''
            if payload:
                sort_pay = sorted(payload.items())
                # sort_pay.sort()
                for k in sort_pay:
                    param += '&' + str(k[0]) + '=' + str(k[1])
                param = param.lstrip('&')
                r_url=r_url+"?"+param
            r = requests.request(method, r_url)
            r.raise_for_status()
        except requests.exceptions.HTTPError as err:
            print(err)
        if r.status_code == 200:
            return r.json()

    def getSign(self,data):
        result = hmac.new(self.secret.encode("utf-8"), data.encode("utf-8"), hashlib.md5).hexdigest()
        return result

    def get_signed(self, params):
        """signed params use sha512"""
        _params = copy.copy(params)
        sort_params = sorted(_params.items(), key=operator.itemgetter(0))
        sort_params = dict(sort_params)
        sort_params['secret_key'] = self.secret
        string = urllib.parse.urlencode(sort_params)
        _sign = hashlib.md5(bytes(string.encode('utf-8'))).hexdigest()
        params['sign'] = _sign
        return params

    def signed_request(self, method, api_url, **payload):
        """request a signed url"""

        payload['api_key'] = self.key
        full_url = self.create_uri(api_url)
        payload = self.get_signed(payload)
        r = {}

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.137 Safari/537.36 LBBROWSER'
            }
            r = requests.post(full_url, data=payload, headers=headers, timeout=5)
            r.raise_for_status()
        except requests.exceptions.HTTPError as err:
            # print(err)
            print(r.text)
        finally:
            pass

        if r.status_code == 200:
            print(str(r.json()))
            return r.json()

    def norm_symbol(self,this_symbol):
        this_symbol = str(this_symbol).lower()
        if this_symbol.find('_') == -1:
            l = len(this_symbol)
            if this_symbol.endswith('btc') or this_symbol.endswith('eth'):
                this_symbol = this_symbol[0:l-3] + "_" + this_symbol[-3:]
            elif this_symbol.endswith('usdt'):
                this_symbol = this_symbol[0:l - 4] + "_" + 'ckusd'
        return this_symbol.upper()

    def get_tickers(self):
        json = self.public_request('GET','Api_Market/getPriceList')
        if json==None:
            return None
        result={}
        if len(json) == 0:
            return None
        for base_coin in json:
            if base_coin == 'cnet' or base_coin == 'qtum':
                continue
            for info in json[base_coin]:
                ticker = Ticker()
                ticker.symbol = info['coin_from'] + base_coin
                if base_coin == 'ckusd':
                    ticker.symbol = info['coin_from'] + 'usdt'
                ticker.symbol = ticker.symbol.lower()
                ticker.last = float(info['current'])
                ticker.buy = float(info['buy'])
                ticker.sell = float(info['sale'])
                result[ticker.symbol] = ticker
                print(ticker)
        return result

    def get_balance(self):
        """get user balance"""
        json = self.signed_request('POST','Api_User/userBalance')

        if json == None:
            return None
        result = {}
        if 'data' not in json:
            return None
        json = json['data']
        if len(json) == 0:
            return None
        for b in json:
            b=str(b)
            point = b.find('_')
            if point == -1:
                continue
            coin = b[0:point].lower()
            if coin in result:
                continue
            balance = Balance()
            balance.currency = coin
            balance.frozen = float(json[coin+"_lock"])
            balance.available = float(json[coin + "_over"])
            balance.balance = float(balance.available + balance.frozen)
            print(balance)
            result[balance.currency] = balance
        return result

    def list_history_orders(self,this_symbol):
        """get orders"""
        if this_symbol is None:
            result1 = self.list_pending_orders('btcusdt')
            result2 = self.list_pending_orders('ethusdt')
            result3 = self.list_pending_orders('ethbtc')
            result = []
            if result1!=None:
                result.append(result1)
            if result2 != None:
                result.append(result2)
            if result3 != None:
                result.append(result3)
            if len(result) == 0:
                return None
            return result
        else:
            this_symbol = self.norm_symbol(this_symbol)
            json = self.signed_request('POST', 'Api_Order/orderList', symbol=this_symbol, type='open')
        if json == None:
            return None
        order_list = []
        json = json['result']
        if json == None:
            return None
        json = json[0]['result']['items']
        if json == None:
            return None
        if len(json) == 0:
            return None
        for t in json:
            state = t['status']
            if state == 3:
                continue
            order = Order()
            order.symbol = t['coin_symbol'] + t['currency_symbol']
            order.coin = t['coin_symbol']
            order.currency = t['currency_symbol']
            order.id = t['id']
            order.price = float(t['price'])
            order.amount = float(t['amount'])
            order.money = float(t['money'])
            order.fee = float(t['fee'])
            order.created_at = (int(t['createdAt']) / 1000 )
            if t['order_side'] == '1':
                order.side = Side.buy
            else:
                order.side = Side.sell
            order.state = State.filled

            order_list.append(order)
            #print(order)
        return order_list

    def list_pending_orders(self, this_symbol):
        """get orders"""
        if this_symbol is None:
            result1 = self.list_pending_orders('btcusdt')
            result2 = self.list_pending_orders('ethusdt')
            result3 = self.list_pending_orders('ethbtc')
            result = []
            if result1!=None:
                result.append(result1)
            if result2 != None:
                result.append(result2)
            if result3 != None:
                result.append(result3)
            if len(result) == 0:
                return None
            return result
        else:
            this_symbol = self.norm_symbol(this_symbol)
            json = self.signed_request('POST', 'Api_Order/tradeList', symbol=this_symbol, type='open')
        if json == None:
            return None
        order_list = []
        json = json['result']
        if json == None:
            return None
        json = json[0]['result']['items']
        if json == None:
            return None
        if len(json) == 0:
            return None
        for t in json:
            state = t['status']
            if state == 3:
                continue
            order = Order()
            order.symbol = t['coin_symbol'] + t['currency_symbol']
            order.id = t['id']
            order.price = float(t['price'])
            order.amount = float(t['amount'])
            order.created_at = (int(t['createdAt']) / 1000 )
            if t['order_side'] == '1':
                order.side = Side.buy
            else:
                order.side = Side.sell
            order.state = State.submitted
            order_list.append(order)
            #print(order)
        return order_list

    def create_order(self, **payload):
        """create order"""
        return self.signed_request('POST','Api_Order/coinTrust', **payload)

    def buy(self,symbol, price, amount):
        """buy someting"""
        symbol=self.norm_symbol(symbol)
        result = self.create_order(symbol=symbol,order_type='buy', price=price, number=amount)
        if result == None:
            return None
        try:
            return result['result'][0]['result']
        except:
            return None


    def sell(self, symbol, price, amount):
        """buy someting"""
        symbol=self.norm_symbol(symbol)
        result = self.create_order(symbol=symbol, order_type='sale', price=price, number=amount)
        if result == None:
            return None
        try:
            return result['result'][0]['result']
        except:
            return None


    def cancel_order(self,order_id):
        """cancel specfic order"""
        return self.signed_request('POST', 'Api_Order/cancel',order_id=order_id)


# 守护进程
if __name__ == '__main__':

    t = Api()
    #print(t.get_tickers())
    print(t.get_balance())
    #print(t.sell('ethusdt',473,0.1))
    #print(t.list_pending_orders('ethusdt'))

    #print(t.cancel_order('12823547'))