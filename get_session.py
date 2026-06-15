from telethon.sync import TelegramClient
from telethon.sessions import StringSession

API_ID = 34989469
API_HASH = '3d8e9f2619d7d993d1f943181eb4e8c3'

with TelegramClient(StringSession(), API_ID, API_HASH) as client:
    print("\n✅ YOUR STRING SESSION IS BELOW (KEEP IT SECRET):\n")
    print(client.session.save())