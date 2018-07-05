import hmac
import hashlib
import requests
import sys
import time
import base64
import json
from collections import OrderedDict
from Data import *
from coinpark_config import *
import pycurl
import urllib
from io import StringIO
from io import BytesIO
import certifi

class Api():
    def __init__(self,base_url = 'https://api.coinpark.cc/v1/'):
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

    def post_order(self,url, cmds):
        s_cmds = json.dumps(cmds)
        sign = self.getSign(s_cmds)
        timestamp = int(time.time())
        if cmds[0]['cmd'].endswith('trade') or cmds[0]['cmd'].endswith('cancelTrade'):
            r = requests.post(url, data={'index':timestamp,'cmds': s_cmds, 'apikey': self.key, 'sign': sign})
        else:
            r = requests.post(url, data={'cmds': s_cmds, 'apikey': self.key, 'sign': sign})
        return r

    def signed_request(self, method, api_url, cmd_url ,**payload):
        """request a signed url"""

        param=''

        if payload:
            sort_pay = sorted(payload.items())
            #sort_pay.sort()
            for k in sort_pay:
                param += '&' + str(k[0]) + '=' + str(k[1])
            param = param.lstrip('&')

        full_url = self.base_url + api_url

        cmds = []
        cmds_l = {}
        cmds_l['cmd'] = cmd_url
        cmds_l['body'] = payload
        cmds.append(cmds_l)

        r = {}
        if method == 'GET':
            pass
        else:
            r = self.post_order(full_url,cmds)
            r.raise_for_status()

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
        return this_symbol.upper()

    def get_tickers(self):
        json = self.public_request('GET','mdata' ,cmd='marketAll')
        if json==None:
            return None
        if 'result' not in json:
            return None
        json = json['result']
        result={}
        if len(json) == 0:
            return None
        for info in json:
            ticker = Ticker()
            ticker.symbol = info['coin_symbol'] + info['currency_symbol']
            ticker.symbol = ticker.symbol.lower()
            ticker.last = float(info['last'])
            result[ticker.symbol] = ticker
            #print(ticker)
        return result

    def get_market_ticker(self, this_symbol):
        """get market ticker"""
        this_symbol = self.norm_symbol(this_symbol)
        info = self.public_request('GET','mdata',cmd='market' ,pair=this_symbol)
        if info is None:
            # print("err1")
            return None
        elif 'result' in info and len(info['result']):
            item_info = info['result']
            ticker = Ticker()
            ticker.symbol = this_symbol
            ticker.last = float(item_info['last'])
            return ticker
        else:
            # print("err2")
            return None
        return None

    def get_markets(self):
        """get all currencies"""
        return self.public_request('GET', '/markets')['data']

    def get_market_depth(self, symbol):
        """get market depth"""
        return self.public_request('GET', '/depth',market_code=symbol)

    def get_balance(self):
        """get user balance"""
        json = self.signed_request('POST','transfer','transfer/assets',select=-1)

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
            balance.available = float(b['balance'])
            balance.currency = b['coin_symbol'].lower()
            balance.frozen = float(b['freeze'])
            balance.balance = float(balance.available + balance.frozen)
            #print(balance)
            result[balance.currency] = balance
        return result

    def list_history_orders(self,this_symbol):
        """get orders"""
        if this_symbol is None:
            json = self.signed_request('POST', 'orderpending', 'orderpending/orderHistoryList', page=1, size=20)
        else:
            this_symbol = self.norm_symbol(this_symbol)
            json = self.signed_request('POST','orderpending','orderpending/orderHistoryList',page=1,size=20,pair=this_symbol)
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
            json = self.signed_request('POST', 'orderpending', 'orderpending/orderPendingList', page=1, size=20)
        else:
            this_symbol = self.norm_symbol(this_symbol)
            json = self.signed_request('POST','orderpending','orderpending/orderPendingList',page=1,size=20,pair=this_symbol)
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
        return self.signed_request('POST','orderpending','orderpending/trade', **payload)

    def buy(self,symbol, price, amount):
        """buy someting"""
        symbol=self.norm_symbol(symbol)
        result = self.create_order(pair=symbol,account_type ='0' ,order_type='2', order_side='1',  price=price, amount=amount)
        if result == None:
            return None
        try:
            return result['result'][0]['result']
        except:
            return None


    def sell(self, symbol, price, amount):
        """buy someting"""
        symbol=self.norm_symbol(symbol)
        result = self.create_order(pair=symbol, account_type='0', order_type='2', order_side='2', price=price,
                                   amount=amount)
        if result == None:
            return None
        try:
            return result['result'][0]['result']
        except:
            return None


    def cancel_order(self,order_id):
        """cancel specfic order"""
        return self.signed_request('POST', 'orderpending','orderpending/cancelTrade',orders_id=order_id)


# 守护进程
if __name__ == '__main__':

    t = Api()
    #print(t.get_market_ticker('ethusdt'))
    #print(t.get_balance())
    print(t.sell('ethusdt',473,0.1))
    #print(t.list_pending_orders('ethusdt'))

    print(t.get_tickers())
    #print(t.cancel_order('12823547'))