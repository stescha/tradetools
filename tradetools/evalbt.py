import backtrader as bt
import numpy as np
import pandas as pd
from datetime import timedelta
import os


class SignalStrat(bt.Strategy):

    def __init__(self, buys, sells):
        self.buys = buys
        self.sells = sells
        self.dataclose = self.datas[0].close
        self.in_trade = False
        self.n_ticks = len(self.dataclose.array)

    def next(self):
        i = len(self) - 1
        if i >= self.n_ticks - 2:
            if self.in_trade:
                self.close()
                self.in_trade = False
            return
        if self.buys[i] and not self.in_trade:

            self.buy()
            self.in_trade = True
        elif self.sells[i] and self.in_trade:
            self.close()
            self.in_trade = False


class InvestAll(bt.Sizer):

    def __init__(self, sizing):
        self.sizing = sizing

    def _getsizing(self, comminfo, cash, data, isbuy):
        if isbuy:
            c = comminfo.p.commission
            self.stake = self.sizing*(1 - 2*c) * cash / data.close[0]
        return self.stake


def get_bt_timeframe(ohlcv):
    dt = ohlcv.index[1] - ohlcv.index[0]
    if dt < timedelta(seconds=1):
        timeframe = bt.TimeFrame.MicroSeconds
    elif dt < timedelta(minutes=1):
        timeframe = bt.TimeFrame.Seconds
    elif dt < timedelta(hours=1):
        timeframe = bt.TimeFrame.Minutes
    elif dt < timedelta(days=7):
        timeframe = bt.TimeFrame.Days
    elif dt < timedelta(days=30):
        timeframe = bt.TimeFrame.Weeks
    else:
        raise Exception('Wrong timeframe in BacktradeRunner')
    return timeframe


def bt_eval(ohlcv, buys, sells, start_capital, fee, position_rel=None):
    timeframe = get_bt_timeframe(ohlcv)
    cerebro = bt.Cerebro(cheat_on_open=False, stdstats=True)
    data_feed = bt.feeds.PandasData(dataname=ohlcv, timeframe=timeframe)

    cerebro.adddata(data_feed)
    cerebro.broker.setcash(start_capital)
    cerebro.broker.setcommission(commission=fee)
    cerebro.broker.set_slippage_perc(0.000)

    if position_rel is not None:
        cerebro.addsizer(InvestAll, sizing=position_rel)

    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpeanalyzer', riskfreerate=0, factor=1,
                        convertrate=False, timeframe=timeframe, compression=1)
    cerebro.addanalyzer(bt.analyzers.VWR, _name='vwr', timeframe=timeframe, compression=1, tann=252,
                        tau=2.0, sdev_max=0.2)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')
    cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='timereturns', fund=None, compression=1)
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns', timeframe=timeframe)
    cerebro.addanalyzer(bt.analyzers.PositionsValue, _name='positions', cash=True)
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='tradeanalyzer')
    cerebro.addobserver(bt.observers.Value)
    cerebro.addobserver(bt.observers.Broker)
    cerebro.addobserver(bt.observers.TimeReturn)
    cerebro.addobserver(bt.observers.Cash) ## == Broker

    cerebro.addstrategy(SignalStrat, buys=buys, sells=sells)
    results = cerebro.run(runonce=False)
    result = results[0]
    returns = pd.Series(result.analyzers.timereturns.get_analysis())
    equity = pd.DataFrame(result.analyzers.positions.get_analysis(), index=['position', 'balance']).T
    equity['returns'] = returns
    equity['values'] = result.observers.value.array
    equity.position = equity.position / ohlcv.close

    trades = result._trades[data_feed][0]
    trades = get_trade_history(trades)
    trades['sell_price'] = ohlcv.open.loc[trades.sell_time].values

    logreturns = result.analyzers.returns.get_analysis()
    sharpe = result.analyzers.sharpeanalyzer.get_analysis()
    vwr = result.analyzers.vwr.get_analysis()
    metrics = dict(**logreturns, **sharpe, **vwr)

    trade_analysis = result.analyzers.tradeanalyzer.get_analysis()
    metrics['tradecount'] = trade_analysis['total']['closed']
    metrics['won_count'] = trade_analysis['won']['total']
    metrics['lost_count'] = trade_analysis['lost']['total']
    metrics['pnl_sum'] = trade_analysis['long']['pnl']['total']
    metrics['pnl_mean'] = trade_analysis['long']['pnl']['average']
    metrics['pnl_won_sum'] = trade_analysis['won']['pnl']['total']
    metrics['pnl_won_mean'] = trade_analysis['won']['pnl']['average']
    metrics['pnl_lost_sum'] = trade_analysis['lost']['pnl']['total']
    metrics['pnl_lost_mean'] = trade_analysis['lost']['pnl']['average']

    metrics['sqn_abs'] = result.analyzers.sqn.get_analysis()['sqn']
    metrics['sqn'] = np.sqrt(metrics['tradecount']) * trades['pnlcomm_rel'].mean() / trades['pnlcomm_rel'].std()


    drawdown_analysis = result.analyzers.drawdown.get_analysis()
    metrics['drawdown_len'] = drawdown_analysis['max']['len']
    metrics['drawdown_perc'] = drawdown_analysis['max']['drawdown']
    metrics['drawdown'] = drawdown_analysis['max']['moneydown']
    metrics = pd.Series(metrics)
    return equity, trades, metrics

def get_trade_history(trades):
    trade_hist = []
    for trade in trades:
        t = [bt.num2date(trade.dtopen),
            bt.num2date(trade.dtclose) if trade.dtclose > 0 else None,
            trade.baropen - 1, # backtrader index starts with 1
            trade.barclose - 1,
            # trade.size,
            # trade.commission,
            trade.pnl,
            trade.pnlcomm,
            trade.price,
            # trade.value
            ]
        trade_hist.append(t)

    trade_hist = pd.DataFrame(trade_hist, columns=['buy_time', 'sell_time', 'baropen', 'barclose', 'pnl', 'pnlcomm',
                                                   'buy_price'])
    trade_hist['pnlcomm_rel'] = trade_hist['pnlcomm'] / trade_hist['buy_price']
    return trade_hist


def get_rnd_signals(index, signal_prob, seed=None):
    np.random.seed(seed)
    signals = np.random.random(len(index)) < signal_prob
    np.random.seed(None)
    return pd.Series(signals, index=index.copy())

def save_rnd_results(ohlcv, filename, start_capital, fee):
    buys = get_rnd_signals(ohlcv.index, signal_prob=0.1, seed=None)
    sells = get_rnd_signals(ohlcv.index, signal_prob=0.1, seed=None)
    equity, trades, metrics = bt_eval(ohlcv, buys, sells, start_capital, fee)
    buys.name = 'buy'
    sells.name = 'sell'
    signals = pd.concat([buys, sells], axis=1)
    if os.path.exists(filename):
        os.remove(filename)
    with pd.HDFStore(filename, mode='w') as store:
        store.put('ohlcv', ohlcv)
        store.put('signals', signals)
        # store.put('data/ohlcv2', ohlcv)
        store.put('trades', trades)
        store.put('equity', equity)
        store.put('metrics', metrics)
        store.get_storer('equity').attrs.metadata = {'start_capital': start_capital,
                                                     'fee': fee}


def load_rnd_results(filename):
    with pd.HDFStore(filename, mode='r') as store:
        ohlcv = store['ohlcv']
        signals = store['signals']
        trades = store['trades']
        equity = store['equity']
        metrics = store['metrics']
        metadata = store.get_storer('equity').attrs.metadata
    return ohlcv, signals, trades, equity, metrics, metadata

