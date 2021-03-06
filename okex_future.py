import hmac
import hashlib
import requests
import sys
import time
import base64
import json
from collections import OrderedDict
from manbi_config import Ath
from manbi_config import Status_info
from Data import *

class Api():
    def __init__(self,base_url = 'https://www.okex.com/api/v1'):
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

    def get_signed(self, sig_str):
        """signed params use sha512"""
        mysecret = sig_str.upper().encode()
        m = hashlib.md5()
        m.update(mysecret)
        return m.hexdigest()


    def signed_request(self, method, api_url, **payload):
        """request a signed url"""

        timestamp = str(int(time.time() * 1000))
        param=''
        #del payload['secret']
        payload['apiid']=self.key
        payload['timestamp']=timestamp
        payload['account']=self.account
        payload['secret']=self.secret
        if payload:
            sort_pay = sorted(payload.items())
            #sort_pay.sort()
            for k in sort_pay:
                param += '&' + str(k[0]) + '=' + str(k[1])
            param = param.lstrip('&')

        sig_str = param

        signature = self.get_signed(sig_str)

        full_url = self.base_url + api_url

        header_dict = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; Trident/7.0; rv:11.0) like Gecko", "Content-Type": "application/json;charset=utf-8", "Connection": "keep-alive"}

        r = {}
        del payload['secret']
        payload['sign']=signature
        try:
            if method == 'GET':
                r = requests.get( full_url, timeout=5)
            else:
                r = requests.post(full_url, data=json.dumps(payload), headers=header_dict,  timeout=5)
                #r = requests.request(method, full_url,data=json.dumps(payload),  timeout=5)
            # r.raise_for_status()
        except requests.exceptions.HTTPError as err:
            # print(err)
            print(r.text)
        finally:
            pass

        if r.status_code == 200:
            return r.json()

    def get_tickers(self):
        return self.public_request('GET','/market/ticker',symbol='all')

    def get_market_ticker(self, this_symbol ,this_contract_type):
        result= self.public_request('GET', '/future_ticker.do',symbol=this_symbol,contract_type=this_contract_type)
        if result == None:
            return None
        ticker = Ticker()
        if  'ticker' not in result:
            return  None
        ticker.last = float(result['ticker']['last'])
        ticker.symbol = this_symbol
        return  ticker

    def get_kline(self,this_symbol,this_type,this_contract_type,this_size):
        result = self.public_request('GET', '/future_kline.do', symbol=this_symbol,type = this_type, contract_type=this_contract_type,size=this_size,)

        if result == None:
            return None
        kline_list = []
        n = this_size
        for kl in result:
            kline = Kline()
            kline.time = int(kl[0])
            kline.open = float(kl[1])
            kline.high = float(kl[2])
            kline.low = float(kl[3])
            kline.close = float(kl[4])
            kline.num = n
            n=n-1
            kline_list.append(kline)
            print(kline)
        return kline_list

    def get_bollBands(self,kline_list,n):
        avi_list=[]
        size = len(kline_list)
        for i in size - n -1, size-1:
            avi_list.append(self.get_avi(kline_list,i,n))
        md = 0
        for i in size - n - 1 , size-1:
            tmp = kline_list[i].close - avi_list[i]
            md = md + tmp * tmp
        md = md / n
        md = md ** 0.5




    def get_avi(self,kline_list,k,n):
        sum=0
        for i in k-n+1,k+1:
            sum = sum + kline_list[i].close
        sum = sum / n
        return sum


    def get_balance(self):
        """get user balance"""
        json = self.signed_request('POST', '/trade/balance')

        if json == None:
            return None
        result = {}
        if 'balance' not in json:
            return None
        json = json['balance']
        if len(json) == 0:
            return None
        for b in json:
            balance = Balance()
            balance.available = float(b['available'])
            balance.currency = b['asset'].lower()
            balance.frozen = float(b['reserved'])
            balance.balance = float(b['total'])
            #print(balance)
            result[balance.currency] = balance
        return result

    def list_orders(self, **payload):
        """get orders"""
        this_symbol=payload['symbol']
        if payload['states']==State.submitted:
            json = self.signed_request('POST','/trade/order/open-orders',symbol=this_symbol)
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
    #print(api.get_market_ticker('btc_usd','this_week'))
    print(api.get_kline('btc_usd','1day','this_week',20))
    #print(api.get_balance())
    #print(api.list_orders(symbol='btcusdt',states=State.filled))

