import os
import sqlite3
import random
import threading
import logging
from datetime import datetime, timedelta
from flask import Flask
import telebot
from telebot import types

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# --- 1. ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('giveaways.db')
    cursor = conn.cursor()
    
    # Таблица конкурсов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            creator_id INTEGER,
            channel_id TEXT,
            title TEXT,
            description TEXT,
            photo_id TEXT,
            end_time TIMESTAMP,
            status TEXT DEFAULT 'active',
            winner_id INTEGER,
            instruction_text TEXT,
            instruction_photo_id TEXT,
            message_id INTEGER
        )
    ''')
    
    # Таблица участников
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS participants (
            contest_id INTEGER,
            user_id INTEGER,
            user_name TEXT,
            PRIMARY KEY (contest_id, user_id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- 2. ВЕБ-СЕРВЕР ДЛЯ RENDER (HEALTH CHECK) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Giveaway Bot is active!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- 3. ИНИЦИАЛИЗАЦИЯ БОТА ---
TOKEN = os.getenv("TELEGRAM_TOKEN")  # Ну что бляди думали будет фри реклама а вот и нет уебаны
bot = telebot.TeleBot(TOKEN)

# Временное хранилище состояний создания конкурса
user_creation_data = {}

# --- 4. ВСПАМОГАТЕЛЬНЫЕ КЛАВИАТУРЫ ---
def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🎉 Создать новый конкурс"))
    return markup

def get_skip_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("⏭ Пропустить"))
    return markup

# --- 5. ОБРАБОТКА КОМАНД И НАЧАЛА СОЗДАНИЯ ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    welcome_text = (
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        "Я бот для проведения розыгрышей и конкурсов.\n"
        "Нажмите кнопку ниже, чтобы начать!"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda msg: msg.text == "🎉 Создать новый конкурс")
def start_contest_creation(message):
    chat_id = message.chat.id
    user_creation_data[chat_id] = {}
    
    msg = bot.send_message(
        chat_id,
        "📌 **Шаг 1/6:** Укажите `@username` или `ID` канала, где будет проходить конкурс.\n\n"
        "⚠️ *Убедитесь, что бот добавлен в этот канал как администратор!*",
        parse_mode="Markdown",
        reply_markup=types.ReplyKeyboardRemove()
    )
    bot.register_next_step_handler(msg, process_step_channel)

# Шаг 1: Канал
def process_step_channel(message):
    chat_id = message.chat.id
    channel = message.text.strip()
    if not channel.startswith("@") and not channel.startswith("-"):
        channel = "@" + channel
    
    user_creation_data[chat_id]['channel_id'] = channel
    msg = bot.send_message(chat_id, "📌 **Шаг 2/6:** Введите **заголовок** конкурса:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_step_title)

# Шаг 2: Заголовок
def process_step_title(message):
    chat_id = message.chat.id
    user_creation_data[chat_id]['title'] = message.text
    msg = bot.send_message(chat_id, "📌 **Шаг 3/6:** Введите **описание** конкурса:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_step_description)

# Шаг 3: Описание
def process_step_description(message):
    chat_id = message.chat.id
    user_creation_data[chat_id]['description'] = message.text
    msg = bot.send_message(
        chat_id,
        "📌 **Шаг 4/6:** Отправьте **картинку** для поста (или нажмите кнопку 'Пропустить'):",
        parse_mode="Markdown",
        reply_markup=get_skip_keyboard()
    )
    bot.register_next_step_handler(msg, process_step_photo)

# Шаг 4: Картинка поста
def process_step_photo(message):
    chat_id = message.chat.id
    if message.content_type == 'photo':
        user_creation_data[chat_id]['photo_id'] = message.photo[-1].file_id
    else:
        user_creation_data[chat_id]['photo_id'] = None

    msg = bot.send_message(
        chat_id,
        "📌 **Шаг 5/6:** Укажите длительность конкурса в **минутах** (например `60` — 1 час, `1440` — 1 день):",
        parse_mode="Markdown",
        reply_markup=types.ReplyKeyboardRemove()
    )
    bot.register_next_step_handler(msg, process_step_duration)

# Шаг 5: Длительность
def process_step_duration(message):
    chat_id = message.chat.id
    try:
        minutes = int(message.text.strip())
        end_time = datetime.now() + timedelta(minutes=minutes)
        user_creation_data[chat_id]['end_time'] = end_time
        
        msg = bot.send_message(
            chat_id,
            "📌 **Шаг 6/6 (Опционально):** Отправьте **инструкцию для победителя** (как забрать приз) "
            "или прикрепите фото с инструкцией (или нажмите 'Пропустить'):",
            parse_mode="Markdown",
            reply_markup=get_skip_keyboard()
        )
        bot.register_next_step_handler(msg, process_step_instruction)
    except ValueError:
        msg = bot.send_message(chat_id, "❌ Ошибка! Введите число (количество минут):")
        bot.register_next_step_handler(msg, process_step_duration)

# Шаг 6: Инструкция и публикации
def process_step_instruction(message):
    chat_id = message.chat.id
    data = user_creation_data.get(chat_id, {})
    
    if message.content_type == 'photo':
        data['instruction_photo_id'] = message.photo[-1].file_id
        data['instruction_text'] = message.caption or "Инструкция по получению приза прикреплена к фото."
    elif message.text != "⏭ Пропустить":
        data['instruction_photo_id'] = None
        data['instruction_text'] = message.text
    else:
        data['instruction_photo_id'] = None
        data['instruction_text'] = None

    # Запись конкурсов в БД
    conn = sqlite3.connect('giveaways.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO contests (creator_id, channel_id, title, description, photo_id, end_time, instruction_text, instruction_photo_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        chat_id, data['channel_id'], data['title'], data['description'],
        data['photo_id'], data['end_time'], data['instruction_text'], data['instruction_photo_id']
    ))
    contest_id = cursor.lastrowid
    conn.commit()

    # Публикация в канал
    try:
        end_str = data['end_time'].strftime("%d.%m.%Y %H:%M")
        post_text = (
            f"🎉 **{data['title']}**\n\n"
            f"{data['description']}\n\n"
            f"⏳ **Итоги:** `{end_str}`"
        )
        
        inline_kb = types.InlineKeyboardMarkup()
        inline_kb.add(types.InlineKeyboardButton("Участвовать 🎁 (0)", callback_data=f"join_{contest_id}"))

        if data['photo_id']:
            sent_msg = bot.send_photo(data['channel_id'], data['photo_id'], caption=post_text, parse_mode="Markdown", reply_markup=inline_kb)
        else:
            sent_msg = bot.send_message(data['channel_id'], post_text, parse_mode="Markdown", reply_markup=inline_kb)
        
        # Обновляем message_id в базе
        cursor.execute('UPDATE contests SET message_id = ? WHERE id = ?', (sent_msg.message_id, contest_id))
        conn.commit()

        bot.send_message(chat_id, "✅ **Конкурс успешно создан и опубликован в канале!**", parse_mode="Markdown", reply_markup=get_main_keyboard())
    except Exception as e:
        bot.send_message(chat_id, f"❌ Ошибка при публикации в канал: {e}\nУбедитесь, что бот добавлен администратором в канал!", reply_markup=get_main_keyboard())
    finally:
        conn.close()

# --- 6. НАЖАТИЕ НА КНОПКУ "УЧАСТВОВАТЬ" ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("join_"))
def handle_join(call):
    contest_id = int(call.data.split("_")[1])
    user_id = call.from_user.id
    user_name = call.from_user.first_name

    conn = sqlite3.connect('giveaways.db')
    cursor = conn.cursor()

    # Проверка статуса конкурса
    cursor.execute('SELECT status, channel_id, message_id FROM contests WHERE id = ?', (contest_id,))
    contest = cursor.fetchone()

    if not contest or contest[0] != 'active':
        bot.answer_callback_query(call.id, "❌ Этот конкурс уже завершен!", show_alert=True)
        conn.close()
        return

    # Добавление участника
    try:
        cursor.execute('INSERT INTO participants (contest_id, user_id, user_name) VALUES (?, ?, ?)', (contest_id, user_id, user_name))
        conn.commit()
        bot.answer_callback_query(call.id, "🎉 Вы успешно зарегистрированы в розыгрыше!", show_alert=True)

        # Обновление кнопки с количеством участников
        cursor.execute('SELECT COUNT(*) FROM participants WHERE contest_id = ?', (contest_id,))
        count = cursor.fetchone()[0]

        inline_kb = types.InlineKeyboardMarkup()
        inline_kb.add(types.InlineKeyboardButton(f"Участвовать 🎁 ({count})", callback_data=f"join_{contest_id}"))

        bot.edit_message_reply_markup(chat_id=contest[1], message_id=contest[2], reply_markup=inline_kb)
    except sqlite3.IntegrityError:
        bot.answer_callback_query(call.id, "⚠️ Вы уже участвуете в этом конкурсе!", show_alert=True)
    finally:
        conn.close()

# --- 7. КНОПКА ПУБЛИКАЦИИ ПОБЕДИТЕЛЯ В КАНАЛ ХОСТОМ ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("publish_"))
def handle_publish_winner(call):
    contest_id = int(call.data.split("_")[1])
    
    conn = sqlite3.connect('giveaways.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT channel_id, title, winner_id, instruction_text, instruction_photo_id 
        FROM contests WHERE id = ?
    ''', (contest_id,))
    contest = cursor.fetchone()
    conn.close()

    if contest:
        channel_id, title, winner_id, instr_text, instr_photo = contest
        try:
            winner_user = bot.get_chat(winner_id)
            winner_mention = f"[{winner_user.first_name}](tg://user?id={winner_id})"
        except Exception:
            winner_mention = f"ID: {winner_id}"

        win_text = (
            f"🏆 **Итоги конкурса '{title}'!**\n\n"
            f"Победитель: {winner_mention} 🥳\n\n"
        )
        if instr_text:
            win_text += f"📋 **Инструкция для победителя:**\n{instr_text}"

        try:
            if instr_photo:
                bot.send_photo(channel_id, instr_photo, caption=win_text, parse_mode="Markdown")
            else:
                bot.send_message(channel_id, win_text, parse_mode="Markdown")
            
            bot.answer_callback_query(call.id, "✅ Результаты опубликованы в канале!")
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        except Exception as e:
            bot.send_message(call.message.chat.id, f"❌ Ошибка публикации: {e}")

# --- 8. ФОНОВЫЙ ПОТОК ПРОВЕРКИ ИТОГОВ (24/7) ---
def check_contests_loop():
    while True:
        try:
            conn = sqlite3.connect('giveaways.db')
            cursor = conn.cursor()
            
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("SELECT id, creator_id, title, channel_id FROM contests WHERE end_time <= ? AND status = 'active'", (now_str,))
            ended_contests = cursor.fetchall()

            for contest in ended_contests:
                contest_id, creator_id, title, channel_id = contest
                
                # Выбор случайного победителя
                cursor.execute("SELECT user_id, user_name FROM participants WHERE contest_id = ?", (contest_id,))
                participants = cursor.fetchall()

                if participants:
                    winner = random.choice(participants)
                    winner_id, winner_name = winner

                    cursor.execute("UPDATE contests SET status = 'finished', winner_id = ? WHERE id = ?", (winner_id, contest_id))
                    conn.commit()

                    # Сообщение хосту
                    kb = types.InlineKeyboardMarkup()
                    kb.add(types.InlineKeyboardButton("📢 Опубликовать итоги в канал", callback_data=f"publish_{contest_id}"))
                    
                    bot.send_message(
                        creator_id,
                        f"🎉 **Конкурс завершен!**\n\n"
                        f"📌 Конкурс: **{title}**\n"
                        f"👤 Победитель: [{winner_name}](tg://user?id={winner_id}) (`{winner_id}`)\n\n"
                        f"Нажмите кнопку ниже, чтобы отправить результаты и инструкцию в канал:",
                        parse_mode="Markdown",
                        reply_markup=kb
                    )
                else:
                    cursor.execute("UPDATE contests SET status = 'finished' WHERE id = ?", (contest_id,))
                    conn.commit()
                    bot.send_message(creator_id, f"😔 Конкурс **{title}** завершен, но участников не было.")
            
            conn.close()
        except Exception as e:
            logging.error(f"Ошибка в фоновом потоке проверки: {e}")
        
        threading.Event().wait(15)  # Проверка каждые 15 секунд

# --- 9. ЗАПУСК ---
if __name__ == "__main__":
    # Запуск Flask сервера
    threading.Thread(target=run_flask, daemon=True).start()
    # Запуск фоновой проверки конкурсов
    threading.Thread(target=check_contests_loop, daemon=True).start()
    
    logging.info("Бот для розыгрышей запущен!")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
