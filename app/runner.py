import asyncio
from asyncio import Queue
from mt_bot.trade_executioner import TradeExecutioner
from telegram_listener import TelegramListener
import logging
from logging.handlers import RotatingFileHandler


def setup_logging():
    log_format = "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s"

    file_handler = RotatingFileHandler(
        "logs/bot.log",
        maxBytes=5_000_000,
        backupCount=5
    )
    file_handler.setFormatter(logging.Formatter(log_format))

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format))

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


logger = logging.getLogger(__name__)


async def run_trader_process(signal_queue: Queue):
    """Run the trading algorithm asynchronously."""
    trade_executor = TradeExecutioner()
    logger.info("TradeExecutioner initialised in trader process")

    async def trader_loop():
        """Continually listen for signals and execute trades."""
        while True:
            sig = await signal_queue.get()
            if sig is None:
                logger.warning("Received invalid signal: %s", sig)
                continue

            logger.info("Handling signal: %s", sig)
            try:
                trade_executor.execute_trade(sig)
                logger.info("Executed trade for signal: %s", sig)
            except Exception:
                logger.exception("Error while executing trade for signal: %s", sig)

    await trader_loop()

async def run_listener_process(signal_queue: Queue):
    """Run Pyrogram's Telegram listener asynchronously."""
    logger.info("Starting Telegram listener...")
    listener = TelegramListener(signal_queue)
    try:
        await listener.run()
    except Exception:
        logger.exception("Telegram listener crashed")

async def main():
    signal_queue = asyncio.Queue()

    logger.info("Creating listener and trader tasks")
    listener_task = asyncio.create_task(run_listener_process(signal_queue))
    trader_task = asyncio.create_task(run_trader_process(signal_queue))

    await asyncio.gather(listener_task, trader_task)

if __name__ == "__main__":
    setup_logging()
    logger.info("Starting processes...")
    asyncio.run(main())
