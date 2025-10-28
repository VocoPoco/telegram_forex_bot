from datetime import datetime, timezone
from asyncio import Queue
from storage.file_manager import FileManager
from telegram_listener import TelegramListener
    
if __name__ == "__main__":
    listener = TelegramListener(queue=None)
    file_manager = FileManager()
    msgs = listener.fetch_all_messages_from_date(datetime(2025,4,25,tzinfo=timezone.utc))
    file_manager.save_json(msgs)
    print(f"Saved {len(msgs)} messages.")
