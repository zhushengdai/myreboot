
class Balance():
    def __init__(self):
        self.currency=''
        self.balance=0
        self.available=0
        self.frozen=0
    def __str__(self):
        return self.currency +'\t账户余额\t' + str(self.balance)+ "\t可用:\t" + str(self.available) +"\t冻结:\t" + str(self.frozen)

class Order():
    def __init__(self):
        self.id = ''
        self.price = 0
        self.avg_price = 0
        self.executed_volume = 0
        self.amount = 0
        self.side = ''
        self.created_at = 0
        self.state = ''
        self.symbol = ''
        self.fee = 0
        self.money = 0
        self.coin = ''
        self.currency = ''
    def __str__(self):
        if self.state == State.submitted:
            return 'id\t' + str(self.id) + '\t价格\t' + str(self.price) + '\t数量\t' + str(self.amount)+ '\t挂单方向\t' + self.side
        elif self.state == State.filled:
            return 'id\t' + str(self.id) + '\t价格\t' + str(self.avg_price) + '\t数量\t' + str(self.executed_volume)+ '\t成交单方向\t' + self.side
        return 'id\t' + str(self.id) + '\t价格\t' + str(self.price) + '\t数量\t' + str(self.amount) + '\t挂单方向\t' + self.side

class State():
    filled='filled'
    submitted='submitted'

class Ticker():
    def __init__(self):
        self.last=0
        self.symbol=''
        self.buy=0
        self.sell=0
    def __str__(self):
        return self.symbol + "\t当前价\t" +str(self.last)

class Side():
    buy='buy'
    sell='sell'

class Kline():
    def __init__(self):
        self.high=0
        self.low=0
        self.open=0
        self.close=0
        self.time=0
        self.num=0
    def __str__(self):
        return str(self.num)+"\t" + '\t开\t'+ str(self.open) + '\t收\t' + str(self.close) +'\t低\t' + str(self.low) + '\t高\t' + str(self.high)
