import os
import re
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from yt_dlp import YoutubeDL

API_TOKEN = '7378664309:AAHc2TeVWSA9pKwtn9QyTkG-ZkQymyPwSbY'  

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

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
        'noplaylist': True
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
        await bot.send_message(user_id, f"⚠️ Қате болды: {str(e)}")
        print("Error:", e)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
