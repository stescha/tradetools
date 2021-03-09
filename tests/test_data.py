import pytest
import tradetools as tt
import pandas as pd


@pytest.mark.parametrize('index_col', ['open_time', 'close_time'])
@pytest.mark.parametrize('pair', ['BTCUSDT', 'ETHUSDT'])
@pytest.mark.parametrize('start, stop', [(10000, 20000),
                                         (pd.Timestamp(2018, 1, 1), None),
                                         (None, pd.Timestamp(2018, 1, 1)),
                                         (pd.Timestamp(2018, 1, 1), pd.Timestamp(2018, 6, 1))])
def test_load_binance_ohlcv(pair, start, stop, index_col):
    o = tt.load_binance_ohlcv(pair, start=start, stop=stop, index_col=index_col)
    assert isinstance(o, pd.DataFrame)
    assert isinstance(o.index, pd.DatetimeIndex)
    assert o.index.name == 'date'
    if isinstance(start, int) and isinstance(stop, int):
        assert len(o) == (stop - start)
    if isinstance(start, pd.Timestamp):
        if index_col == 'open_time':
            assert o.index[0] == start
        else:
            assert o.index[0] == start + pd.Timedelta('1min')
    if isinstance(stop, pd.Timestamp):
        if index_col == 'open_time':
            assert o.index[-1] < stop
        else:
            assert o.index[-1] < stop + pd.Timedelta('1min')


@pytest.mark.parametrize('pairs', [('BTCUSDT', 'ETHUSDT', 'ETHBTC'),
                                   ('ETHUSDT', 'ETHBTC')])
def test_load_binance_ohlcvs(pairs):
    os = tt.load_binance_ohlcvs(pairs, start=0, stop=1000)
    assert len(os) == len(pairs)


@pytest.mark.parametrize('period', ('5min', '1h'))
def test_resample_ohlcv(period):
    o = tt.load_binance_ohlcv('BTCUSDT', stop=10000)
    o_res = tt.data.resample_ohlcv(o, period)
    assert (((o_res.index[1:] - o_res.index[:-1]) == pd.Timedelta(period)).all())


def test_ohlcv_time_split(ohlcv):
    ohlcv = ohlcv.iloc[:1000]
    ohlcv_train, ohlcv_val, ohlcv_test = tt.data.ohlcv_time_split(ohlcv, val_perc=0.3, test_perc=0.1)
    assert len(ohlcv_train) == 600
    assert len(ohlcv_val) == 300
    assert len(ohlcv_test) == 100
    ohlcv_train, ohlcv_val = tt.data.ohlcv_time_split(ohlcv, val_perc=0.3)
    assert len(ohlcv_train) == 700
    assert len(ohlcv_val) == 300
