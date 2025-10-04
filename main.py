#!/usr/bin/env python3
# Telegram Bot: PNG/JPG to WEBP converter + Flask ping server

import os
import tempfile
from PIL import Image, UnidentifiedImageError
import telebot
from flask import Flask

# --- Telegram Bot ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("❌ Please set BOT_TOKEN environment variable!")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

MAX_FILE_SIZE_MB = 20

def convert_to_webp(input_path, output_path):
    with Image.open(input_path) as img:
        if img.mode in ("RGBA", "LA") or ("transparency" in img.info):
            img.save(output_path, format="WEBP", lossless=True)
        else:
            img.convert("RGB").save(output_path, format="WEBP", quality=85)

@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    text = (
        "👋 *Welcome!* I convert your PNG/JPG images into *WEBP* format. 🎉\n\n"
        "👉 Just send me a *photo* or upload an *image file*.\n"
        "I'll magically turn it into WEBP — perfect for stickers ✨"
    )
    bot.reply_to(message, text)

@bot.message_handler(content_types=["photo", "document"])
def handle_image(message):
    file_info = None
    filename = "converted.webp"

    if message.content_type == "photo":
        file_info = bot.get_file(message.photo[-1].file_id)
        filename = message.photo[-1].file_unique_id + ".webp"
    elif message.content_type == "document":
        if not message.document.mime_type.startswith("image/"):
            bot.reply_to(message, "⚠️ Please send only PNG or JPG images.")
            return
        if message.document.file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
            bot.reply_to(message, f"❌ File too large! Limit is {MAX_FILE_SIZE_MB} MB.")
            return
        file_info = bot.get_file(message.document.file_id)
        base = os.path.splitext(message.document.file_name or "image")[0]
        filename = f"{base}.webp"

    if not file_info:
        bot.reply_to(message, "⚠️ Couldn't get the file. Try again.")
        return

    waiting_msg = bot.reply_to(message, "🔄 Converting your image... Please wait ✨")

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "input")
            output_path = os.path.join(tmpdir, "output.webp")

            downloaded = bot.download_file(file_info.file_path)
            with open(input_path, "wb") as f:
                f.write(downloaded)

            try:
                convert_to_webp(input_path, output_path)
            except UnidentifiedImageError:
                bot.edit_message_text(
                    "❌ I couldn't read that image. Try another PNG/JPG.",
                    chat_id=waiting_msg.chat.id,
                    message_id=waiting_msg.message_id,
                )
                return

            with open(output_path, "rb") as out:
                bot.send_document(
                    message.chat.id,
                    out,
                    visible_file_name=filename,
                    caption="✅ Done! Your image is now *WEBP* 🎯",
                )

            bot.delete_message(waiting_msg.chat.id, waiting_msg.message_id)

    except Exception:
        bot.edit_message_text(
            "❌ Oops, something went wrong! Try again later.",
            chat_id=waiting_msg.chat.id,
            message_id=waiting_msg.message_id,
        )

@bot.message_handler(func=lambda m: True)
def fallback(message):
    bot.reply_to(message, "🤷 Send me a *photo* or *PNG/JPG* file and I'll convert it to WEBP! 🪄")

# --- Flask server for uptime ping ---
app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Bot is alive!"

import threading
def run_bot():
    print("🚀 Bot is running...")
    bot.infinity_polling()

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
