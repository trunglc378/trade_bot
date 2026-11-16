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


class VnTrendPullbackCandidate(VnTrend1hCandidate):
    def populate_entry_trend(self, dataframe, metadata):
        dataframe = super().populate_entry_trend(dataframe, metadata)
        # Enter after a recent pullback to EMA20 and a close back above it.
        previous_retest = (dataframe['low'] <= dataframe['ema20']).shift(1)
        reclaimed = previous_retest.eq(True) & (dataframe['close'] > dataframe['ema20'])
        dataframe.loc[~reclaimed, ['enter_long', 'enter_tag']] = (0, '')
        return dataframe


class VnTrendQualityCandidate(VnTrend1hCandidate):
    def populate_indicators(self, dataframe, metadata):
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe['atr14'] = ta.ATR(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe, metadata):
        dataframe = super().populate_entry_trend(dataframe, metadata)
        acceptable = (
            (dataframe['ema50'] > dataframe['ema50'].shift(6))
            & (dataframe['close'] - dataframe['ema20'] <= dataframe['atr14'])
        )
        dataframe.loc[~acceptable, ['enter_long', 'enter_tag']] = (0, '')
        return dataframe


class VnTrendMarketCandidate(VnTrend1hCandidate):
    @informative('1h', 'BTC/USDT', fmt='market_{column}_{timeframe}')
    def populate_market_indicators(self, dataframe, metadata):
        ema = ta.EMA(dataframe, timeperiod=50)
        dataframe['trend_ok'] = (dataframe['close'] > ema) & (ema > ema.shift(3))
        return dataframe

    def populate_entry_trend(self, dataframe, metadata):
        dataframe = super().populate_entry_trend(dataframe, metadata)
        dataframe.loc[~dataframe['market_trend_ok_1h'].eq(True), ['enter_long', 'enter_tag']] = (0, '')
        return dataframe
