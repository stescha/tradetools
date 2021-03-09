import pytest
import numpy as np


def test_eval_signals(result_bt, result_eval):
    ohlcv, signals, trades, equity, metrics, metadata = result_bt
    open_idx, close_idx, values, positions, pnlcomm_rel = result_eval
    assert (open_idx == trades.baropen).all()
    assert (close_idx == trades.barclose).all()
    assert np.allclose(metadata['start_capital'] + values, equity['values'])
    assert np.allclose(positions, equity['position'])
    assert np.allclose(pnlcomm_rel, trades['pnlcomm_rel'])
    assert len(pnlcomm_rel) == metrics['tradecount']