from domain.models import Signal, TradeResult
from mt_bot.mt5_client import MT5Client
from shared.constants import DEFAULT_SYMBOL, MT5_ACCOUNT, MT5_PASSWORD, MT5_SERVER
import logging

logger = logging.getLogger(__name__)


class TradeExecutioner:
    def __init__(self):
        self.trader = MT5Client(MT5_ACCOUNT, MT5_PASSWORD, MT5_SERVER)
        logger.info("TradeExecutioner initialized with MT5 account %s", MT5_ACCOUNT)

    def execute_trade(self, signal: Signal) -> TradeResult:
        """Execute a trade based on the parsed signal."""
        side = signal.side
        tp = signal.tp
        sl = signal.sl

        logger.info(
            "Executing trade: %s %s | TP=%s SL=%s (message_id=%s)",
            signal.symbol,
            side,
            tp,
            sl,
            signal.message_id,
        )

        with self.trader:
            try:
                pending_order_result = self.trader.place_market_order(signal)
                logger.info(
                    "Pending trade sent: order_id=%s deal_id=%s comment=%s",
                    pending_order_result.order_id,
                    pending_order_result.deal_id,
                    pending_order_result.comment,
                )
            except Exception:
                logger.exception("Error while sending PENDING trade for signal %s", signal)
                raise

            try:
                instant_order_result = self.trader.place_instant_market_order(signal)
                logger.info(
                    "Instant trade sent: order_id=%s deal_id=%s comment=%s",
                    instant_order_result.order_id,
                    instant_order_result.deal_id,
                    instant_order_result.comment,
                )
            except Exception:
                logger.exception(
                    "Error while sending INSTANT trade for signal %s", signal
                )
                raise

        return pending_order_result
