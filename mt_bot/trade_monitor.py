import asyncio
from models.trade_handle import TradeHandle
from models.signal import Signal
from mt_bot.mt5_client import MT5Client
from storage.file_manager import FileManager
from datetime import datetime, timezone
from storage.google_sheet_client import GoogleSheetsClient


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

    def _load_existing_rows(self):
        try:
            return self.file_manager.load_json("var/signal_results.json")
        except FileNotFoundError:
            return []

    async def monitor_trade(self, trade: TradeHandle):
        """Run until this specific trade is closed, then log it."""
        ticket = trade.ticket
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
            break

    def _build_row_from_deal(self, trade: TradeHandle, deal) -> dict:
        signal = trade.signal
        hit_time = datetime.fromtimestamp(deal.time, tz=timezone.utc)
        close_price = deal.price
        side = signal.side.upper()

        if side == "BUY":
            result = "TP" if close_price >= signal.tp else "SL"
        else:
            result = "TP" if close_price <= signal.tp else "SL"

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

    def _flush_to_disk(self):
        self.file_manager.save_results_to_json(self.rows)

        last = self.rows[-1] 
        
        self.sheets.worksheet.insert_row([
            last["message_id"],
            last["symbol"],
            last["direction"],
            last["entry_price_signal"],
            last["take_profit"],
            last["stop_loss"],
            last["market_price_at_signal"],
            last["open_timestamp"].isoformat() if last["open_timestamp"] else "",
            last["close_timestamp"].isoformat() if last["close_timestamp"] else "",
            last["result"],
        ], index=2)