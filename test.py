import asyncio
from asyncio import Queue

from mt_bot.trade_executioner import TradeExecutioner
from telegram_listener import TelegramListener
from shared.parser import parse_signal
from pyrogram import Client, filters
from shared.constants import TELEGRAM_APP_ID, TELEGRAM_API_HASH, TELEGRAM_GROUP_ID


async def main():
    signal_queue = asyncio.Queue()

    listener = TelegramListener(signal_queue)
    trade_executor = TradeExecutioner()

    async def trader_loop():
        """Continually listen for signals and execute trades."""
        _ = 0
        while _ in range(1):
            _ = _ + 1

            text = """XAUUSD BUY (4037.5-4038.5)

            TP 4045

            STOP LOSS: 4000"""
            sig = parse_signal(text)
            if sig is None:
                print(f"Failed to parse signal: {text}")
                continue
            print(f"Handling signal: {sig}")
            trade_executor.execute_trade(sig)

    await asyncio.gather(
        # asyncio.to_thread(listener.run),  
        trader_loop(),
    )

def print_last_message():
    # app = Client("telegram_bot", api_id=TELEGRAM_APP_ID, api_hash=TELEGRAM_API_HASH)
    # app.start()
    # messages = app.get_chat_history(-1002016753445, limit=1)
    # for msg in messages:
    #     print(f"Last message: {msg.text}")
    # app.stop()
    with Client("telegram_bot", api_id=TELEGRAM_APP_ID, api_hash=TELEGRAM_API_HASH) as app:
        for dialog in app.get_dialogs():
            print(f"{dialog.chat.title}: {dialog.chat.id}")


if __name__ == "__main__":
    print_last_message()