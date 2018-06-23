# coding=utf-8

import threading
import time
import os

#plat='fc'
plat='manbi'
if plat=='fc':
    from fcoin3 import Api
    from fc_config import Ath
    from fc_config import Config
    from fc_config import Log
    from fc_config import Balance_info
    from fc_config import Order_info
elif plat=='manbi':
    from manbi import Api
    from manbi_config import Ath
    from manbi_config import Config
    from manbi_config import Log
    from manbi_config import Balance_info
    from manbi_config import Order_info



# 已成交
filled = 'filled'
# 已提交（未成交）
submitted = 'submitted'
#
part_filled='partial_filled'
# 买金额
buy_amount = Config['buy_amount']
# 卖金额
sell_amount = Config['sell_amount']
# 交易对
symbol = Config['symbol']
#
logdir = Log['log_dir']

soft_point = float(Config['soft_point'])

cancel_time = float(Config['cancel_time'])

# 初始化
api = Api()

# 授权
api_key = Ath['key']
api_secret = Ath['secret']
account = Ath['account']
api.auth(api_key, api_secret)

wait_orders_cancer_time={}

nowTime = lambda: int(round(time.time() * 1000))
timestamp_path = nowTime()
dir=time.strftime("%Y_%m_%d", time.localtime(timestamp_path / 1000))
dir = logdir + account+ "_" + symbol +'_' + dir
if not os.path.exists(dir):
    os.makedirs(dir)
curtime=time.strftime("%H_%M", time.localtime(timestamp_path / 1000))
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
    return  account + ","+ time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp / 1000))

# 获取交易对的筹码类型
def get_symbol_type(this_symbol):
    type=''
    result=[]
    base_coin=''
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

def do_one_action(this_symbol):

    balance_info = api.get_balance()
    this_symbol_type = get_symbol_type(this_symbol)[1]
    base_coin=get_symbol_type(this_symbol)[0]
    if balance_info is None:
        print(gettime(), "查询账户失败 ")
        return
    elif 'data' in balance_info and len(balance_info['data']):
        for item in balance_info['data']:
            if item[Balance_info['currency']] == this_symbol_type:
                balance = item
                label = this_symbol_type.upper()
                print(gettime(), label, '账户余额', balance[Balance_info['balance']], '可用', balance[Balance_info['available']], '冻结', balance[Balance_info['frozen']])
                symbol_avail_amount = float(balance[Balance_info['available']])
                symbol_forzen_amount = float(balance[Balance_info['frozen']])
            elif item[Balance_info['currency']] == base_coin:
                balance = item
                label = base_coin
                print(gettime(), label, '账户余额', balance[Balance_info['balance']], '可用', balance[Balance_info['available']], '冻结', balance[Balance_info['frozen']])
                ustc_avail_amount = float(balance[Balance_info['available']])
                ustc_forzen_amount = float(balance[Balance_info['frozen']])
    else:
        return

    now_price = get_ticker(this_symbol)
    if now_price is None:
        print(gettime(),'查询行情失败:')
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


    sub_order_list = api.list_orders(symbol=this_symbol,states=submitted)
    now_timestamp = nowTime()

    if sub_order_list is None:
        pass
    buy_order_num=0
    sell_order_num=0

    if sub_order_list and len(sub_order_list):
        for order in sub_order_list['data']:
            print(gettime(),'订单ID', order[Order_info['id']], '挂单价格', order[Order_info['price']], '挂单数量', order[Order_info['amount']], '方向', order[Order_info['side']])
            this_states = order[Order_info['state']]

            if this_states == submitted:
                order_time = order[Order_info['created_at']]
                if order[Order_info['side']] == 'buy':
                    buy_order_num = buy_order_num + 1
                if order[Order_info['side']] == 'sell':
                    sell_order_num = sell_order_num + 1
                order_time_sec = order_time
                if now_timestamp - order_time_sec > cancel_time * 1000:
                    order_id = order[Order_info['id']]
                    if order_id not in wait_orders_cancer_time or now_timestamp - wait_orders_cancer_time[order_id] > cancel_time * 1000:
                        print(gettime(),'订单ID', order[Order_info['id']], '挂单价格', order[Order_info['price']], '挂单数量', order[Order_info['amount']], '方向', order[Order_info['side']])
                        print(gettime(),'开始取消订单')
                        wait_orders_cancer_time[order_id] = now_timestamp
                        cancel_order_action(order[Order_info['id']])

        if buy_order_num >= 2 or sell_order_num >= 2:
            return

    symbol_avail_num = symbol_avail_amount / sell_amount
    symbol_forzen_num = symbol_forzen_amount / sell_amount

    ustc_avail_num = ustc_avail_amount / buy_amount
    usct_forzen_num = ustc_forzen_amount / buy_amount

    if symbol_forzen_num > 3 or usct_forzen_num > 3:
        return
    if ustc_avail_num >= 1 and symbol_avail_num < 3 and usct_forzen_num < 3 and symbol_avail_num + usct_forzen_num < 3:
        buy_action(this_symbol,now_price + soft_point * now_price ,buy_amount)
    if symbol_avail_num >= 1:
        sell_action(this_symbol, now_price - soft_point * now_price ,sell_amount)
    while symbol_avail_num > 2:
        sell_action(this_symbol, now_price - soft_point * now_price ,sell_amount)
        symbol_avail_num = symbol_avail_num -1

    if tmp_filled_order_split < filled_order_split:
        tmp_filled_order_split = tmp_filled_order_split + 1
        return
    tmp_filled_order_split=0
    sub_order_list = api.list_orders(symbol=this_symbol, states=filled)

    if sub_order_list is None:
        return

    if sub_order_list and len(sub_order_list):
        sort_list= sub_order_list['data']
        sort_list = sorted(sort_list,key=lambda order_t:float(order_t['created_at']),reverse=False)
        for order in sort_list:
            this_states = order[Order_info['state']]
            if this_states == filled:
                order_id = order[Order_info['id']]
                if order_id not in order_dict:
                    order_dict[order_id] = 1
                    order_time = order[Order_info['created_at']]
                    #print(order_time,now_timestamp)
                    if float(order_time) < start_time:
                        continue
                    order_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(order_time / 1000))
                    order_fee = float(buy_amount) * 0.001 * float(now_price)
                    fee_cost = float(fee_cost) + float(order_fee)
                    left_usdt = float(ustc_avail_amount) + float(ustc_forzen_amount) + (float(
                        symbol_forzen_amount) + float(symbol_avail_amount)) * float(now_price)
                    loss_usdt = init_usdt - left_usdt - fee_cost
                    order_file.writelines(
                        str(order_time) + '\t' + str(left_usdt) + '\t' + str(fee_cost) + '\t' + str(loss_usdt) + "\t" +
                        order[Order_info['side']]  + "\t" + str(order[Order_info['price']]) + "\t" + str(
                            order_fee) + "\n")
                    order_file.flush()

# 买操作
def buy_action(this_symbol,price, this_amount):
    buy_result = api.buy(this_symbol,price, this_amount)
    if buy_result is None:
        print(this_symbol,price,this_amount)
        print(gettime(),"挂 买单 失败")
        return True
    buy_order_id = buy_result['data']
    if buy_order_id:
        print(gettime(), '成功市价买入', '订单ID', buy_order_id)

    return buy_order_id


# 卖操作
def sell_action(this_symbol, price,this_amount):
    this_amount = get_float(this_amount, 2)
    sell_result = api.sell(this_symbol,price, this_amount)

    if sell_result is None:
        print(gettime(),"挂 卖单失败")
        pass
    else:
        sell_order_id = sell_result['data']
        if sell_order_id:
            print( gettime(),'成功市价卖出', '订单ID', sell_order_id)

        return sell_order_id

# 撤销订单
def cancel_order_action(this_order_id):
    api.cancel_order(this_order_id)

# 获取行情
def get_ticker(this_symbol):
    ticker = api.get_market_ticker(symbol)
    if ticker is None:
        return None
    ticker_list = ticker['data']['ticker']
    now_price = ticker_list[0]
    print(gettime(),'最新成交价', now_price,'买一价',ticker_list[2],'买一量',ticker_list[3],'卖一价',ticker_list[4],'卖一量',ticker_list[5])

    return now_price


def robot():
    #try:
        do_one_action(symbol)
    #except:
    #    print(gettime(),"出现异常")

# 定时器
def timer():
    while True:
        robot()
        time.sleep(1)


# 守护进程
if __name__ == '__main__':

    print(gettime())
    t = threading.Thread(target=timer())
    t.start()
    t.join()




