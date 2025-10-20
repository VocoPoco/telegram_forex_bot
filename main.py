import asyncio
from asyncio import Queue
from mt_bot.trade_executioner import TradeExecutioner
from telegram_listener import TelegramListener

async def run_trader_process(signal_queue):
    """Run the trading algorithm asynchronously."""
    trade_executor = TradeExecutioner()

    async def trader_loop():
        """Continually listen for signals and execute trades."""
        while True:
            sig = await signal_queue.get()
            if sig is None:
                print(f"Failed to parse signal: {sig}")
                continue
            print(f"Handling signal: {sig}")
            trade_executor.execute_trade(sig)

    await trader_loop()

async def run_listener_process(signal_queue):
    """Run Pyrogram's Telegram listener asynchronously."""
    print("Starting Telegram listener...")
    listener = TelegramListener(signal_queue)
    await listener.run() 

async def main():
    signal_queue = asyncio.Queue()

    listener_task = asyncio.create_task(run_listener_process(signal_queue))
    trader_task = asyncio.create_task(run_trader_process(signal_queue))

    await asyncio.gather(listener_task, trader_task)

if __name__ == "__main__":
    print("Starting processes...")
    asyncio.run(main()) 
