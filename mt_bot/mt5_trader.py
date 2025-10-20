import MetaTrader5 as mt5
from shared.constants import DEFAULT_LOT_SIZE, MT5_ACCOUNT, MT5_PASSWORD, MT5_SERVER, MAX_SLIPPAGE_PT, MAGIC_NUMBER


class MT5Trader:
    """Encapsulates connection to MetaTrader 5 and trade execution."""

    def __init__(self, account: int = MT5_ACCOUNT, password: str = MT5_PASSWORD, server: str = MT5_SERVER):
        self.account = account
        self.password = password
        self.server = server
        self.connected = False

    def connect(self):
        """Initialize MT5 and log in to the given account."""
        if not mt5.initialize():
            raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")

        if self.account and self.password and self.server:
            if not mt5.login(self.account, self.password, self.server):
                err = mt5.last_error()
                mt5.shutdown()
                raise RuntimeError(f"MT5 login failed: {err}")
        self.connected = True
        print("[MT5] Connected successfully.")

    def ensure_symbol(self, symbol: str):
        """Make sure a symbol is available and visible."""
        info = mt5.symbol_info(symbol)
        if info is None:
            raise RuntimeError(f"Symbol {symbol} not found on broker.")
        if not info.visible:
            if not mt5.symbol_select(symbol, True):
                raise RuntimeError(f"Failed to select {symbol}")
        return mt5.symbol_info(symbol)

    def place_market_order(self, symbol: str, side: str, entry_low: float, entry_high: float, tp=None, sl=None):
        """Place a market order with optional TP/SL."""
        self.ensure_symbol(symbol)
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise RuntimeError(f"No tick information for {symbol}")
        
        tick_size = mt5.symbol_info(symbol).trade_tick_size
        print(f"Tick Size for {symbol}: {tick_size}")

        print(f"Current Ask: {tick.ask}, Current Bid: {tick.bid}")

        order_type = None
        if side.upper() == "SELL":
            order_type = mt5.ORDER_TYPE_SELL
        else:
            order_type = mt5.ORDER_TYPE_BUY
            
        price = 0.0
        if tick.ask < entry_high and tick.ask > entry_low:
            price = tick.ask

        # symbol_info = mt5.symbol_info(symbol)
        # stop_level = symbol_info.trade_stops_level
        # freeze_level = symbol_info.trade_freeze_level
        # tick_size = symbol_info.trade_tick_size

        # Print out the details for debugging
        # print(f"Stop Level: {stop_level}")
        # print(f"Freeze Level: {freeze_level}")
        # print(f"Tick Size: {tick_size}")

        # print(f"Order Type: {order_type}, Price: {price}")

        # print(f"SYMBOL: {symbol}")
        # print(f"DEFAULT_LOT_SIZE: {DEFAULT_LOT_SIZE}")
        # print(f"MAGIC_NUMBER: {MAGIC_NUMBER}")
        # print(f"SLIPPAGE: {MAX_SLIPPAGE_PT}")
        # print(f"TP: {tp}, SL: {sl}")

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": 0.2,
            "type": order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 10,
            "magic": 123456789,
            "comment": "Test order from API",
            "type_time": mt5.ORDER_TIME_DAY,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }


        result = mt5.order_send(request)
        print(f"[MT5] order_send -> {result}")
        if result is None:
            raise RuntimeError(f"Order send failed: {mt5.last_error()}")
        return result




    # def place_market_order(self, symbol: str, side: str, entry_low: float, entry_high: float, tp=None, sl=None):
    #     """Place a market order with optional TP/SL."""
    #     self.ensure_symbol(symbol)
    #     tick = mt5.symbol_info_tick(symbol)
    #     if tick is None:
    #         raise RuntimeError(f"No tick for {symbol}")

    #     price = tick.ask if side.upper() == "BUY" else tick.bid
    #     order_type = mt5.ORDER_TYPE_BUY if side.upper() == "BUY" else mt5.ORDER_TYPE_SELL

    #     print(f"Lot Size: {DEFAULT_LOT_SIZE}")

    #     request = {
    #         "action": mt5.TRADE_ACTION_DEAL,
    #         "symbol": symbol,
    #         "volume": DEFAULT_LOT_SIZE,
    #         "type": order_type,
    #         "price": price,
    #         "sl": sl or 0.0,
    #         "tp": tp or 0.0,
    #         "deviation": MAX_SLIPPAGE_PT,
    #         "magic": MAGIC_NUMBER,
    #         "comment": "Telegram auto-trade",
    #         "type_time": mt5.ORDER_TIME_DAY,
    #         "type_filling": mt5.ORDER_FILLING_IOC,
    #     }
        

    #     result = mt5.order_send(request)
    #     print(f"[MT5] order_send -> {result}")
    #     if result is None:
    #         raise RuntimeError(f"Order send failed: {mt5.last_error()}")
    #     return result
