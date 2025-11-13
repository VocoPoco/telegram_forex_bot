import MetaTrader5 as mt5
from shared.constants import (
    DEFAULT_LOT_SIZE,
    MT5_ACCOUNT_DEMO,
    MT5_PASSWORD_DEMO,
    MT5_SERVER_DEMO,
    MAX_SLIPPAGE_PT,
    MAGIC_NUMBER,
)
import datetime
from domain.models import Signal, TradeResult
import logging

logger = logging.getLogger(__name__)


class MT5Client:
    """Encapsulates connection to MetaTrader 5 and trade execution."""

    def __init__(
        self,
        account: int = MT5_ACCOUNT_DEMO,
        password: str = MT5_PASSWORD_DEMO,
        server: str = MT5_SERVER_DEMO,
    ):
        self.account = account
        self.password = password
        self.server = server
        self.connected = False

        logger.info(
            "MT5Client initialized for account=%s, server=%s",
            self.account,
            self.server,
        )

    def __enter__(self):
        """Allow usage with 'with' statement."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensure MT5 is properly shutdown on exit."""
        self.shutdown()

    def connect(self):
        """Initialize MT5 and log in to the given account."""
        logger.info("Initializing MT5 terminal...")
        if not mt5.initialize():
            err = mt5.last_error()
            logger.error("MT5 initialize failed: %s", err)
            raise RuntimeError(f"MT5 initialize failed: {err}")

        if self.account and self.password and self.server:
            logger.info(
                "Logging in to MT5 account %s on server %s",
                self.account,
                self.server,
            )
            if not mt5.login(self.account, self.password, self.server):
                err = mt5.last_error()
                logger.error("MT5 login failed: %s", err)
                mt5.shutdown()
                raise RuntimeError(f"MT5 login failed: {err}")

        self.connected = True
        logger.info("[MT5] Connected successfully.")

    def shutdown(self):
        """Cleanly shutdown MT5 connection."""
        if self.connected:
            logger.info("Shutting down MT5 connection...")
            mt5.shutdown()
            self.connected = False
            logger.info("[MT5] Connection closed.")
        else:
            logger.debug("Shutdown called but MT5 was not marked as connected.")

    def ensure_symbol(self, symbol: str):
        """Make sure a symbol is available and visible."""
        logger.debug("Ensuring symbol is available: %s", symbol)
        info = mt5.symbol_info(symbol)
        if info is None:
            logger.error("Symbol %s not found on broker.", symbol)
            raise RuntimeError(f"Symbol {symbol} not found on broker.")

        if not info.visible:
            logger.info("Symbol %s not visible. Attempting to select.", symbol)
            if not mt5.symbol_select(symbol, True):
                logger.error("Failed to select symbol %s", symbol)
                raise RuntimeError(f"Failed to select {symbol}")

        logger.debug("Symbol %s is ready for trading.", symbol)
        return mt5.symbol_info(symbol)

    def get_ticks(self, symbol: str, _from: datetime.datetime, _to: datetime.datetime):
        """Tick-level (best for exact TP/SL-first order)."""
        logger.info("Fetching ticks for %s from %s to %s", symbol, _from, _to)
        self.ensure_symbol(symbol)
        ticks = mt5.copy_ticks_range(
            symbol,
            int(_from.timestamp() * 1000),
            int(_to.timestamp() * 1000),
            mt5.COPY_TICKS_ALL,
        )
        return ticks

    def get_bars(
        self,
        symbol: str,
        timeframe: int,
        _from: datetime.datetime,
        _to: datetime.datetime,
    ):
        """OHLC bars (faster but less precise)."""
        logger.info(
            "Fetching bars for %s timeframe=%s from %s to %s",
            symbol,
            timeframe,
            _from,
            _to,
        )
        self.ensure_symbol(symbol)
        bars = mt5.copy_rates_range(symbol, timeframe, _from, _to)
        return bars

    def place_market_order(self, signal: Signal) -> TradeResult:
        """Placing a market order based on the signal."""
        logger.info(
            "Placing live market order for signal: %s %s [%s - %s], tp=%s, sl=%s",
            signal.symbol,
            signal.side,
            signal.entry_low,
            signal.entry_high,
            signal.tp,
            signal.sl,
        )
        self.ensure_symbol(signal.symbol)
        price = self._get_order_price(signal.symbol, signal.side)
        request = self._build_order_request(signal, price)
        logger.debug("Order request (live): %s", request)
        result = mt5.order_send(request)
        return self._process_order_result(result)

    def place_simulation_market_order(self, signal: Signal) -> TradeResult:
        """Placing a simulation market order based on the signal."""
        logger.info(
            "Placing simulation market order for signal: %s %s, tp=%s, sl=%s",
            signal.symbol,
            signal.side,
            signal.tp,
            signal.sl,
        )
        self.ensure_symbol(signal.symbol)
        price = self._get_order_price(signal.symbol, signal.side)
        request = self._build_simulation_order_request(signal, price)
        logger.debug("Order request (simulation): %s", request)
        result = mt5.order_send(request)
        return self._process_order_result(result)

    def _get_order_price(self, symbol: str, side: str) -> float:
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            logger.error("No tick data for %s", symbol)
            raise RuntimeError(f"No tick data for {symbol}")

        price = tick.ask if side.upper() == "BUY" else tick.bid
        return price

    def _decide_entry(
        self,
        symbol: str,
        side: str,
        entry_low: float,
        entry_high: float,
    ) -> tuple[int, float | None]:
        """Determine entry type and entry price based on the signal and current market price."""
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            logger.warning("No tick data for %s while deciding entry; defaulting to BUY at market", symbol)
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
                return mt5.ORDER_TYPE_SELL_LIMIT, entry_low
            return mt5.ORDER_TYPE_SELL, bid

    def _build_order_request(self, signal: Signal, price: float) -> dict:
        order_type, entry_price = self._decide_entry(
            signal.symbol,
            signal.side,
            signal.entry_low,
            signal.entry_high,
        )

        action = (
            mt5.TRADE_ACTION_DEAL
            if order_type in (mt5.ORDER_TYPE_BUY, mt5.ORDER_TYPE_SELL)
            else mt5.TRADE_ACTION_PENDING
        )

        mapping = {
            "XAUUSD.S": 0.01,
            "USDJPY.S": 0.04,
        }
        volume = mapping.get(signal.symbol.upper(), DEFAULT_LOT_SIZE)

        if volume is None or volume <= 0:
            logger.warning(
                "Volume not found or invalid for symbol %s, using DEFAULT_LOT_SIZE=%s",
                signal.symbol,
                DEFAULT_LOT_SIZE,
            )
            volume = DEFAULT_LOT_SIZE

        request = {
            "action": action,
            "symbol": signal.symbol,
            "volume": volume,
            "type": order_type,
            "price": entry_price if entry_price is not None else price,
            "sl": signal.sl,
            "tp": signal.tp,
            "deviation": MAX_SLIPPAGE_PT,
            "magic": MAGIC_NUMBER,
            "comment": "Trade via API",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        return request

    def _build_simulation_order_request(self, signal: Signal, price: float) -> dict:
        order_type = mt5.ORDER_TYPE_BUY if signal.side.upper() == "BUY" else mt5.ORDER_TYPE_SELL

        mapping = {
            "XAUUSD.S": 0.01,
            "USDJPY.S": 0.04,
        }
        volume = mapping.get(signal.symbol.upper(), DEFAULT_LOT_SIZE)

        if volume is None or volume <= 0:
            logger.warning(
                "Simulation volume not found or invalid for symbol %s, using DEFAULT_LOT_SIZE=%s",
                signal.symbol,
                DEFAULT_LOT_SIZE,
            )
            volume = DEFAULT_LOT_SIZE

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": signal.symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "sl": signal.sl,
            "tp": signal.tp,
            "deviation": MAX_SLIPPAGE_PT,
            "magic": MAGIC_NUMBER,
            "comment": "Trade via API (simulation)",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        return request

    def _process_order_result(self, result) -> TradeResult:
        if result is None:
            err = mt5.last_error()
            logger.error("Order send returned None: %s", err)
            raise RuntimeError(f"Order send failed: {err}")

        logger.info(
            "Order send result: retcode=%s, comment=%s, order=%s, deal=%s, price=%s",
            result.retcode,
            result.comment,
            result.order,
            result.deal,
            result.price,
        )

        success = result.retcode in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED)
        if not success:
            logger.warning(
                "Order not successful: retcode=%s, comment=%s",
                result.retcode,
                result.comment,
            )

        trade_result = TradeResult(
            success=success,
            order_id=result.order,
            deal_id=result.deal,
            price=result.price,
            comment=result.comment,
            executed_at=datetime.datetime.now(),
        )

        logger.debug("TradeResult created: %s", trade_result)
        return trade_result
