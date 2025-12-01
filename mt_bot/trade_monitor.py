import asyncio
from datetime import datetime, timezone
import logging

from models.trade_handle import TradeHandle
from mt_bot.mt5_client import MT5Client
from storage.file_manager import FileManager
from storage.google_sheet_client import GoogleSheetsClient

logger = logging.getLogger(__name__)


class TradeMonitor:
    def __init__(self, mt5_client: MT5Client):
        self.mt5 = mt5_client
        self.file_manager = FileManager()
        self.rows = self._load_existing_rows()

        self.sheets = GoogleSheetsClient(
            credentials_path="var/google_sheet_account/service_account.json",
            spreadsheet_name="signal_results",
            worksheet_name="Results",
        )

        logger.info(
            "TradeMonitor initialized. Loaded %s existing rows from JSON.",
            len(self.rows),
        )

    def _load_existing_rows(self):
        try:
            data = self.file_manager.load_json("var/signal_results.json")
            if not isinstance(data, list):
                logger.warning(
                    "signal_results.json did not contain a list. Wrapping into list."
                )
                return [data]
            return data
        except FileNotFoundError:
            logger.info("signal_results.json not found, starting with empty rows.")
            return []

    async def monitor_trade(self, trade: TradeHandle):
        """
        Run until this specific trade is closed, then log it.
        """
        ticket = trade.ticket
        logger.info(
            "Starting monitor_trade for position ticket=%s, symbol=%s, side=%s, pending_order_ticket=%s",
            ticket,
            trade.signal.symbol,
            trade.signal.side,
            getattr(trade, "pending_order_ticket", None),
        )

        while True:
            positions = self.mt5.get_positions(ticket=ticket)
            if positions:
                await asyncio.sleep(10)
                continue

            history = self.mt5.get_history_deals(position_id=ticket)
            if not history:
                await asyncio.sleep(10)
                continue

            closing_deal = history[-1]
            row = self._build_row_from_deal(trade, closing_deal)
            self.rows.append(row)
            self._flush_to_disk()

            pending_ticket = getattr(trade, "pending_order_ticket", None)
            if row["result"] == "TP" and pending_ticket is not None:
                logger.info(
                    "Trade hit TP. Checking for pending order %s to cancel.",
                    pending_ticket,
                )

                try:
                    orders = self.mt5.get_orders(ticket=pending_ticket)
                except AttributeError:
                    logger.error(
                        "MT5Client has no get_orders() method. "
                        "You must implement it to manage pending orders."
                    )
                    orders = ()

                if orders:
                    try:
                        cancel_result = self.mt5.cancel_pending_order(pending_ticket)
                        logger.info(
                            "Cancelled pending order %s, retcode=%s, comment=%s",
                            pending_ticket,
                            getattr(cancel_result, "retcode", None),
                            getattr(cancel_result, "comment", None),
                        )
                    except Exception:
                        logger.exception(
                            "Failed to cancel pending order %s after TP",
                            pending_ticket,
                        )
                else:
                    logger.info(
                        "No live pending order found for ticket=%s; nothing to cancel.",
                        pending_ticket,
                    )

            logger.info(
                "Finished monitoring ticket=%s (result=%s)",
                ticket,
                row["result"],
            )
            break

    def _build_row_from_deal(self, trade: TradeHandle, deal) -> dict:
        signal = trade.signal

        hit_time = datetime.fromtimestamp(deal.time, tz=timezone.utc)
        close_price = deal.price

        result = self._get_result_of_signal(signal, close_price)

        return {
            "message_id": signal.message_id,
            "symbol": signal.symbol,
            "direction": signal.side,
            "entry_price_signal": trade.signal_entry_price,
            "take_profit": signal.tp,
            "stop_loss": signal.sl,
            "market_price_at_signal": trade.market_price_at_signal,
            "open_timestamp": signal.created_at,
            "close_timestamp": hit_time,
            "result": result,
        }
    
    def _get_result_of_signal(self, signal, close_price: float) -> str:
        TOLERANCE = 1.0 
        diff = abs(close_price - signal.tp)

        if diff <= TOLERANCE:
            return "TP"
        else:
            return "SL"

    def _flush_to_disk(self):
        self.file_manager.save_results_to_json(self.rows)

        last = self.rows[-1]

        self.sheets.worksheet.insert_row(
            [
                last["message_id"],
                last["symbol"],
                last["direction"],
                last["entry_price_signal"],
                last["take_profit"],
                last["stop_loss"],
                last["market_price_at_signal"],
                last["open_timestamp"].isoformat()
                if last["open_timestamp"]
                else "",
                last["close_timestamp"].isoformat()
                if last["close_timestamp"]
                else "",
                last["result"],
            ],
            index=2,
        )
