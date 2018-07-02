import hmac
import hashlib
import requests
import sys
import time
import base64
import json
from collections import OrderedDict
from bitz_config import Ath
from Data import *
from urllib import *
import urllib
import pycurl
from io import StringIO

class Api():
    def __init__(self,base_url = 'https://api.bit-z.com/api_v1'):
        self.base_url = base_url
        self.pwd = Ath['pwd']
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
                r_url=r_url
            r = requests.request(method, r_url, params=payload)
            r.raise_for_status()
        except requests.exceptions.HTTPError as err:
            print(err)
        if r.status_code == 200:
            return r.json()

    def get_signed(self, sig_str):
        """signed params use sha512"""
        mysecret = (sig_str+self.secret).encode()
        m = hashlib.md5()
        m.update(mysecret)
        return m.hexdigest()


    def signed_request(self, method, api_url, **payload):
        """request a signed url"""

        timestamp = str(int(time.time()))
        param=''
        payload['api_key']=self.key
        payload['timestamp']=timestamp
        payload['nonce'] = timestamp[-6:]
        if payload:
            sort_pay = sorted(payload.items())
            #sort_pay.sort()
            for k in sort_pay:
                param += '&' + str(k[0]) + '=' + str(k[1])
            param = param.lstrip('&')

        sig_str = param

        signature = self.get_signed(sig_str)

        full_url = self.base_url + api_url

        r = {}
        payload['sign']=signature

        headerdata = {"Content-type": "application/json"}

        try:
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
                return self.postData(full_url, payload)
        except requests.exceptions.HTTPError as err:
            # print(err)
            print(r.text)
        finally:
            pass

        if r.status_code == 200:
            return r.json()

    def postData(curl, url, data):
        crl = pycurl.Curl()
        crl.setopt(pycurl.CONNECTTIMEOUT, 5)
        crl.setopt(pycurl.TIMEOUT, 5)
        crl.setopt(pycurl.HEADER, True)
        crl.setopt(crl.POST,True)
        crl.fp = StringIO()
        crl.setopt(crl.POSTFIELDS, urllib.parse.urlencode(data))
        crl.setopt(pycurl.URL, url)
        crl.setopt(pycurl.WRITEFUNCTION, crl.fp.write)
        crl.setopt(pycurl.FOLLOWLOCATION, 1)  # 参数有1、2
        crl.perform()
        print(crl.fp.getvalue())

    def get_tickers(self):
        return self.public_request('GET','/tickers')

    def get_market_ticker(self, this_symbol):
        result= self.public_request('GET', '/ticker',coin=this_symbol)
        if result == None:
            return None
        ticker = Ticker()
        if  'data' not in result:
            return  None
        if result['data']['last'] is None:
            return None
        ticker.last = float(result['data']['last'])
        ticker.symbol = this_symbol
        return  ticker

    def get_balance(self):
        """get user balance"""
        json = self.signed_request('POST', '/balances')
        if json == None:
            return None
        result={}
        if 'data' not in json:
            return None
        json=json['data']
        if json == None or len(json) ==0:
            return None
        for b in json:
            if b =='uid':
                continue
            b=str(b)
            if b.find('_') == -1:
                balance = Balance()
                balance.available = float(json[b+"_over"])
                balance.currency = b
                balance.frozen = float(json[b+"_lock"])
                balance.balance = float(json[b+"_over"])
                result[balance.currency] = balance
                #print(balance)
        return result

    def list_orders(self, **payload):
        """get orders"""
        this_symbol = payload['symbol']
        if payload['states'] == State.submitted:
            json = self.signed_request('POST','/openOrders',coin=this_symbol)
            if json == None:
                return None
            order_list = []
            if 'orders' not in json:
                return None
            json = json['orders']
            if 'result' not in json:
                return None
            if len(json) == 0:
                return None
            for t in json:
                order = Order()
                order.id = t['orderid']
                order.symbol = t['symbol']
                order.price = float(t['price'])
                order.amount = float(t['orderquantity'])
                order.created_at = int(t['createtime'])
                if t['type'].startwith('buy'):
                    order.side = Side.buy
                else:
                    order.side = Side.sell
                if t['orderstatus'] == 'filled':
                    order.state = State.filled
                elif t['orderstatus'] == 'unfilled':
                    order.state = State.submitted
                order_list.append(order)
                print(order)
            return order_list
        else:
            return None

    def create_order(self, **payload):
        """create order"""
        return self.signed_request('POST','/tradeAdd', **payload)

    def buy(self,symbol, price, amount):
        """buy someting"""
        return self.create_order(tradepwd=self.pwd,coin=symbol, type='in',  price=price, number=amount)

    def sell(self, symbol, price, amount):
        """buy someting"""
        return self.create_order(tradepwd=self.pwd,coin=symbol, type='out',  price=price, number=amount)

    def cancel_order(self,order_id):
        """cancel specfic order"""
        return self.signed_request('POST', '/tradeCancel',id=order_id)


# 守护进程
if __name__ == '__main__':
    api = Api()
    #print(api.get_market_ticker('eth_btc'))
    print(api.get_balance())
    #print(api.buy('btc_usdt',6385,0.01))
    #print(api.list_orders(symbol='btc_usdt',states=State.submitted))
    #print(api.cancel_order('2323'))