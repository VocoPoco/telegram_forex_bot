from pyrogram import Client, filters
from shared.constants import TELEGRAM_APP_ID, TELEGRAM_API_HASH, TELEGRAM_GROUP_ID
from shared.parser import parse_signal
import time
import asyncio

class TelegramListener:
    """
    Listens for new Telegram messages in a specific group and pushes
    parsed trading signals into an async queue.
    """

    def __init__(self, queue, app_name: str = "telegram_bot"):
        self.queue = queue
        self.app = Client(app_name, api_id=TELEGRAM_APP_ID, api_hash=TELEGRAM_API_HASH)
        print("Telegram client initialized.")
        self.last_message_id = None

        # @self.app.on_message(filters.chat(TELEGRAM_GROUP_ID) & filters.channel)
        # async def on_channel_post(_, message):
        #     text = (message.text or message.caption or "").strip()
        #     if not text:
        #         return

        #     dt = message.date.strftime("%Y-%m-%d %H:%M:%S")
        #     print(f"[POST {dt}] chat={message.chat.id} title={message.chat.title!r} text={text!r}")

        #     sig = parse_signal(text)
        #     if sig and self.queue:
        #         print(f"[SIGNAL RECEIVED] {sig}")
        #         self.queue.put(sig)

        # @self.app.on_edited_message(filters.chat(TELEGRAM_GROUP_ID) & filters.channel)
        # async def on_channel_edit(_, message):
        #     text = (message.text or message.caption or "").strip()
        #     if not text:
        #         return
        #     dt = message.edit_date.strftime("%Y-%m-%d %H:%M:%S") if message.edit_date else message.date.strftime("%Y-%m-%d %H:%M:%S")
        #     print(f"[EDIT {dt}] chat={message.chat.id} title={message.chat.title!r} text={text!r}")

        #     sig = parse_signal(text)
        #     if sig and self.queue:
        #         self.queue.put(sig)

        # @self.app.on_raw_update()
        # async def _raw(_, update, users, chats):
        #     # Look for UpdateNewChannelMessage / UpdateEditChannelMessage
        #     print("RAW:", type(update))
        
        # @self.app.on_message()
        # async def debug_all_messages(client, message):
        #     print(f"Incoming: {message.chat.id} | {message.from_user} | {message.text}")


    async def poll_channel(self):
        """Manually fetch the latest message and check for new signals."""
        while True:
            try:
                async for message in self.app.get_chat_history(TELEGRAM_GROUP_ID, limit=1):
                    if message:
                        if self.last_message_id != message.id:
                            self.last_message_id = message.id 
                            text = (message.text or message.caption or "").strip()

                            if text:  
                                print(f"New message detected: {text}")
                                sig = parse_signal(text)
                                if sig and self.queue:
                                    print(f"[SIGNAL RECEIVED] {sig}")
                                    await self.queue.put(sig) 

            except Exception as e:
                print(f"Error while fetching messages: {e}")

            await asyncio.sleep(3)

    async def run(self):
        """Start the Telegram client and begin polling messages."""
        await self.app.start()
        print("Telegram listener started.")
        await self.poll_channel()


    def print_last_message(self):
        # Forex testing signals id group: -1003100636902
        # Forex channel testL -1003054653270
        app = Client("telegram_bot", api_id=TELEGRAM_APP_ID, api_hash=TELEGRAM_API_HASH)
        app.start()
        messages = app.get_chat_history(-1003054653270, limit=1)
        for msg in messages:
            print(f"Last message: {msg.text}")
        app.stop()

    def print_dm_id(self):
        with Client("telegram_bot", api_id=TELEGRAM_APP_ID, api_hash=TELEGRAM_API_HASH) as app:
            for dialog in app.get_dialogs():
                print(f"{dialog.chat.title}: {dialog.chat.id}")

    def check_group_type(self):
        app = Client("telegram_bot", api_id=TELEGRAM_APP_ID, api_hash=TELEGRAM_API_HASH)
        app.start()
        chat = app.get_chat(-1003054653270)
        print(f"Chat type: {chat.type}")
        app.stop()

if __name__ == "__main__":
    listener = TelegramListener(queue=None)
    listener.print_last_message()
    listener.check_group_type()
    listener.print_dm_id()