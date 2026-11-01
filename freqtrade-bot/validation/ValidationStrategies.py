"""Research candidates only. Do not select these in the live Compose services."""
import talib.abstract as ta
from freqtrade.strategy import informative
from VnSmartTrendStrategy import VnSmartTrendStrategy


class VnTrend1hCandidate(VnSmartTrendStrategy):
    @informative('1h')
    def populate_indicators_1h(self, dataframe, metadata):
        dataframe['ema50'] = ta.EMA(dataframe, timeperiod=50)
        dataframe['ema200'] = ta.EMA(dataframe, timeperiod=200)
        dataframe['trend_ok'] = (
            (dataframe['close'] > dataframe['ema200'])
            & (dataframe['ema50'] > dataframe['ema200'])
            & (dataframe['ema50'] > dataframe['ema50'].shift(3))
        )
        return dataframe

    def populate_entry_trend(self, dataframe, metadata):
        dataframe = super().populate_entry_trend(dataframe, metadata)
        # informative() shifts the 1h data to its close before merging into 5m.
        allowed = dataframe['trend_ok_1h'].fillna(False).astype(bool)
        dataframe.loc[~allowed, ['enter_long', 'enter_tag']] = (0, '')
        return dataframe


class VnEarlierTrailCandidate(VnSmartTrendStrategy):
    # A hypothesis to test, not a chosen production setting.
    trailing_stop_positive_offset = 0.012
    trailing_stop_positive = 0.005


class VnTrendTrailCandidate(VnTrend1hCandidate):
    trailing_stop_positive_offset = 0.012
    trailing_stop_positive = 0.005
