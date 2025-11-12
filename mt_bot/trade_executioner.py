from domain.models import Signal, TradeResult
from mt_bot.mt5_client import MT5Client
from shared.constants import DEFAULT_SYMBOL, MT5_ACCOUNT, MT5_PASSWORD, MT5_SERVER

class TradeExecutioner:
    def __init__(self):
        self.trader = MT5Client(MT5_ACCOUNT, MT5_PASSWORD, MT5_SERVER)

    def execute_trade(self, signal: Signal) -> TradeResult:
        """Execute a trade based on the parsed signal."""
        with self.trader:
            symbol = DEFAULT_SYMBOL
            side = signal.side
            tp = signal.tp
            sl = signal.sl
            
            print(f"Placing {side} order for {symbol}, TP: {tp}, SL: {sl}")
            result = self.trader.place_market_order(signal)
            print(f"Order result: {result.comment}")
            simulation_result = self.trader.place_simulation_market_order(signal)
            print(f"Order result: {simulation_result.comment}")
