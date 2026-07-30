import os
import time
import logging
import requests
from flask import Flask
from threading import Thread

# Инициализируем веб-сервер Flask
app = Flask('')

# Отключаем стандартные логи Flask (Werkzeug), чтобы они не засоряли консоль Render каждую минуту
logging.getLogger('werkzeug').setLevel(logging.ERROR)

# 1. ОБРАБОТЧИК ВХОДЯЩИХ ЗАПРОСОВ (Серверная часть)
@app.route('/')
def home():
    # Возвращаем пустой ответ со статусом 200 OK
    return "", 200

def run_server():
    # Render автоматически передает нужный порт в переменные окружения
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# 2. АВТО-ПИНГЕР (Клиентская часть, отправка пустого запроса)
def self_ping_loop():
    # Ждем 10 секунд при старте, чтобы Flask успел полностью подняться
    time.sleep(10)
    
    # Получаем уникальный домен твоего приложения на Render
    app_name = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
    # Если бот запущен локально, пингуем локальный адрес, если на Render — внешний URL
    url = f"https://{app_name}/" if app_name else "http://127.0.0"
    
    while True:
        try:
            # Отправляем пустой GET-запрос сами себе с таймаутом в 5 секунд
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                # Технический лог в консоль бота (можно закомментировать, если не нужен)
                print("[Keep-Alive] Отправлен пустой запрос. Сервер активен.")
                
        except Exception as e:
            print(f"[Keep-Alive] Не удалось отправить запрос: {e}")
            
        # Засыпаем ровно на 60 секунд (1 минуту) перед следующим запросом
        time.sleep(60)

# Главная функция, которую мы вызываем в main.py
def keep_alive():
    # Запускаем Flask-сервер в отдельном независимом потоке
    server_thread = Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    
    # Запускаем ежеминутный пингер во втором потоке
    ping_thread = Thread(target=self_ping_loop)
    ping_thread.daemon = True
    ping_thread.start()
