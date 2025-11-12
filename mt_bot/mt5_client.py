import MetaTrader5 as mt5
from shared.constants import DEFAULT_LOT_SIZE, MT5_ACCOUNT_DEMO, MT5_PASSWORD_DEMO, MT5_SERVER_DEMO, MAX_SLIPPAGE_PT, MAGIC_NUMBER
import datetime
from domain.models import Signal, TradeResult


class MT5Client:
    """Encapsulates connection to MetaTrader 5 and trade execution."""

    def __init__(self, account: int = MT5_ACCOUNT_DEMO, password: str = MT5_PASSWORD_DEMO, server: str = MT5_SERVER_DEMO):
        self.account = account
        self.password = password
        self.server = server
        self.connected = False

    def __enter__(self):
        """Allow usage with 'with' statement."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensure MT5 is properly shutdown on exit."""
        self.shutdown()

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

    def shutdown(self):
        """Cleanly shutdown MT5 connection."""
        if self.connected:
            mt5.shutdown()
            self.connected = False
            print("[MT5] Connection closed.")

    def ensure_symbol(self, symbol: str):
        """Make sure a symbol is available and visible."""
        info = mt5.symbol_info(symbol)
        if info is None:
            raise RuntimeError(f"Symbol {symbol} not found on broker.")
        if not info.visible:
            if not mt5.symbol_select(symbol, True):
                raise RuntimeError(f"Failed to select {symbol}")
        return mt5.symbol_info(symbol)


    def get_ticks(self, symbol: str, _from: datetime, _to: datetime):
        """Tick-level (best for exact TP/SL-first order)."""
        self.ensure_symbol(symbol)
        return mt5.copy_ticks_range(symbol, int(_from.timestamp()*1000), int(_to.timestamp()*1000), mt5.COPY_TICKS_ALL)


    def get_bars(self, symbol: str, timeframe: int, _from: datetime, _to: datetime):
        """OHLC bars (faster but less precise)."""
        self.ensure_symbol(symbol)
        return mt5.copy_rates_range(symbol, timeframe, _from, _to)


    def place_market_order(self, signal: Signal) -> TradeResult:
        """Placing a market order based on the signal."""
        self.ensure_symbol(signal.symbol)
        price = self._get_order_price(signal.symbol, signal.side)
        request = self._build_order_request(signal, price)
        result = mt5.order_send(request)
        return self._process_order_result(result)

    def place_simulation_market_order(self, signal: Signal) -> TradeResult:
        """Placing a simulation market order based on the signal."""
        self.ensure_symbol(signal.symbol)
        price = self._get_order_price(signal.symbol, signal.side)
        request = self._build_simulation_order_request(signal, price)
        result = mt5.order_send(request)
        return self._process_order_result(result)

    def _get_order_price(self, symbol: str, side: str) -> float:
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            raise RuntimeError(f"No tick data for {symbol}")
        return tick.ask if side.upper() == "BUY" else tick.bid


    def _decide_entry(self, symbol: str, side: str, entry_low: float, entry_high: float) -> tuple[str, float | None]:
        """Determine entry type and entry price based on the signal and current market price."""
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            return mt5.ORDER_TYPE_BUY, None

        ask, bid = tick.ask, tick.bid
        side = side.upper()

        if side == "BUY":
            if entry_low > ask:
                return mt5.ORDER_TYPE_BUY_STOP, entry_low
            if entry_high < ask:
                return mt5.ORDER_TYPE_BUY_LIMIT, entry_high
            return mt5.ORDER_TYPE_BUY, ask
        else:
            if entry_high < bid:
                return mt5.ORDER_TYPE_SELL_STOP, entry_high
            if entry_low > bid:
                return  mt5.ORDER_TYPE_SELL_LIMIT, entry_low
            return mt5.ORDER_TYPE_SELL, bid


    def _build_order_request(self, signal: Signal, price: float) -> dict:
        order_type, entry_price = self._decide_entry(signal.symbol, signal.side, signal.entry_low, signal.entry_high)
        action = (
            mt5.TRADE_ACTION_DEAL
            if order_type == mt5.ORDER_TYPE_BUY or order_type == mt5.ORDER_TYPE_SELL
            else mt5.TRADE_ACTION_PENDING
        )

        mapping = {
            "XAUUSD.S": 0.01,
            "USDJPY.S": 0.04,
        }
        volume = mapping.get(signal.symbol.upper())
        return {
            "action": action,
            "symbol": signal.symbol,
            "volume": volume,
            "type": order_type,
            "price": entry_price,
            "sl": signal.sl,
            "tp": signal.tp,
            "deviation": 100,
            "magic": 123456789,
            "comment": "Trade via API",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
    
    def _build_simulation_order_request(self, signal: Signal, price: float) -> dict:
        order_type = mt5.ORDER_TYPE_BUY if signal.side.upper() == "BUY" else mt5.ORDER_TYPE_SELL
        
        mapping = {
            "XAUUSD.S": 0.01,
            "USDJPY.S": 0.04,
        }
        volume = mapping.get(signal.symbol.upper())

        return {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": signal.symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "sl": signal.sl,
            "tp": signal.tp,
            "deviation": 100,
            "magic": 123456789,
            "comment": "Trade via API",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }



    def _process_order_result(self, result) -> TradeResult:
        if result is None:
            raise RuntimeError(f"Order send failed: {mt5.last_error()}")
        success = result.retcode in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED)
        return TradeResult(
            success=success,
            order_id=result.order,
            deal_id=result.deal,
            price=result.price,
            comment=result.comment,
            executed_at=datetime.datetime.now(),
        )