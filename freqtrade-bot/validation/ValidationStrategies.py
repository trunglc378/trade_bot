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
        # Only use the 1h trend once the informative candle has closed.
        allowed = dataframe['trend_ok_1h'].eq(True)
        dataframe.loc[~allowed, ['enter_long', 'enter_tag']] = (0, '')
        return dataframe


class VnTrend15mCandidate(VnTrend1hCandidate):
    timeframe = '15m'

    @property
    def protections(self):
        # Keep the original protection windows in minutes across both timeframes.
        settings = super().protections
        for protection in settings:
            for key in ('lookback_period_candles', 'stop_duration_candles'):
                if key in protection:
                    protection[key] = protection[key] // 3
        return settings


class VnTrend15mEntryCandidate(VnTrend1hCandidate):
    @informative('15m', ffill=False)
    def populate_entry_indicators_15m(self, dataframe, metadata):
        dataframe = super().populate_indicators(dataframe, metadata)
        signals = self._populate_entry_signals(dataframe)
        return signals[['date', 'enter_long', 'enter_tag']]

    def populate_entry_trend(self, dataframe, metadata):
        # The 15m signal is available only on the 5m candle with the same close.
        allowed = dataframe['enter_long_15m'].eq(1) & dataframe['trend_ok_1h'].eq(True)
        dataframe['enter_long'] = allowed.astype(int)
        dataframe['enter_tag'] = dataframe['enter_tag_15m'].where(allowed, '')
        return self._filter_entry_schedule(dataframe)


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
