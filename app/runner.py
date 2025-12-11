import asyncio
from asyncio import Queue
from mt_bot.trade_executioner import TradeExecutioner
from mt_bot.trade_monitor import TradeMonitor
from telegram_listener import TelegramListener
import logging
import sys
from logging.handlers import RotatingFileHandler
from mt_bot.mt5_client import MT5Client


def setup_logging():
    log_format = "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s"

    file_handler = RotatingFileHandler(
        "logs/bot.log",
        maxBytes=5_000_000,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(log_format))

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format))

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


logger = logging.getLogger(__name__)


async def run_trader_process(signal_queue: Queue, monitor_queue: Queue, mt5_client: MT5Client):
    """Run the trading algorithm asynchronously."""
    trade_executor = TradeExecutioner(mt5_client)
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
                trade_handle = trade_executor.execute_trade(sig)
                logger.info("Executed trade for signal: %s", sig)

                if trade_handle is not None:
                    await monitor_queue.put(trade_handle)
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

async def run_monitor_process(monitor_queue: Queue, mt5_client: MT5Client):
    """Run TradeMonitor that watches trades until they close."""
    logger.info("Starting TradeMonitor loop...")

    monitor = TradeMonitor(mt5_client)

    async def monitor_loop():
        while True:
            trade_handle = await monitor_queue.get()
            asyncio.create_task(monitor.monitor_trade(trade_handle))

    try:
        await monitor_loop()
    except Exception:
        logger.exception("TradeMonitor crashed")

async def main(mt5_client: MT5Client):
    signal_queue = asyncio.Queue()
    monitor_queue = asyncio.Queue()

    logger.info("Creating listener and trader tasks")
    listener_task = asyncio.create_task(run_listener_process(signal_queue))
    trader_task = asyncio.create_task(run_trader_process(signal_queue, monitor_queue, mt5_client))
    monitor_task = asyncio.create_task(run_monitor_process(monitor_queue, mt5_client))

    await asyncio.gather(listener_task, trader_task, monitor_task)

if __name__ == "__main__":
    setup_logging()
    logger.info("Starting processes...")

    with MT5Client() as mt5_client:
        asyncio.run(main(mt5_client))