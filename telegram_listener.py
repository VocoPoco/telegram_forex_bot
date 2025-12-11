from pyrogram import Client
from shared.constants import TELEGRAM_APP_ID, TELEGRAM_API_HASH, TELEGRAM_GROUP_ID, LAST_MESSAGE_ID_PATH
from shared.parser import SignalParser
from storage.file_manager import FileManager

import asyncio
from datetime import datetime, timezone
from pathlib import Path
import os
import logging

logger = logging.getLogger(__name__)


def _find_anchor_dir(anchor_name: str) -> Path:
    cur = Path(__file__).resolve().parent
    for p in [cur, *cur.parents]:
        if p.name == anchor_name:
            return p
    return cur


class TelegramListener:
    """
    Listens for new Telegram messages in a specific group and pushes
    parsed trading signals into an async queue.
    """

    def __init__(self, queue, app_name: str = "telegram_bot"):
        self.queue = queue

        anchor = _find_anchor_dir("telegram_bot")
        sessions_dir = Path(os.getenv("SESSION_DIR", anchor / "var" / "sessions")).resolve()
        sessions_dir.mkdir(parents=True, exist_ok=True)

        session_base = sessions_dir / app_name

        self.app = Client(
            str(session_base),
            api_id=TELEGRAM_APP_ID,
            api_hash=TELEGRAM_API_HASH
        )

        self.parser = SignalParser()
        self.file_manager = FileManager(LAST_MESSAGE_ID_PATH=LAST_MESSAGE_ID_PATH)
        self.last_message_id = self.file_manager.read_last_message_id()

        logger.info("TelegramListener initialized with session directory: %s", sessions_dir)
        logger.info("Last saved message ID: %s", self.last_message_id)


    async def run(self):
        """Start the Telegram client and begin polling messages."""
        await self.app.start()
        logger.info("Telegram listener started.")
        await self.poll_channel()


    async def poll_channel(self):
        """Manually fetch the latest message and check for new signals."""
        while True:
            try:
                async for message in self.app.get_chat_history(TELEGRAM_GROUP_ID, limit=1):
                    if message:
                        if self.last_message_id != message.id:
                            logger.info(
                                "New message ID %s detected (last was %s)",
                                message.id, self.last_message_id
                            )

                            self.last_message_id = message.id
                            self.file_manager.write_last_message_id(self.last_message_id)

                            text = (message.text or message.caption or "").strip()

                            if text:
                                logger.info("New message detected: %s", text)

                                signals = self.parser.parse(message.id, message.date, text)
                                if signals and self.queue:
                                    for signal in signals:
                                        logger.info("[SIGNAL RECEIVED] %s", signal)
                                        await self.queue.put(signal)

            except Exception:
                logger.exception("Error while fetching messages")

            await asyncio.sleep(3)


    def print_last_message(self):
        """Debug helper: print last message from test group."""
        self.app.start()
        try:
            messages = self.app.get_chat_history(-1003054653270, limit=1)
            for msg in messages:
                logger.info("Last message: %s", msg.text)
        except Exception:
            logger.exception("Failed to print last message")
        finally:
            self.app.stop()


    def print_dm_id(self):
        """Print user/group IDs in dialogs."""
        try:
            with self.app as app:
                for dialog in app.get_dialogs():
                    print(f"Title: {dialog.chat.title}, ID: {dialog.chat.id}")
        except Exception:
            logger.exception("Failed to print DM IDs")


    def check_group_type(self):
        """Log group type for debugging."""
        self.app.start()
        try:
            chat = self.app.get_chat(-1003054653270)
            logger.info("Chat type: %s", chat.type)
        except Exception:
            logger.exception("Failed to check group type")
        finally:
            self.app.stop()


    def fetch_all_messages_from_date(self, date: datetime = datetime(2025, 4, 25, tzinfo=timezone.utc)):
        """Fetch all channel messages from a given date."""
        self.app.start()
        out = []

        logger.info("Fetching all messages from date: %s", date)

        try:
            messages = self.app.get_chat_history(TELEGRAM_GROUP_ID, limit=0)
            for message in messages:
                if not message.date:
                    continue

                if message.date.replace(tzinfo=timezone.utc) < date:
                    break

                text = (message.text or message.caption or "").strip()
                if text:
                    out.append({
                        "id": message.id,
                        "date": message.date,
                        "text": text
                    })
        except Exception:
            logger.exception("Failed during message fetch_all_messages_from_date")
        finally:
            self.app.stop()

        logger.info("Fetched %d messages from date filter", len(out))
        return out


if __name__ == "__main__":
    listener = TelegramListener(queue=None)
    listener.print_dm_id()
