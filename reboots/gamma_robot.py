# coding=utf-8

import threading
import time
import os

from Data import *

#plat='fc'
#plat='manbi'
#plat='bitz'
#plat='ocx'
plat = 'coinpark'
#plat = 'bigone'
if plat=='fc':
    from fcoin import *
    from fc_config import *
elif plat=='manbi':
    from manbi import *
    from manbi_config import *
elif plat == 'bitz':
    from bitz import *
    from bitz_config import *
elif plat == 'ocx':
    from ocx import *
    from ocx_config import *
elif plat == 'coinpark':
    from coinpark import *
    from coinpark_config import *
elif plat == 'bigone':
    from bigone import *
    from bigone_config import *

# 金额
amount = Gamma_Config['amount']

# 交易对
coin = Gamma_Config['symbol']
#
logdir = Log['log_dir']

soft_point = float(Gamma_Config['soft_point'])

cancel_time = float(Gamma_Config['cancel_time'])

account = Ath['account']

fee = Gamma_Config['fee']

ethusdt=coin+"usdt"
ethbtc=coin + "btc"
btcusdt="btcusdt"

# 初始化
api = Api()

wait_orders_cancer_time={}

nowTime = lambda: int(round(time.time()))
timestamp_path = nowTime()
date=time.strftime("%Y_%m_%d", time.localtime(timestamp_path ))
dir = logdir + plat + "_" + account+ "_" + "tri_" + coin +'_' + date
if not os.path.exists(dir):
    os.makedirs(dir)
curtime=time.strftime("%H_%M", time.localtime(timestamp_path ))
order_path=dir+"/"+curtime
print('订单文件：',order_path)
order_file=open(order_path,'w')
order_dict={}
init_state=True
init_usdt=0
fee_cost=0
left_usdt=0
loss_usdt=0
start_time = nowTime()

def gettime():
    timestamp = nowTime()
    return  account + ","+ time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp ))

# 获取交易对的筹码类型
def get_symbol_type(this_symbol):
    type=''
    result=[]
    base_coin=''
    this_symbol=this_symbol.replace('_','')
    if this_symbol.endswith('usdt'):
        base_coin='usdt'
        type=this_symbol[:-4]
    elif this_symbol.endswith('btc'):
        base_coin='btc'
        type=this_symbol[:-3]
    elif this_symbol.endswith('eth'):
        base_coin='eth'
        type=this_symbol[:-3]
    result.append(base_coin)
    result.append(type)

    return result

# 取小数，不四舍五入
def get_float(value, length):
    if type(value) is not float:
        value = str(value)
    value=str(value)
    flag = '.'
    point = value.find(flag)
    length = int(length) + point
    value = value[0:point] + value[point:length + 1]

    return float(value)

def soft_price(value,soft):
    soft_value = value * soft
    if type(value) is not float:
        value = str(value)
    flag = '.'
    point = value.find(flag)
    length = len(value) - point - 1
    return get_float(soft_value,length)

def do_one_action():

    balance_info = api.get_balance()
    eth = coin
    usdt="usdt"
    btc="btc"
    if balance_info is None:
        print(gettime(), "查询账户失败 ")
        return
    else:
        print(gettime(),balance_info[coin])
        print(gettime(),balance_info[usdt])
        print(gettime(), balance_info[btc])
        eth_avail_amount = balance_info[eth].available
        eth_forzen_amount = balance_info[eth].frozen
        ustc_avail_amount = balance_info[usdt].available
        ustc_forzen_amount = balance_info[usdt].frozen
        btc_avail_amount = balance_info[btc].available
        btc_forzen_amount = balance_info[btc].frozen

    ticker_list = api.get_tickers()
    if ticker_list is None:
        print(gettime(),'查询行情失败:')
        return

    ethusdt_price = ticker_list[ethusdt].last
    btcusdt_price = ticker_list[btcusdt].last
    ethbtc_price = ticker_list[ethbtc].last

    print(gettime(),ethusdt,'当前成交价',ethusdt_price)
    print(gettime(), btcusdt, '当前成交价', btcusdt_price)
    print(gettime(), ethbtc, '当前成交价', ethbtc_price)

    global init_state
    global init_usdt
    global fee_cost
    global loss_usdt
    global left_usdt
    global tmp_filled_order_split

    if init_state:
        init_state=False
        init_usdt = ustc_avail_amount + ustc_forzen_amount +  (eth_avail_amount + eth_forzen_amount )  * ethusdt_price  + (btc_avail_amount + btc_forzen_amount) * btcusdt_price
        order_file.writelines(gettime()+'\t'+str(init_usdt)+"\t"+str(ustc_avail_amount+ustc_forzen_amount)+"\t"+str(eth_avail_amount + eth_forzen_amount)+"\t"+str(ethusdt_price)+str(btc_avail_amount + btc_forzen_amount)+"\t"+str(btcusdt_price)+"\n")
        order_file.writelines("")
        order_file.flush()

    sub_order_list = api.list_pending_orders(None)
    now_timestamp = int( nowTime() )

    if sub_order_list is None:
        pass
    buy_order_num=0
    sell_order_num=0

    if sub_order_list and len(sub_order_list):
        for order in sub_order_list:
            #print(gettime(),order)
            this_states = order.state
            order_time = order.created_at
            if order.side == 'buy':
                buy_order_num = buy_order_num + 1
            else:
                sell_order_num = sell_order_num + 1
            order_id = order.id
            if order_id not in wait_orders_cancer_time or now_timestamp - wait_orders_cancer_time[order_id] > cancel_time:
                print(gettime(),'开始取消订单',order)
                wait_orders_cancer_time[order_id] = now_timestamp
                cancel_order_action(order.id)

    eth_avail_num = eth_avail_amount / amount
    eth_forzen_num = eth_forzen_amount / amount

    ustc_avail_num = ustc_avail_amount / (ethusdt_price * amount )
    ustc_forzen_num = ustc_forzen_amount / (ethusdt_price * amount )

    btc_avail_num = btc_avail_amount / (ethbtc_price * amount)
    btc_forzen_num = btc_forzen_amount / (ethbtc_price * amount)

    avi_num =  (eth_avail_num + ustc_avail_num + btc_avail_num + eth_forzen_num + ustc_forzen_num + btc_forzen_num) /3
    max_avail_num = min(ustc_avail_num,eth_avail_num,btc_avail_num)

    if eth_avail_num < 1 :
        n1 = ustc_avail_num - avi_num
        if n1 > amount / 3  :
            buy_action(ethusdt,ethusdt_price, n1 * amount)
        n2 = btc_avail_num - avi_num
        if n2 > amount / 3 :
            buy_action(ethbtc,ethbtc_price , n2 * amount)

    if ustc_avail_num <1 :
        n1 = eth_avail_num - avi_num
        if n1 > amount / 3:
            sell_action(ethusdt , ethusdt_price , n1 * amount)
        n2 = btc_avail_num - avi_num
        if n2 > amount / 3:
            sell_action(btcusdt,btcusdt_price , n2 * ethbtc_price * amount)

    if btc_avail_num < 1:
        n1 = eth_avail_num - avi_num
        if n1 > amount / 3:
            sell_action(ethbtc, ethbtc_price , n1 * amount)
        n1 = ustc_avail_num - avi_num
        if n1 > amount / 3:
            buy_action(btcusdt, btcusdt_price, n1 * ethbtc_price * amount)

    if max_avail_num > amount:
        cur_amount = amount
    else:
        cur_amount = max_avail_num * 0.8
    if cur_amount > amount * 0.5:
        if ethusdt_price > btcusdt_price * ethbtc_price :
            buy_action(btcusdt,btcusdt_price ,cur_amount)
            buy_action(ethbtc, ethbtc_price ,cur_amount)
            sell_action(ethusdt,ethusdt_price ,cur_amount)
        else:
            buy_action(ethusdt, ethusdt_price, cur_amount)
            sell_action(ethbtc,ethbtc_price,cur_amount)
            sell_action(btcusdt,btcusdt_price,cur_amount)

    sub_order_list = api.list_history_orders(None)

    if sub_order_list is None:
        return

    if sub_order_list and len(sub_order_list):
        sort_list = sorted(sub_order_list,key=lambda order_t:order_t.created_at,reverse=False)
        for order in sort_list:
            order_id = order.id
            if order_id not in order_dict:
                order_dict[order_id] = 1
                if order_id not in wait_orders_cancer_time:
                    continue
                order_time = wait_orders_cancer_time[order_id]
                if float(order_time) < start_time:
                    continue
                order_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(order_time))
                order_fee = order.fee
                base_cur = 'usdt'
                if order.side == Side.buy:
                    base_cur = order.currency
                else:
                    base_cur = order.coin
                if base_cur == 'eth':
                    order_fee = order_fee * ethusdt_price
                elif base_cur == 'btc':
                    order_fee = order_fee * btcusdt_price

                fee_cost = float(fee_cost) + float(order_fee)
                left_usdt = ustc_avail_amount + ustc_forzen_amount + (eth_forzen_amount + eth_avail_amount) * ethusdt_price + (btc_avail_amount + btc_forzen_amount) * btcusdt_price
                loss_usdt = init_usdt - left_usdt - fee_cost
                order_file.writelines(str(order_time) + '\t' + str(left_usdt) + '\t' + str(fee_cost) + '\t' + str(loss_usdt) + "\t" + order + "\n")
                order_file.flush()

# 买操作
def buy_action(this_symbol,price, this_amount):
    price = price + soft_price(price,soft_point)
    buy_result = api.buy(this_symbol,price, this_amount)
    if buy_result is None:
        print(gettime(),"挂 买单 失败",this_symbol,price,this_amount)
        return True
    buy_order_id = buy_result
    if buy_order_id is None:
        print(gettime(), "挂 买单 失败")
    if buy_order_id:
        now_timestamp = int(nowTime() )
        wait_orders_cancer_time[buy_order_id] = now_timestamp
        print(gettime(), '成功市价买入', '订单ID', buy_order_id,this_symbol,'价格',price,'数量',this_amount)

    return buy_order_id


# 卖操作
def sell_action(this_symbol, price,this_amount):
    price = price - soft_price(price, soft_point)
    this_amount = get_float(this_amount, 2)
    sell_result = api.sell(this_symbol,price, this_amount)

    if sell_result is None:
        print(gettime(),"挂 卖单失败",this_symbol,price,this_amount)
        pass
    else:
        sell_order_id = sell_result
        if sell_order_id is None:
            print(gettime(), "挂 卖单失败")
        if sell_order_id:
            now_timestamp = int(nowTime())
            wait_orders_cancer_time[sell_order_id] = now_timestamp
            print( gettime(),'成功市价卖出',  '订单ID', sell_order_id,this_symbol,'价格',price,'数量',this_amount)

        return sell_order_id

# 撤销订单
def cancel_order_action(this_order_id):
    api.cancel_order(this_order_id)

def robot():
    #try:
        do_one_action()
    #except:
    #    print(gettime(),"出现异常")

# 定时器
def timer():
    while True:
        robot()
        time.sleep(2)


# 守护进程
if __name__ == '__main__':

    print(gettime())
    t = threading.Thread(target=timer())
    t.start()
    t.join()




