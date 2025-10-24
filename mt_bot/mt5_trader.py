import MetaTrader5 as mt5
from shared.constants import DEFAULT_LOT_SIZE, MT5_ACCOUNT_DEMO, MT5_PASSWORD_DEMO, MT5_SERVER_DEMO, MAX_SLIPPAGE_PT, MAGIC_NUMBER
import datetime
from domain.models import Signal, TradeResult


class MT5Trader:
    """Encapsulates connection to MetaTrader 5 and trade execution."""

    def __init__(self, account: int = MT5_ACCOUNT_DEMO, password: str = MT5_PASSWORD_DEMO, server: str = MT5_SERVER_DEMO):
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


    def _get_order_price(self, symbol: str, side: str) -> float:
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            raise RuntimeError(f"No tick data for {symbol}")
        return tick.ask if side.upper() == "BUY" else tick.bid


    def _build_order_request(self, signal: Signal, price: float) -> dict:
        order_type = mt5.ORDER_TYPE_BUY if signal.side.upper() == "BUY" else mt5.ORDER_TYPE_SELL
        return {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": signal.symbol,
            "volume": DEFAULT_LOT_SIZE,
            "type": order_type,
            "price": price,
            "sl": signal.sl,
            "tp": signal.tp,
            "deviation": MAX_SLIPPAGE_PT,
            "magic": MAGIC_NUMBER,
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
            executed_at=datetime.now(),
        )