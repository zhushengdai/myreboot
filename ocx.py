import hmac
import hashlib
import requests
import sys
import time
import base64
import json
from collections import OrderedDict
from Data import *
from ocx_config import *
import pycurl
import urllib
from io import StringIO
from io import BytesIO
import certifi

class Api():
    def __init__(self,base_url = 'https://openapi.ocx.com/api/v2'):
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
            r = requests.request(method, r_url, params=payload)
            r.raise_for_status()
        except requests.exceptions.HTTPError as err:
            print(err)
        if r.status_code == 200:
            return r.json()

    def get_signed(self, sig_str):
        """signed params use sha512"""
        signature = hmac.new(bytes(self.secret,'utf-8'), sig_str, digestmod=hashlib.sha256).hexdigest()
        return signature


    def signed_request(self, method, api_url, **payload):
        """request a signed url"""

        timestamp = str(int(time.time() * 1000))
        param=''
        payload['access_key']=self.key
        payload['tonce']=timestamp
        if payload:
            sort_pay = sorted(payload.items())
            #sort_pay.sort()
            for k in sort_pay:
                param += '&' + str(k[0]) + '=' + str(k[1])
            param = param.lstrip('&')

        full_url = self.base_url + api_url

        sig_str = method + "|" + "/api/v2"+ api_url +"|"+ param

        signature = self.get_signed(bytes(sig_str, 'utf-8'))

        payload['signature'] = signature

        headerdata = {"Content-type": "application/json"}
        r = {}
        if method == 'GET':
            if param:
                full_url = full_url + '?' + param + "&signature=" + signature
            try:

                r = requests.request(method, full_url, data=json.dumps(payload), headers=headerdata, timeout=5)
                r.raise_for_status()
            except requests.exceptions.HTTPError as err:
                # print(err)
                print(r.text)
            finally:
                pass
        else:
            return self.postData(full_url,payload)

        if r.status_code == 200:
            return r.json()

    def postData(curl, url, data):
        crl = pycurl.Curl()
        crl.setopt(pycurl.CONNECTTIMEOUT, 5)
        crl.setopt(pycurl.TIMEOUT, 5)
        crl.setopt(pycurl.HEADER, True)
        crl.setopt(crl.POST,True)
        crl.setopt(pycurl.CAINFO,certifi.where())
        crl.fp = BytesIO()
        crl.setopt(crl.POSTFIELDS, urllib.parse.urlencode(data))
        crl.setopt(pycurl.URL, url)
        crl.setopt(pycurl.WRITEFUNCTION, crl.fp.write)
        crl.setopt(pycurl.FOLLOWLOCATION, 1)  # 参数有1、2
        crl.perform()
        return crl.fp.getvalue()

    def get_tickers(self):
        return self.public_request('GET','/tickers')

    def get_market_ticker(self, this_symbol):
        """get market ticker"""
        info = self.get_tickers()
        if info is None:
            # print("err1")
            return None
        elif 'data' in info and len(info['data']):
            for item in info['data']:
                if item['market_code'] == this_symbol:
                    item_info = item
                    label = this_symbol.upper()
                    ticker = Ticker()
                    ticker.symbol = this_symbol
                    ticker.last = float(item_info['last'])
                    #print(label, '最高价', item_info['high'], '最低价', item_info['low'],'最新价',item_info['last'])
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
        json = self.signed_request('GET', '/accounts')

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
            balance.currency = b['currency_code'].lower()
            balance.frozen = float(b['locked'])
            balance.balance = float(balance.available + balance.frozen)
            #print(balance)
            result[balance.currency] = balance
        return result

    def list_orders(self, **payload):
        """get orders"""
        this_symbol=payload['symbol']
        this_state=payload['states']
        json = self.signed_request('GET','/orders')
        if json == None:
            return None
        order_list = []
        json = json['data']
        if json == None:
            return None
        if len(json) == 0:
            return None
        for t in json:
            cur_sym = t['market_code']
            if cur_sym != this_symbol:
                continue
            cur_state = t['state']
            if cur_state != 'wait' and this_state ==State.submitted:
                continue
            if cur_state != 'done' and this_state == State.filled:
                continue
            order = Order()
            order.symbol = cur_sym
            order.id = t['id']
            order.avg_price = float(t['avg_price'])
            order.executed_volume = float(t['executed_volume'])
            order.price = float(t['price'])
            order.amount = float(t['volume'])
            order.created_at = int(time.mktime(time.strptime(t['created_at'], '%Y-%m-%dT%H:%M:%SZ')))
            if t['side'] == 'buy':
                order.side = Side.buy
            else:
                order.side = Side.sell
            if t['state'] == 'done':
                order.state = State.filled
            elif t['state'] == 'wait':
                order.state = State.submitted
            order_list.append(order)
            print(order)
        return order_list

    def create_order(self, **payload):
        """create order"""
        return self.signed_request('POST','/orders', **payload)

    def buy(self,symbol, price, amount):
        """buy someting"""
        result = self.create_order(market_code=symbol, side='buy',  price=price, volume=amount)
        if result == None:
            return None
        result=str(result)
        pos = result.find('{')
        result = result[pos:].rstrip('\'')
        try:
            result = json.loads(result)
            # print(result['data'])
            return result['data']['id']
        except:
            return None

    def sell(self, symbol, price, amount):
        """buy someting"""
        result = self.create_order(market_code=symbol, side='sell',  price=price, volume=amount)
        if result == None:
            return None
        result = str(result)
        pos = result.find('{')
        result = result[pos:].rstrip('\'')
        try:
            result = json.loads(result)
            # print(result['data'])
            return result['data']['id']
        except:
            return None

    def get_order(self,order_id):
        """get specfic order"""
        return self.signed_request('GET', '/orders/{order_id}'.format(order_id=order_id))

    def cancel_order(self,order_id):
        """cancel specfic order"""
        return self.signed_request('POST', '/orders/{order_id}/cancel'.format(order_id=order_id),id=order_id)

    def clear_order(self):
        return self.signed_request('POST', '/orders/clear')

# 守护进程
if __name__ == '__main__':

    t = Api()
    #print(t.get_market_ticker('btcusdt'))
    #print(t.get_balance())
    #print(t.get_market_depth('btcusdt'))
    #print(t.buy('ethusdt',453.3,0.1))
    print(t.list_orders(symbol='ethusdt',states=State.submitted))
    print(t.list_orders(symbol='ethusdt', states=State.filled))
    print(t.cancel_order('284599260'))