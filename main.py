import os
import threading
import logging
from flask import Flask
import telebot

# Настройка логирования в консоль Render
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 1. Веб-сервер Flask для прохождения проверки хостинга Render (Health Check)
app = Flask(__name__)

@app.route('/')
def home():
    return "Telegram Bot is active and running on Render!"

def run_flask():
    # Render автоматически передает порт в переменную окружения PORT
    port = int(os.environ.get("PORT", 10000))
    logging.info(f"Запуск Flask-сервера на порту {port}...")
    app.run(host='0.0.0.0', port=port)

# 2. Инициализация Telegram-бота
TOKEN = os.environ.get('8884771579:AAHyOVjQaJBRKpSPJALg2oVdwuRjBHQePEA')

if not TOKEN:
    logging.error("ОШИБКА: Переменная окружения BOT_TOKEN не найдена! Убедитесь, что вы добавили её в Render Dashboard -> Environment Variables.")

bot = telebot.TeleBot(TOKEN) if TOKEN else None

if bot:
    # Обработчик команды /start
    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        user_name = message.from_user.first_name
        welcome_text = (
            f"Привет, {user_name}! 👋\n\n"
            "Я твой новый Telegram-бот, переписанный с Discord и успешно работающий на **Render.com**! 🚀\n\n"
            "Доступные команды:\n"
            "/start — Запустить бота\n"
            "/help — Справка"
        )
        bot.reply_to(message, welcome_text, parse_mode="Markdown")

    # Обработчик команды /help
    @bot.message_handler(commands=['help'])
    def send_help(message):
        help_text = (
            "📌 **Справка по боту:**\n"
            "• Напиши мне любое сообщение, и я отвечу тебе.\n"
            "• Бот настроен на постоянную работу 24/7."
        )
        bot.reply_to(message, help_text, parse_mode="Markdown")

    # Обработчик любых текстовых сообщений (эхо)
    @bot.message_handler(content_types=['text'])
    def echo_message(message):
        bot.reply_to(message, f"💬 Ты написал: {message.text}")

if __name__ == "__main__":
    # Запуск Flask сервера в отдельном потоке
    threading.Thread(target=run_flask, daemon=True).start()
    
    if bot:
        logging.info("Telegram бот запущен и готов к работе!")
        # infinity_polling автоматически восстанавливает соединение при сетевых сбоях
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    else:
        logging.error("Бот не запущен из-за отсутствия BOT_TOKEN.")
