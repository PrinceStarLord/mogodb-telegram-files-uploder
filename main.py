import asyncio
import logging
import os
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from motor.motor_asyncio import AsyncIOMotorClient
from umongo import Instance, Document, fields
from config import *

logging.basicConfig(level=logging.INFO)

mongo_client = AsyncIOMotorClient(DATABASE_URI)
db = mongo_client[DATABASE_NAME]
instance = Instance.from_db(db)

@instance.register
class Media(Document):
    file_id = fields.StrField(attribute="_id")
    file_ref = fields.StrField(allow_none=True)
    file_name = fields.StrField(required=True)
    file_size = fields.IntField(required=True)
    file_type = fields.StrField(allow_none=True)
    mime_type = fields.StrField(allow_none=True)
    caption = fields.StrField(allow_none=True)

    class Meta:
        collection_name = COLLECTION_NAME

cancel_flag = False

app = Client("media_clone_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.command("savemydb") & filters.user(ADMINS))
async def savemydb_handler(client, message):
    global cancel_flag
    cancel_flag = False
    await message.reply_text("🔄 Cloning started...")

    try:
        skip = int(message.command[1])
        limit = int(message.command[2])
    except (IndexError, ValueError):
        return await message.reply_text("❗ Usage: /savemydb <skip> <limit>")

    total = await Media.count_documents({})
    if skip >= total:
        return await message.reply_text("⚠️ Skip value exceeds total documents.")

    cursor = Media.find().sort('$natural', 1).skip(skip).limit(limit)
    files = await cursor.to_list(length=limit)

    for idx, doc in enumerate(files, start=1):
        if cancel_flag:
            await message.reply_text("❌ Operation canceled.")
            break

        try:
            caption = f"<b>{doc.file_name}</b>" if doc.file_name else None
            await client.send_cached_media(
                chat_id=TARGET_CHAT_ID,
                file_id=doc.file_id,
                caption=caption
            )
            await asyncio.sleep(1.2)
        except FloodWait as fw:
            logging.warning(f"⏳ FloodWait: sleeping for {fw.value}s")
            await asyncio.sleep(fw.value)
            await client.send_cached_media(
                chat_id=TARGET_CHAT_ID,
                file_id=doc.file_id,
                caption=caption
            )
            await asyncio.sleep(1.2)
        except Exception as e:
            logging.exception("❌ Error occurred while sending:")
            await message.reply_text(f"❌ Error: {e}")
            break

    if not cancel_flag:
        await message.reply_text("✅ Cloning completed.")

@app.on_message(filters.command("cancelcopy") & filters.user(ADMINS))
async def cancel_clone(client, message):
    global cancel_flag
    cancel_flag = True
    await message.reply_text("🛑 Cloning canceled by user.")

if __name__ == "__main__":
    print("🚀 Bot is starting...")
    app.run()
