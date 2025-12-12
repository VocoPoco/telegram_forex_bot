import MetaTrader5 as mt5
from shared.constants import (
    MT5_ACCOUNT,
    MT5_PASSWORD,
    MT5_SERVER,
)
import datetime
from models.signal import Signal
from models.trade_result import TradeResult
import logging

logger = logging.getLogger(__name__)


class MT5Client:
    """Encapsulates connection to MetaTrader 5 and trade execution."""
    
    MARKET_ORDER_TYPES = (mt5.ORDER_TYPE_BUY, mt5.ORDER_TYPE_SELL)

    def __init__(
        self,
        account: int = MT5_ACCOUNT,
        password: str = MT5_PASSWORD,
        server: str = MT5_SERVER,
    ):
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

    def get_market_price(self, symbol: str, side: str) -> float | None:
        """
        Return current market price for given symbol & side.
        BUY -> ask, SELL -> bid.
        """
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            logger.error("No tick data for %s", symbol)
            return None

        side = side.upper()
        return tick.ask if side == "BUY" else tick.bid

    def get_positions(self, ticket: int | None = None, symbol: str | None = None):
        """
        Wrapper around mt5.positions_get().
        - If ticket is given: return position(s) with that ticket.
        - If symbol is given: return all positions for that symbol.
        - If neither: return all open positions.
        """
        if ticket is not None:
            positions = mt5.positions_get(ticket=ticket)
        elif symbol is not None:
            positions = mt5.positions_get(symbol=symbol)
        else:
            positions = mt5.positions_get()

        if positions is None:
            err = mt5.last_error()
            logger.error("positions_get failed: %s", err)
            return tuple()

        return positions

    def get_orders(self, ticket: int | None = None, symbol: str | None = None):
        """
        Wrapper around mt5.orders_get().
        - If ticket is given: return order(s) with that ticket.
        - If symbol is given: return all orders for that symbol.
        - If neither: return all open orders.
        """
        if ticket is not None:
            orders = mt5.orders_get(ticket=ticket)
        elif symbol is not None:
            orders = mt5.orders_get(symbol=symbol)
        else:
            orders = mt5.orders_get()

        if orders is None:
            err = mt5.last_error()
            logger.error("orders_get failed: %s", err)
            return tuple()

        return orders

    def get_position_ticket(self, symbol: str, magic: int | None = 123456789) -> int | None:
        """
        Find the latest open position ticket for this symbol (optionally filtered by magic).
        Returns the position.ticket or None if not found.
        """
        positions = mt5.positions_get(symbol=symbol)
        if positions is None or len(positions) == 0:
            return None

        candidates = positions
        if magic is not None:
            candidates = [p for p in positions if p.magic == magic]
            if not candidates:
                candidates = positions

        pos = max(candidates, key=lambda p: p.time_msc)
        return pos.ticket

    def get_history_deals(self, position_id: int):
        """
        Returns deals for a given position id over the last `days_back` days.

        This uses:
          - mt5.history_select(from, to)
          - mt5.history_deals_get(position=position_id)
        and returns a tuple of TradeDeal namedtuples (or empty tuple).
        """

        deals = mt5.history_deals_get(position=position_id)
        if deals is None:
            err = mt5.last_error()
            return tuple()

        return deals

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
    
    def is_market_order_type(self, order_type: int) -> bool:
        """
        Return True if the given order_type is a market order (BUY/SELL).
        """
        return order_type in self.MARKET_ORDER_TYPES

    def place_pending_order(self, signal: Signal, offset: int) -> TradeResult:
        """Placing a pending order based on the signal."""
        logger.info(
            "Placing pending pending order for signal: %s %s [%s - %s], tp=%s, sl=%s",
            signal.symbol,
            signal.side,
            signal.entry_low,
            signal.entry_high,
            signal.tp,
            signal.sl,
        )
        self.ensure_symbol(signal.symbol)
        price = self._get_order_price(signal.symbol, signal.side)
        request = self._build_order_request(signal, price, offset)
        logger.debug("Order request (pending): %s", request)
        result = mt5.order_send(request)
        return self._process_order_result(result)
    
    def _ensure_valid_pending_price(
        self,
        symbol: str,
        side: str,
        order_type: int,
        price: float,
    ) -> tuple[int, float]:
        """
        Ensure that the pending price is still valid w.r.t current ASK/BID.
        If not, either adjust it or downgrade to a market order.
        Returns (final_order_type, final_price).
        """
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            raise RuntimeError(f"No tick data for {symbol} while validating pending price")

        ask, bid = tick.ask, tick.bid
        side = side.upper()

        if order_type == mt5.ORDER_TYPE_BUY_LIMIT:
            if price >= ask:
                logger.warning(
                    "BUY_LIMIT price %s is not below ask=%s anymore; converting to market BUY",
                    price,
                    ask,
                )
                return mt5.ORDER_TYPE_BUY, ask

        elif order_type == mt5.ORDER_TYPE_SELL_LIMIT:
            if price <= bid:
                logger.warning(
                    "SELL_LIMIT price %s is not above bid=%s anymore; converting to market SELL",
                    price,
                    bid,
                )
                return mt5.ORDER_TYPE_SELL, bid

        return order_type, price

    def place_instant_market_order(self, signal: Signal) -> TradeResult:
        """Placing a instant market order based on the signal."""
        logger.info(
            "Placing instant market order for signal: %s %s, tp=%s, sl=%s",
            signal.symbol,
            signal.side,
            signal.tp,
            signal.sl,
        )
        self.ensure_symbol(signal.symbol)
        price = self._get_order_price(signal.symbol, signal.side)
        request = self._build_instant_order_request(signal, price)
        logger.debug("Order request (instant): %s", request)
        result = mt5.order_send(request)
        return self._process_order_result(result)
    
    def cancel_pending_order(self, order_ticket: int):
        """Cancel a pending order by its ticket."""
        logger.info("Attempting to cancel pending order %s", order_ticket)

        request = {
            "action": mt5.TRADE_ACTION_REMOVE,
            "order": order_ticket,
        }

        result = mt5.order_send(request)
        if result is None:
            err = mt5.last_error()
            logger.error("Cancel order failed: %s", err)
            raise RuntimeError(f"Cancel order failed: {err}")

        logger.info(
            "Cancel order result: retcode=%s, comment=%s",
            result.retcode,
            result.comment,
        )
        return result

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

        TOLERANCE = 1.0
        if side == "BUY":
            if entry_high < ask - TOLERANCE:
                return mt5.ORDER_TYPE_BUY_LIMIT, entry_high
            return mt5.ORDER_TYPE_BUY, ask
        else:
            if entry_low > bid + TOLERANCE:
                return mt5.ORDER_TYPE_SELL_LIMIT, entry_low
            return mt5.ORDER_TYPE_SELL, bid

    def _build_order_request(self, signal: Signal, price: float, offset: int) -> dict:
        signal_entry_low = signal.entry_low - offset if signal.side == "BUY" else signal.entry_low + offset
        signal_entry_high = signal.entry_high - offset if signal.side == "BUY" else signal.entry_high + offset

        order_type, entry_price = self._decide_entry(
            signal.symbol,
            signal.side,
            signal_entry_low,
            signal_entry_high,
        )

        base_price = entry_price if entry_price is not None else price

        action = (
            mt5.TRADE_ACTION_DEAL
            if order_type in (mt5.ORDER_TYPE_BUY, mt5.ORDER_TYPE_SELL)
            else mt5.TRADE_ACTION_PENDING
        )

        mapping = {
            "XAUUSD.S": 0.01,
            "USDJPY.S": 0.04,
        }

        volume = mapping.get(signal.symbol.upper())

        if action == mt5.TRADE_ACTION_PENDING:
            order_type, price = self._ensure_valid_pending_price(
                symbol=signal.symbol,
                side=signal.side,
                order_type=order_type,
                price=base_price,
            )

            if self.is_market_order_type(order_type):
                action = mt5.TRADE_ACTION_DEAL

        request = {
            "action": action,
            "symbol": signal.symbol,
            "volume": volume,
            "type": order_type,
            "price": entry_price if entry_price is not None else price,
            "sl": signal.sl,
            "tp": signal.tp,
            "deviation": 100,
            "magic": 123456789,
            "comment": "Trade via API",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        return request

    def _build_instant_order_request(self, signal: Signal, price: float) -> dict:
        order_type = mt5.ORDER_TYPE_BUY if signal.side.upper() == "BUY" else mt5.ORDER_TYPE_SELL

        mapping = {
            "XAUUSD.S": 0.01,
            "USDJPY.S": 0.04,
        }
        volume = mapping.get(signal.symbol.upper())

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": signal.symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "sl": signal.sl,
            "tp": signal.tp,
            "deviation": 100,
            "magic": 123456789,
            "comment": "Trade via API (instant)",
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
