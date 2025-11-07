from pyrogram import Client
from shared.constants import TELEGRAM_APP_ID, TELEGRAM_API_HASH, TELEGRAM_GROUP_ID, LAST_MESSAGE_ID_PATH
from shared.parser import SignalParser
from storage.file_manager import FileManager

import asyncio
from datetime import datetime, timezone
from pathlib import Path
import os


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

        # Temporary solution to find the anchor directory
        anchor = _find_anchor_dir("telegram_bot")
        
        sessions_dir = Path(os.getenv("SESSION_DIR", anchor / "var" / "sessions")).resolve()
        sessions_dir.mkdir(parents=True, exist_ok=True)

        session_base = sessions_dir / app_name

        self.app = Client(str(session_base), api_id=TELEGRAM_APP_ID, api_hash=TELEGRAM_API_HASH)
        self.parser = SignalParser()
        self.file_manager = FileManager(LAST_MESSAGE_ID_PATH=LAST_MESSAGE_ID_PATH)
        self.last_message_id = self.file_manager.read_last_message_id()


    async def run(self):
        """Start the Telegram client and begin polling messages."""
        await self.app.start()
        print("Telegram listener started.")
        await self.poll_channel()


    async def poll_channel(self):
        """Manually fetch the latest message and check for new signals."""
        while True:
            try:
                async for message in self.app.get_chat_history(TELEGRAM_GROUP_ID, limit=1):
                    if message:
                        if self.last_message_id != message.id:
                            print(f"New message ID {message.id} detected (last was {self.last_message_id})")
                            self.last_message_id = message.id 
                            self.file_manager.write_last_message_id(self.last_message_id)

                            text = (message.text or message.caption or "").strip()

                            if text:  
                                print(f"New message detected: {text}")
                                sig = self.parser.parse(message.id, message.date, text)
                                if sig and self.queue:
                                    print(f"[SIGNAL RECEIVED] {sig}")
                                    await self.queue.put(sig) 

            except Exception as e:
                print(f"Error while fetching messages: {e}")

            await asyncio.sleep(3)



    def print_last_message(self):
        # Forex testing signals id group: -1003100636902
        # Forex channel testL -1003054653270
        self.app.start()
        messages = self.app.get_chat_history(-1003054653270, limit=1)
        for msg in messages:
            print(f"Last message: {msg.text}")
        self.app.stop()


    def print_dm_id(self):
        with self.app as app:
            for dialog in app.get_dialogs():
                print(f"{dialog.chat.title}: {dialog.chat.id}")


    def check_group_type(self):
        self.app.start()
        chat = self.app.get_chat(-1003054653270)
        print(f"Chat type: {chat.type}")
        self.app.stop()


    def fetch_all_messages_from_date(self, date: datetime = datetime(2025, 4, 25, tzinfo=timezone.utc)):
        self.app.start()
        out = []
        try:
            messages = self.app.get_chat_history(TELEGRAM_GROUP_ID, limit=0)
            for message in messages:
                if not message.date:
                    continue
                if message.date.replace(tzinfo=timezone.utc) < date:
                    break
                text = (message.text or message.caption or "").strip()
                if text:
                    out.append({"id": message.id, "date": message.date, "text": text})
        finally:
            self.app.stop()
        return out


if __name__ == "__main__":
    listener = TelegramListener(queue=None)
    listener.print_last_message()
    listener.check_group_type()
    listener.print_dm_id()