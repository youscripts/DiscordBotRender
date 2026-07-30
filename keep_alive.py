import os
import time
import random
import logging
import requests
from flask import Flask, request
from threading import Thread

app = Flask('')
# Отключаем лишние стандартные логи Werkzeug, чтобы не забивать консоль Render
logging.getLogger('werkzeug').setLevel(logging.ERROR)

# 1. ОБРАБОТЧИК ЗАПРОСОВ (Серверная часть)
@app.route('/solve', methods=['POST'])
def solve_math():
    data = request.get_json()
    if data and 'example' in data:
        try:
            # Безопасно вычисляем пример сгенерированный нами же
            result = eval(data['example'], {"__builtins__": None}, {})
            return {"status": "success", "result": result}, 200
        except Exception:
            return {"status": "error"}, 400
    return {"status": "ignored"}, 200

@app.route('/')
def home():
    return "Server is Active", 200

def run_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# 2. АВТО-ПИНГЕР (Клиентская часть)
def self_ping_loop():
    # Ждем 10 секунд, пока Flask полностью запустится при старте
    time.sleep(10)
    
    # Render дает вашему приложению уникальное имя, берем его из окружения
    # Если переменной нет, запросы будут идти локально
    app_name = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
    url = f"https://{app_name}/solve" if app_name else "http://127.0.0"
    
    while True:
        try:
            # Генерируем случайный пример
            num1 = random.randint(1, 100)
            num2 = random.randint(1, 100)
            op = random.choice(['+', '-', '*'])
            example_str = f"{num1} {op} {num2}"
            
            # Отправляем скрытый запрос сами себе
            payload = {"example": example_str}
            response = requests.post(url, json=payload, timeout=5)
            
            if response.status_code == 200:
                logging.info(f"[Self-Ping] Пример {example_str} успешно решен сервером.")
                
        except Exception as e:
            logging.error(f"[Self-Ping] Ошибка отправки запроса: {e}")
            
        # Засыпаем на 5 минут перед следующим примером
        time.sleep(300)

# Основная функция запуска
def keep_alive():
    # Запуск веб-сервера Flask
    server_thread = Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    
    # Запуск генератора примеров в отдельном потоке
    ping_thread = Thread(target=self_ping_loop)
    ping_thread.daemon = True
    ping_thread.start()
