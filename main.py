import os
import logging
import telebot
from telebot import types
from keep_alive import keep_alive  # Подключаем твою систему ежеминутного самопинга

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота (берет токен из настроек Render)
TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)

# --- 1. ПРИВЕТСТВИЕ И ПЕРВЫЙ ВЫБОР ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    markup = types.InlineKeyboardMarkup()
    btn_hello = types.InlineKeyboardButton("👋 Привет", callback_data="step_robux")
    btn_skip = types.InlineKeyboardButton("⏭️ Пропустить", callback_data="step_robux")
    markup.row(btn_hello, btn_skip)
    
    bot.send_message(
        message.chat.id, 
        "Привет! Спасибо что зашла 😊", 
        reply_markup=markup
    )

# --- 2. ВЫБОР СУММЫ РОБУКСОВ ---
@bot.callback_query_handler(func=lambda call: call.data == "step_robux")
def step_robux(call):
    markup = types.InlineKeyboardMarkup()
    btn_200 = types.InlineKeyboardButton("💎 200 Робуксов", callback_data="rb_200")
    btn_500 = types.InlineKeyboardButton("🔥 500 Робуксов", callback_data="rb_500")
    btn_1000 = types.InlineKeyboardButton("👑 1000 Робуксов", callback_data="rb_1000")
    btn_no = types.InlineKeyboardButton("❌ Нет, это деньги на ветер", callback_data="rb_no")
    
    markup.row(btn_200)
    markup.row(btn_500)
    markup.row(btn_1000)
    markup.row(btn_no)
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Ладно я хотел чтобы ты мне купила робуксы выбери сумму которую ты мне задонатишь 👇",
        reply_markup=markup
    )

# --- 3. ОБРАБОТКА НАЖАТИЙ НА КНОПКИ ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("rb_"))
def handle_robux_choice(call):
    choice = call.data.split("_")[1]
    
    # Если нажала "Деньги на ветер" — бесконечный капкан
    if choice == "no":
        # Отправляем всплывающее окно (alert)
        bot.answer_callback_query(call.id, text="Так нельзя, выбери еще раз! 👿", show_alert=True)
        return
        
    # Считаем рубли в зависимости от выбора робуксов
    robux_amount = ""
    rubles_amount = ""
    
    if choice == "200":
        robux_amount = "200 робуксов"
        rubles_amount = "299"
    elif choice == "500":
        robux_amount = "500 робуксов"
        rubles_amount = "599"
    elif choice == "1000":
        robux_amount = "1000 робуксов"
        rubles_amount = "1050"
        
    # Итоговый текст
    final_text = f"Пасиба😍😍🏆 жду💋 ({robux_amount}) да мне надо {rubles_amount}₽ все давай пака"
    
    # Убираем кнопки и выводим финальное сообщение
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=final_text,
        reply_markup=None  # Кнопки стираются
    )
    bot.answer_callback_query(call.id) # Закрываем анимацию загрузки на кнопке

# --- 4. ЗАПУСК ВСЕЙ СИСТЕМЫ ---
if __name__ == "__main__":
    # Запускаем твой ежеминутный пустой пинг из файла keep_alive
    keep_alive()
    
    logging.info("Шуточный бот успешно запущен!")
    # Запуск бесконечной работы бота
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
