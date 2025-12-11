from models.signal import Signal
from models.trade_result import TradeResult
from models.trade_handle import TradeHandle
from mt_bot.mt5_client import MT5Client
from shared.constants import MT5_ACCOUNT
import logging

logger = logging.getLogger(__name__)


class TradeExecutioner:
    def __init__(self, mt5_client: MT5Client):
        self.trader = mt5_client
        logger.info("TradeExecutioner initialized with MT5 account %s", MT5_ACCOUNT)

    def execute_trade(self, signal: Signal) -> TradeHandle | None:
        """
        Entry point for executing signal trades.
        Supports:
          - TP1 → instant order only
          - TP2+ → multiple pending orders
        """
        logger.info(
            "Executing trade logic: symbol=%s tp_index=%s offsets=%s",
            signal.symbol, signal.tp_index, signal.sub_entry_offsets
        )

        if signal.tp_index == 1:
            return self._execute_instant_trade(signal)
        
        return self._execute_pending_trades(signal)
    

    def _execute_instant_trade(self, signal: Signal) -> TradeHandle | None:
        """Instant trade logic: using the first TP of the signal."""
        
        result = self.trader.place_instant_market_order(signal)
        if not result.success:
            logger.warning("Instant TP order failed")
            return None
        
        logger.info(
            "Instant order sent: order_id=%s deal_id=%s comment=%s",
            result.order_id,
            result.deal_id,
            result.comment,
        )

        position_ticket = self.trader.get_position_ticket(signal.symbol)
        if position_ticket is None:
            logger.warning("Could not retrieve instant order ticket")
            return None
        
        handle = TradeHandle(
            ticket=position_ticket,
            signal=signal,
            executed_price=result.price,
            signal_entry_price=result.price,
            market_price_at_signal=result.price,
            pending_order_tickets=[],
            opened_at=result.executed_at,
            is_parent=True,
        )
        
        return handle
    
    def _execute_pending_trades(self, signal: Signal) -> TradeHandle | None:
        """Multiple pending limit orders for second tp of the signal."""
        
        pending_tickets = []
        
        OFFSETS = [0, 5, 10]
        for offset in OFFSETS:
            logger.info("Placing pending order at range %s - %s", signal.entry_low - offset, signal.entry_high - offset)
            
            result = self.trader.place_pending_order(
                signal=signal,
                offset=offset,
            )
            logger.info(
                "Pending order sent: order_id=%s deal_id=%s comment=%s",
                result.order_id,
                result.deal_id,
                result.comment,
            )

            if result and result.success:
                pending_tickets.append(result.order_id)
        
        if not pending_tickets:
            logger.error("All pending orders failed for TP2+")
            return None
        
        handle = TradeHandle(
            ticket=None,
            signal=signal,
            executed_price=None,
            signal_entry_price=None,
            market_price_at_signal=None,
            pending_order_ticket=None,
            pending_order_tickets=pending_tickets,
            opened_at=result.executed_at,
            is_parent=False,
        )
        
        return handle
