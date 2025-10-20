from mt_bot.mt5_trader import MT5Trader
from shared.constants import DEFAULT_SYMBOL, MT5_ACCOUNT, MT5_PASSWORD, MT5_SERVER

class TradeExecutioner:
    def __init__(self):
        self.trader = MT5Trader(MT5_ACCOUNT, MT5_PASSWORD, MT5_SERVER)

    def execute_trade(self, signal):
        """Execute a trade based on the parsed signal."""
        if not self.trader.connected:
            self.trader.connect()

        symbol = DEFAULT_SYMBOL
        side = signal['side']
        tp = signal.get('tp')
        sl = signal.get('sl')
        entry_low = signal.get('entry_low')
        entry_high = signal.get('entry_high')
        
        print(f"Placing {side} order for {symbol}, TP: {tp}, SL: {sl}")
        result = self.trader.place_market_order(symbol, side, entry_low, entry_high, tp, sl)
        print(f"Order result: {result}")