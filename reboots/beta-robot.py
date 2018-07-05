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

# 买卖金额
amount = Config['buy_amount']

# 交易对
symbol = Config['symbol']
#
logdir = Log['log_dir']

soft_point = float(Config['soft_point'])

cancel_time = float(Config['cancel_time'])

account = Ath['account']

fee = Config['fee']

protect_price = float(Config['protect_price'])


# 初始化
api = Api()

wait_orders_cancer_time={}

nowTime = lambda: int(round(time.time()))
timestamp_path = nowTime()
date=time.strftime("%Y_%m_%d", time.localtime(timestamp_path ))
dir = logdir + plat + "_" + account+ "_" + symbol +'_' + date
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
filled_order_split=3
tmp_filled_order_split=0

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

def do_one_action(this_symbol):

    balance_info = api.get_balance()
    this_symbol_type = get_symbol_type(this_symbol)[1]
    base_coin=get_symbol_type(this_symbol)[0]
    if balance_info is None:
        print(gettime(), "查询账户失败 ")
        return
    else:
        print(gettime(),balance_info[base_coin])
        print(gettime(),balance_info[this_symbol_type])
        symbol_avail_amount = balance_info[this_symbol_type].available
        symbol_forzen_amount = balance_info[this_symbol_type].frozen
        ustc_avail_amount = balance_info[base_coin].available
        ustc_forzen_amount = balance_info[base_coin].frozen

    ticker = api.get_market_ticker(this_symbol)
    if ticker is None:
        print(gettime(),'查询行情失败:')
        return

    now_price = ticker.last
    print(gettime(),symbol,'当前成交价',now_price)

    if now_price < protect_price * 0.99 or now_price > protect_price * 1.01:
        print(gettime(),'现价过高 或者 过低 超过保护价范围',symbol,'当前成交价',now_price)
        return

    global init_state
    global init_usdt
    global fee_cost
    global loss_usdt
    global left_usdt
    global tmp_filled_order_split

    if init_state:
        init_state=False
        init_usdt = ustc_avail_amount + ustc_forzen_amount + now_price * symbol_avail_amount + now_price * symbol_forzen_amount
        order_file.writelines(gettime()+'\t'+str(init_usdt)+"\t"+str(ustc_avail_amount)+"\t"+str(symbol_avail_amount)+"\t"+str(symbol_forzen_amount)+"\t"+str(now_price)+"\n")
        order_file.writelines("")
        order_file.flush()

    sub_order_list = api.list_pending_orders(this_symbol)
    now_timestamp = int( nowTime() )

    if sub_order_list is None:
        pass
    buy_order_num=0
    sell_order_num=0

    if sub_order_list and len(sub_order_list):
        for order in sub_order_list:
            this_states = order.state
            if order.side == 'buy':
                buy_order_num = buy_order_num + 1
            else:
                sell_order_num = sell_order_num + 1
            order_id = order.id
            if order_id not in wait_orders_cancer_time :
                print(gettime(),'开始取消订单',order)
                wait_orders_cancer_time[order_id] = now_timestamp
                cancel_order_action(order.id)
            else:
                wait_order_time = wait_orders_cancer_time[order_id]
                if now_timestamp -  wait_order_time > cancel_time:
                    print(wait_order_time,now_timestamp,"xxx")
                    print(gettime(), '开始取消订单', order)
                    wait_orders_cancer_time[order_id] = now_timestamp
                    cancel_order_action(order.id)

    symbol_avail_num = symbol_avail_amount / amount
    symbol_forzen_num = symbol_forzen_amount / amount

    ustc_avail_num = ustc_avail_amount / (now_price * amount )
    ustc_forzen_num = ustc_forzen_amount / (now_price * amount )

    avi_num = (symbol_avail_num+symbol_forzen_num+ustc_avail_num+ustc_forzen_num) / 2
    max_avail_num = min(symbol_avail_num,ustc_avail_num)

    if symbol_avail_num < 1 :
        n1 = ustc_avail_num - avi_num
        if n1 > amount / 3  :
            buy_action(symbol,now_price, n1 * amount)

    if ustc_avail_num <1 :
        n1 = symbol_avail_num - avi_num
        if n1 > amount / 3:
            sell_action(symbol , now_price , n1 * amount)

    if max_avail_num > amount:
        cur_amount = amount
    else:
        cur_amount = max_avail_num * 0.8
    if cur_amount > amount * 0.5:
        buy_action(this_symbol,now_price  ,amount)
        sell_action(this_symbol, now_price , amount)

    sub_order_list = api.list_history_orders(None)

    if sub_order_list is None:
        return

    if sub_order_list and len(sub_order_list):
        sort_list = sorted(sub_order_list, key=lambda order_t: order_t.created_at, reverse=False)
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

                if order.side == Side.sell:
                    order_fee = order_fee * now_price

                fee_cost = float(fee_cost) + float(order_fee)
                left_usdt = ustc_avail_amount + ustc_forzen_amount + (symbol_forzen_amount + symbol_avail_amount) * now_price
                loss_usdt = init_usdt - left_usdt - fee_cost
                order_file.writelines(str(order_time) + '\t' + str(left_usdt) + '\t' + str(fee_cost) + '\t' + str(loss_usdt) + "\t" + order + "\n")
                order_file.flush()

# 买操作
def buy_action(this_symbol,price, this_amount):
    price = price + soft_price(price, soft_point)
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
    try:
        do_one_action(symbol)
    except:
        print(gettime(),"出现异常")

# 定时器
def timer():
    while True:
        robot()
        time.sleep(5)


# 守护进程
if __name__ == '__main__':

    print(gettime())
    t = threading.Thread(target=timer())
    t.start()
    t.join()




