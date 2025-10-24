from dotenv import load_dotenv
import os

load_dotenv()

# Telegram API configuration
TELEGRAM_APP_ID = os.getenv("TELEGRAM_APP_ID")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")

# Telegram group configuration
TELEGRAM_GROUP_ID = int(os.getenv("TELEGRAM_GROUP_ID"))
TELEGRAM_GROUP_NAME = os.getenv("TELEGRAM_GROUP_NAME")

# MetaTrader 5 configuration
MT5_ACCOUNT=int(os.getenv("MT5_ACCOUNT"))
MT5_SERVER=os.getenv("MT5_SERVER")
MT5_PASSWORD=os.getenv("MT5_PASSWORD")

# MetaTrader 5 Demo configuration
MT5_ACCOUNT_DEMO=int(os.getenv("MT5_ACCOUNT_DEMO"))
MT5_SERVER_DEMO=os.getenv("MT5_SERVER_DEMO")
MT5_PASSWORD_DEMO=os.getenv("MT5_PASSWORD_DEMO")


# Market order configuration
MAX_SLIPPAGE_PT=os.getenv("MAX_SLIPPAGE_PT")
MAGIC_NUMBER=os.getenv("MAGIC_NUMBER")
DEFAULT_LOT_SIZE=float(os.getenv("DEFAULT_LOT_SIZE", "0.01"))
DEFAULT_SYMBOL=os.getenv("DEFAULT_SYMBOL", "XAUUSD.s")

LAST_MESSAGE_FILE = "last_message_id.txt"