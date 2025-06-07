import os
import re
import traceback
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from yt_dlp import YoutubeDL
from aiohttp import web
from datetime import datetime
from dotenv import load_dotenv
from aiogram.utils.executor import start_webhook

load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = 742572547

WEBHOOK_HOST = f"https://{os.getenv('WEBHOOK_DOMAIN')}"  # e.g., yourproject.up.railway.app
WEBHOOK_PATH = f"/webhook/{API_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

def log_download(user: types.User, format_type: str, title: str, url: str):
    with open("downloads.log", "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now()}] {user.full_name} ({user.id}) → {format_type.upper()}\n")
        f.write(f"Title: {title}\n")
        f.write(f"URL: {url}\n\n")

@dp.errors_handler()
async def global_error_handler(update, error):
    print("🔥 Error caught:", repr(error))
    return True

@dp.message_handler(commands=["start"])
async def send_welcome(message: types.Message):
    print(f"/start from {message.from_user.full_name} ({message.from_user.id})")
    await message.reply("👋 Сәлем, маған Youtube сілтемені жібер")

@dp.message_handler(lambda m: "youtube.com" in m.text or "youtu.be" in m.text)
async def handle_youtube_link(message: types.Message):
    link = message.text.strip()
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("🎵 Музыкасы керек (mp3)", callback_data=f"mp3|{link}"),
        InlineKeyboardButton("🎥 Видеосы керек (mp4)", callback_data=f"mp4|{link}")
    )
    await message.reply("Сізге қай формат керек:", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data.startswith("mp3") or c.data.startswith("mp4"))
async def process_download(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    format_type, url = callback_query.data.split("|")
    user_id = callback_query.from_user.id

    output_template = f"{user_id}_video.%(ext)s"
    ydl_opts = {
        "outtmpl": output_template,
        "quiet": True,
        "noplaylist": True
    }

    if format_type == "mp3":
        ydl_opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "64",
            }]
        })
    else:
        ydl_opts.update({
            "format": "bestvideo[height<=360]+bestaudio/best/best",
            "merge_output_format": "mp4",
            "postprocessors": [{
                "key": "FFmpegVideoConvertor",
                "preferedformat": "mp4"
            }]
        })

    try:
        await bot.send_message(user_id, "⏳ Тартылуда, күте тұрыңыз...")

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            base_filename = ydl.prepare_filename(info)

        title = info.get("title", "video")
        safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
        ext = ".mp3" if format_type == "mp3" else ".mp4"
        temp_filename = os.path.splitext(base_filename)[0] + ext
        final_filename = f"{safe_title}{ext}"

        if not os.path.exists(temp_filename):
            raise FileNotFoundError(f"Downloaded file not found: {temp_filename}")

        os.rename(temp_filename, final_filename)

        await bot.send_chat_action(user_id, types.ChatActions.UPLOAD_DOCUMENT)
        await bot.send_document(user_id, types.InputFile(final_filename))
        os.remove(final_filename)

        await bot.send_message(
            ADMIN_ID,
            f"📅 {callback_query.from_user.full_name} ({callback_query.from_user.id})\n"
            f"🎮 {format_type.upper()} — {title}\n🔗 {url}"
        )

    except Exception as e:
        error_text = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
        await bot.send_message(user_id, f"⚠️ Қате болды:\n{str(e)}")
        print("Full Error:\n", error_text)

# === Webhook Setup ===
async def on_startup(dp):
    print("🚀 Starting bot and setting webhook...")
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(dp):
    print("💤 Shutting down bot...")
    await bot.delete_webhook()

def main():
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, dp.handler)
    return app

if __name__ == '__main__':
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 3000))
    )