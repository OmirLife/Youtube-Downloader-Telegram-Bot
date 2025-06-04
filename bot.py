import os
import re
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from yt_dlp import YoutubeDL
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
import os
import traceback
from aiogram.dispatcher.webhook import get_new_configured_app
from aiohttp import web

API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = 742572547

WEBHOOK_HOST = "https://youtube-downloader-telegram-bot-production.up.railway.app"
WEBHOOK_PATH = f"/webhook/{API_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = int(os.getenv("PORT", 3000))

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

def log_download(user: types.User, format_type: str, title: str, url: str):
    with open("downloads.log", "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now()}] {user.full_name} ({user.id}) → {format_type.upper()}\n")
        f.write(f"Title: {title}\n")
        f.write(f"URL: {url}\n\n")


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.reply("👋 Сәлем, маған Youtube сілтемені жібер")

@dp.message_handler(lambda message: "youtube.com" in message.text or "youtu.be" in message.text)
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
    format_type, url = callback_query.data.split('|')
    user_id = callback_query.from_user.id

    output_template = f"{user_id}_video.%(ext)s"
    ydl_opts = {
        'outtmpl': output_template,
        'quiet': True,
        'noplaylist': True,
        'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept-Language': 'en-US,en;q=0.9',
        },
    }

    if format_type == 'mp3':
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '64',
            }]
        })
    else:
        ydl_opts.update({
            'format': 'bestvideo[height<=360]+bestaudio/best/best',
            'merge_output_format': 'mp4',
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4'
            }]
        })

    try:
        await bot.send_message(user_id, "⏳ Тартылуда, күте тұрыңыз...")

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            base_filename = ydl.prepare_filename(info)

        # Санитарлық атау
        title = info.get('title', 'video')
        log_download(callback_query.from_user, format_type, title, url)
        await bot.send_message(
            ADMIN_ID,
            f"📥 {callback_query.from_user.full_name} ({callback_query.from_user.id})\n"
            f"🎞 {format_type.upper()} — {title}\n🔗 {url}"
        )
        safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
        original_ext = '.mp3' if format_type == 'mp3' else '.mp4'
        temp_filename = os.path.splitext(base_filename)[0] + original_ext
        final_filename = f"{safe_title}{original_ext}"

        # Файлды қайта атау
        os.rename(temp_filename, final_filename)

        await bot.send_chat_action(user_id, types.ChatActions.UPLOAD_DOCUMENT)
        await bot.send_document(user_id, types.InputFile(final_filename))
        os.remove(final_filename)

    except Exception as e:
        error_text = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
        await bot.send_message(user_id, f"⚠️ Қате болды:\n{str(e)}")
        print("Full Error:\n", error_text)

async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)
    print(f"Webhook set to {WEBHOOK_URL}")

async def on_shutdown(app):
    await bot.delete_webhook()

app = get_new_configured_app(dispatcher=dp, path=WEBHOOK_PATH)
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

if __name__ == '__main__':
    web.run_app(app, host=WEBAPP_HOST, port=WEBAPP_PORT)
