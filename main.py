# coding=utf-8
import os
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["LANG"] = "en_US.UTF-8"

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import logging
import openai
import datetime
import json
from aiogram import Bot, Dispatcher, executor, types
from flask import Flask
from threading import Thread
from dotenv import load_dotenv

load_dotenv()  # Для локальной разработки

# === Flask-сервер для Render (чтобы не засыпал) ===
app = Flask('')

@app.route('/')
def home():
    return "Бот работает!"

def run():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run).start()

# === Токены из переменных окружения ===
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# === Файл для хранения информации о пробном периоде и подписке ===
TRIALS_FILE = "trials.json"

# Функция для чтения данных пользователя
def get_user_info(user_id):
    try:
        with open(TRIALS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get(str(user_id), None)
    except Exception as e:
        logging.error("Ошибка чтения файла trials.json: %s", e)
        return None

# Функция для установки данных пользователя
def set_user_info(user_id, info):
    try:
        try:
            with open(TRIALS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except:
            data = {}
        data[str(user_id)] = info
        with open(TRIALS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception as e:
        logging.error("Ошибка сохранения файла trials.json: %s", e)

# === Логирование и Telegram-бот ===
logging.basicConfig(level=logging.INFO)
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(bot)

# Конфигурация: срок бесплатного периода – 14 дней, стоимость продления – 990 руб. в месяц
FREE_TRIAL_DAYS = 14
SUBSCRIPTION_PRICE_RUB = 990  # в месяц
MANAGER_CONTACT = "@methodk"  # контакты менеджера

# === Обработка команды /start ===
@dp.message_handler(commands=['start'])
async def handle_start(message: types.Message):
    user_id = message.from_user.id
    user_info = get_user_info(user_id)
    now = datetime.datetime.now()
    if user_info is None:
        # Если данных нет, создаём запись с бесплатным периодом 14 дней
        expiration = now + datetime.timedelta(days=FREE_TRIAL_DAYS)
        user_info = {
            "trial_start": now.isoformat(),
            "expiration": expiration.isoformat()
        }
        set_user_info(user_id, user_info)
    await message.reply("Привет! Я твой AI-секретарь. Напиши, какие задачи у тебя сегодня — помогу приоритизировать.")

# === Генерация промта для GPT ===
def build_prompt(message_text, user_id):
    # Здесь можно добавить любые дополнительные данные, индивидуальные для пользователя
    return f"""Ты — персональный AI-секретарь для бизнес-руководителя (ID: {user_id}).
Цель: помогать наводить порядок в задачах, снижать хаос и давать рекомендации по оптимизации времени.
Вот новое сообщение от клиента (обрезано до 500 символов):
{message_text[:500]}
Если видишь, что клиент тратит время из-за отсутствия регламентов, делегирования или KPI – предложи внедрить эти инструменты с помощью команды "Метод Куфтырева".
"""

# === Обработка остальных сообщений ===
@dp.message_handler()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    now = datetime.datetime.now()
    user_info = get_user_info(user_id)
    # Если пользователь не зарегистрирован — создаём запись (это редко, если /start уже вызван)
    if user_info is None:
        expiration = now + datetime.timedelta(days=FREE_TRIAL_DAYS)
        user_info = {
            "trial_start": now.isoformat(),
            "expiration": expiration.isoformat()
        }
        set_user_info(user_id, user_info)
    
    # Преобразуем дату окончания доступа в объект datetime
    expiration_date = datetime.datetime.fromisoformat(user_info["expiration"])
    if now > expiration_date:
        await message.reply(
            f"⏳ Ваш пробный период закончился. Чтобы продолжить работу, оформите подписку за {SUBSCRIPTION_PRICE_RUB} руб. в месяц, "
            f"написав нашему менеджеру {MANAGER_CONTACT}."
        )
        return

    prompt = build_prompt(message.text, user_id)
    print("👉 PROMPT:\n", prompt)
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.7
        )
        reply_text = response["choices"][0]["message"]["content"]
        print("✅ REPLY:\n", reply_text)
    except Exception as e:
        print("❌ Ошибка при запросе к GPT:", e)
        reply_text = f"🚫 GPT вернул ошибку: {e}"

    try:
        reply_text = reply_text.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
    except Exception as e:
        print("❌ Ошибка при финальной обработке ответа:", e)
        reply_text = "⚠️ Ошибка обработки ответа."
    await message.reply(reply_text)

# === Запуск бота ===
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
