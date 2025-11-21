from models.signal import Signal
from models.trade_result import TradeResult
from models.trade_handle import TradeHandle
from mt_bot.mt5_client import MT5Client
from shared.constants import MT5_ACCOUNT_DEMO, MT5_PASSWORD_DEMO, MT5_SERVER_DEMO
import logging

logger = logging.getLogger(__name__)


class TradeExecutioner:
    def __init__(self, mt5_client: MT5Client):
        self.trader = mt5_client
        logger.info("TradeExecutioner initialized with MT5 account %s", MT5_ACCOUNT_DEMO)

    def execute_trade(self, signal: Signal) -> TradeHandle | None:
        """
        Execute a trade based on the parsed signal.
        Returns a TradeHandle for monitoring, or None on failure.
        """
        logger.info(
            "Executing trade: %s %s | TP=%s SL=%s (message_id=%s)",
            signal.symbol,
            signal.side,
            signal.tp,
            signal.sl,
            signal.message_id,
        )

        # 1) market price at "signal time" (approx)
        market_price = self.trader.get_market_price(signal.symbol, signal.side)
        if market_price is None:
            logger.error("No market price available for %s", signal.symbol)
            return None

        # 2) decide entry type + signal-entry price using existing _decide_entry
        order_type, entry_price_candidate = self.trader._decide_entry(
            signal.symbol,
            signal.side,
            signal.entry_low,
            signal.entry_high,
        )
        is_immediate = self.trader.is_market_order_type(order_type)
        signal_entry_price = entry_price_candidate or market_price

        logger.info(
            "Entry decision for %s: %s (signal_entry_price=%s)",
            signal.symbol,
            "IMMEDIATE (market)" if is_immediate else "PENDING (limit/stop)",
            signal_entry_price,
        )

        # 3) place main (pending/market) order
        pending_result = self._place_pending_order(signal)
        if pending_result is None:
            return None

        # 4) optional instant order
        instant_result = self._place_instant_order_if_needed(signal, is_immediate)

        # 5) choose which TradeResult we monitor
        chosen_result = self._choose_main_result(pending_result, instant_result)
        if chosen_result is None:
            logger.warning("No valid trade result, skipping monitor.")
            return None

        # 6) find POSITION ticket while client is connected
        position_ticket = self.trader.find_position_ticket(symbol=signal.symbol)
        if position_ticket is None:
            logger.warning(
                "Could not find position for symbol=%s after order, skipping monitor.",
                signal.symbol,
            )
            return None

        # 7) build TradeHandle
        trade_handle = self._build_trade_handle(
            signal=signal,
            chosen_result=chosen_result,
            position_ticket=position_ticket,
            signal_entry_price=signal_entry_price,
            market_price_at_signal=market_price,
        )

        return trade_handle

    def _place_pending_order(self, signal: Signal) -> TradeResult | None:
        try:
            result: TradeResult = self.trader.place_market_order(signal)
            logger.info(
                "Pending trade sent: order_id=%s deal_id=%s comment=%s",
                result.order_id,
                result.deal_id,
                result.comment,
            )
            if not result.success:
                logger.warning(
                    "Pending order not successful: order_id=%s, comment=%s",
                    result.order_id,
                    result.comment,
                )
                return None
            return result
        except Exception:
            logger.exception("Error while sending PENDING trade for signal %s", signal)
            return None

    def _place_instant_order_if_needed(
        self,
        signal: Signal,
        is_immediate: bool,
    ) -> TradeResult | None:
        if is_immediate:
            return None

        try:
            result: TradeResult = self.trader.place_instant_market_order(signal)
            logger.info(
                "Instant trade sent: order_id=%s deal_id=%s comment=%s",
                result.order_id,
                result.deal_id,
                result.comment,
            )
            if not result.success:
                logger.warning(
                    "Instant order not successful: order_id=%s, comment=%s",
                    result.order_id,
                    result.comment,
                )
                return None
            return result
        except Exception:
            logger.exception("Error while sending INSTANT trade for signal %s", signal)
            return None

    def _choose_main_result(
        self,
        pending_result: TradeResult | None,
        instant_result: TradeResult | None,
    ) -> TradeResult | None:
        chosen = instant_result or pending_result
        if chosen is None or not chosen.success or chosen.order_id is None:
            return None
        return chosen

    def _build_trade_handle(
        self,
        signal: Signal,
        chosen_result: TradeResult,
        position_ticket: int,
        signal_entry_price: float,
        market_price_at_signal: float,
    ) -> TradeHandle:
        executed_price = chosen_result.price or signal_entry_price

        handle = TradeHandle(
            ticket=position_ticket,
            signal=signal,
            signal_entry_price=signal_entry_price,
            executed_price=executed_price,
            opened_at=chosen_result.executed_at,
            market_price_at_signal=market_price_at_signal,
        )

        logger.info(
            "Created TradeHandle: ticket=%s, symbol=%s, signal_entry=%s, executed=%s",
            handle.ticket,
            handle.signal.symbol,
            handle.signal_entry_price,
            handle.executed_price,
        )

        return handle
