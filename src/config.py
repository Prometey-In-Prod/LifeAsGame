import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DATABASE_URL = os.environ["DATABASE_URL"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
OWNER_CHAT_ID = int(os.environ["OWNER_CHAT_ID"])
TZ = os.environ.get("TZ", "Europe/Moscow")

# Необязательный прокси для доступа к Telegram (если API заблокирован).
# Пример: socks5://127.0.0.1:10808  (локальный SOCKS от Xray-клиента)
PROXY_URL = os.environ.get("PROXY_URL") or None
