from os import path
import pandas as pd

DATAFOLDER = path.join(path.split(path.dirname(__file__))[0], 'data')


def load_binance_ohlcv(pair, start=None, stop=None, index_col='close_time'):
    filename = path.join(DATAFOLDER, 'ohlcv', 'binance', '1min', 'binance_ohlcv_%s_1min.h5' % (pair,))

    if (isinstance(start, int) or start is None) and (isinstance(stop, int) or stop is None):
        ohlcv = pd.read_hdf(filename, key='/ohlcv', start=start, stop=stop)
    elif isinstance(start, pd.Timestamp) and stop is None:
        start_date = str(start)
        ohlcv = pd.read_hdf(filename, key='/ohlcv', where='(index >= start_date)')
    elif isinstance(stop, pd.Timestamp) and start is None:
        stop_date = str(stop)
        ohlcv = pd.read_hdf(filename, key='/ohlcv', where='(index < stop_date)')
    elif isinstance(start, pd.Timestamp) and isinstance(stop, pd.Timestamp):
        start_date, stop_date = str(start), str(stop)
        ohlcv = pd.read_hdf(filename, key='/ohlcv', where='(index >= start_date) & (index < stop_date)')
    else:
        raise Exception('Wrong start stop specification')
    if index_col == 'close_time':
        ohlcv = ohlcv.set_index('close_time', drop=True)
        ohlcv.index = ohlcv.index.ceil('1min')
    ohlcv.index.rename('date', inplace=True)
    ohlcv = ohlcv[~ohlcv.index.duplicated(keep='last')]
    ohlcv = ohlcv.sort_index()
    return ohlcv


def load_binance_ohlcvs(pairs, start=None, stop=None, index_col='close_time'):
    return {p: load_binance_ohlcv(p, start, stop, index_col) for p in pairs}


def resample_ohlcv(ohlcv, period):
    return ohlcv.resample(period).agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'})


def ohlcv_time_split(ohlcv, val_perc, test_perc=0):
    val_start = int(len(ohlcv)*(1 - (val_perc + test_perc)))
    test_start = int(len(ohlcv)*(1 - test_perc))
    if test_perc > 0:
        return ohlcv.iloc[: val_start], ohlcv.iloc[val_start: test_start], ohlcv.iloc[test_start:]
    else:
        return ohlcv.iloc[: val_start], ohlcv.iloc[val_start: test_start]
