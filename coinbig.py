import hmac
import hashlib
import requests
import sys
import time
import base64
import json
from collections import OrderedDict
from coinbig_config import Ath
from manbi_config import Status_info
from Data import *
import urllib
import copy
import operator

class Api():
    def __init__(self,base_url = 'http://www.3k2k.com:81/api/publics/v1'):
        self.base_url = base_url
        self.account = Ath['account']
        self.key = Ath['key']
        self.secret = Ath['secret']

    def public_request(self, method, api_url, **payload):
        """request public url"""
        r_url = self.base_url + api_url
        try:
            param = ''
            if payload:
                sort_pay = sorted(payload.items())
                # sort_pay.sort()
                for k in sort_pay:
                    param += '&' + str(k[0]) + '=' + str(k[1])
                param = param.lstrip('&')
                r_url=r_url + "?" + param
            if method == 'GET':
                r = requests.get(r_url, timeout=5)
            else:
                r = requests.post(r_url, data=json.dumps(payload),  timeout=5)
            r.raise_for_status()
        except requests.exceptions.HTTPError as err:
            print(err)
        if r.status_code == 200:
            return r.json()

    def get_signed(self, params):
        """signed params use sha512"""
        _params = copy.copy(params)
        sort_params = sorted(_params.items(), key=operator.itemgetter(0))
        sort_params = dict(sort_params)
        sort_params['secret_key'] = self.secret
        string = urllib.parse.urlencode(sort_params)
        _sign = hashlib.md5(bytes(string.encode('utf-8'))).hexdigest().upper()
        params['sign'] = _sign
        return params

    def create_uri(self, path):
        return '{}/{}'.format(self.base_url, path)

    def signed_request(self, method, api_url, **payload):
        """request a signed url"""

        payload['apikey'] = self.key
        full_url = self.create_uri(api_url)
        payload = self.get_signed(payload)
        r = {}

        try:
            r = requests.post(full_url, data=json.dumps(payload),  timeout=5)
            r.raise_for_status()
        except requests.exceptions.HTTPError as err:
            # print(err)
            print(r.text)
        finally:
            pass

        if r.status_code == 200:
            return r.json()

    def norm_symbol(self,this_symbol):
        this_symbol = str(this_symbol).lower()
        if this_symbol.find('_') == -1:
            l = len(this_symbol)
            if this_symbol.endswith('btc') or this_symbol.endswith('eth'):
                this_symbol = this_symbol[0:l-3] + "_" + this_symbol[-3:]
            elif this_symbol.endswith('usdt'):
                this_symbol = this_symbol[0:l - 4] + "_" + this_symbol[-4:]
        return this_symbol

    def get_market_ticker(self, this_symbol):
        """get market ticker"""
        this_symbol = self.norm_symbol(this_symbol)
        info = self.public_request('GET','ticker' ,symbol=this_symbol)
        if info is None:
            # print("err1")
            return None
        elif 'result' in info and len(info['result']):
            item_info = info['result']
            ticker = Ticker()
            ticker.symbol = this_symbol
            ticker.last = float(item_info['last'])
            ticker.buy = float(item_info['buy'])
            ticker.sell = float(item_info['sell'])
            return ticker
        else:
            # print("err2")
            return None
        return None

    def get_balance(self):
        result=[]
        result1 = self.get_balance_symbol('btc')
        if result1 == None:
            return None
        result2 = self.get_balance_symbol('usdt')
        if result2 == None:
            return None
        result3 = self.get_balance_symbol('eth')
        if result3 == None:
            return None
        result.append(result1)
        result.append(result2)
        result.append(result3)
        return result

    def get_balance_symbol(self,coin):
        """get user balance"""
        json = self.signed_request('POST','userinfoBySymbol',shortName=coin)

        if json == None:
            return None
        result = {}
        if 'result' not in json:
            return None
        json = json['result']
        json=json[0]
        if 'result' not in json:
            return None
        json = json['result']
        if 'assets_list' not in json:
            return None
        json = json['assets_list']
        if len(json) == 0:
            return None
        for b in json:
            balance = Balance()
            balance.available = float(b['free'])
            balance.currency = coin.lower()
            balance.frozen = float(b['freezed'])
            balance.balance = float(balance.available + balance.frozen)
            #print(balance)
            result[balance.currency] = balance
        return result

    def list_history_orders(self,this_symbol):
        """get orders"""
        result1 = self.list_orders(this_symbol, 3)
        result2 = self.list_orders(this_symbol, 5)
        result = []
        if result1 != None:
            result.append(result1)
        if result2 != None:
            result.append(result2)
        if len(result) == 0:
            return None
        return result

    def list_pending_orders(self, this_symbol):
        result1=self.list_orders(this_symbol,1)
        result2=self.list_orders(this_symbol,2)
        result=[]
        if result1 !=None:
            result.append(result1)
        if result2 !=None:
            result.append(result2)
        if len(result) == 0:
            return None
        return result

    def list_orders(self, this_symbol,type):
        """get orders"""
        this_symbol = self.norm_symbol(this_symbol)
        json = self.signed_request('POST','orderpending',symbol=this_symbol,size=50,type=type)
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
            order.symbol = this_symbol
            order.id = t['order_id']
            order.price = float(t['price'])
            order.amount = float(t['amount'])
            order.executed_volume = float(t['deal_amount'])
            order.avg_price=float(t['avg_price'])
            order.created_at = (int(t['create_date']) / 1000 )
            order.fee = 0.001 * order.executed_volume
            if t['type'] == 'buy_market':
                order.side = Side.buy
            else:
                order.side = Side.sell
            order.state = State.submitted
            order_list.append(order)
            #print(order)
        return order_list

    def create_order(self, **payload):
        """create order"""
        return self.signed_request('POST','trade', **payload)

    def buy(self,symbol, price, amount):
        """buy someting"""
        symbol=self.norm_symbol(symbol)
        result = self.create_order(symbol=symbol ,type='buy', price=price, amount=amount)
        if result == None:
            return None
        try:
            return result['result'][0]['result']
        except:
            return None


    def sell(self, symbol, price, amount):
        """buy someting"""
        symbol=self.norm_symbol(symbol)
        result = self.create_order(symbol=symbol ,type='sell', price=price, amount=amount)
        if result == None:
            return None
        try:
            return result['result'][0]['result']
        except:
            return None


    def cancel_order(self,order_id):
        """cancel specfic order"""
        return self.signed_request('GET', 'cancel_order',order_id=order_id)

# 守护进程
if __name__ == '__main__':
    api = Api()
    #print(api.get_market_ticker('conibtc'))
    #print(api.get_balance())
    #print(api.list_orders(symbol='btcusdt',states=State.filled))

