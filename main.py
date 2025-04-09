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
from aiogram import Bot, Dispatcher, executor, types
from flask import Flask
from threading import Thread

# === Flask-сервер для Replit (чтобы не засыпал) ===
app = Flask('')

@app.route('/')
def home():
    return "Бот работает!"

def run():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run).start()

# === Токены ===
TELEGRAM_TOKEN = '7967405734:AAHQ7iyLWD5x6pT7V6F5I7ubjY4CXXn1PGU'
OPENAI_API_KEY = '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'

openai.api_key = OPENAI_API_KEY

# === Профиль клиента ===
client_profile = {
    "name": "Артем",
    "activation_date": "2025-04-03",
    "average_tasks_per_day": 20,
    "time_wasters": ["Маркетинг", "отдел первичных продаж"],
    "goals": [
        "Сделать оборот 225 000 руб (5 продаж стартеров)",
        "Завести 3 клиентов на подписку (360 000 руб * 3)"
    ],
    "personally_controlled_tasks": ["Лидогенерация", "обработка лидов", "продажи"]
}

# === Логирование и Telegram-бот ===
logging.basicConfig(level=logging.INFO)
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(bot)

# === Обработка команды /start ===
@dp.message_handler(commands=['start'])
async def handle_start(message: types.Message):
    await message.reply("Привет! Я твой AI-секретарь. Напиши, какие задачи у тебя сегодня — помогу приоритизировать.")

# === Генерация промта для GPT ===
def build_prompt(message_text):
    return f"""Ты — персональный AI-секретарь для бизнес-руководителя по имени {client_profile['name']}.
Цель: помогать ему каждый день наводить порядок в задачах, снижать хаос, фиксировать итоги дня и давать рекомендации, как сэкономить время.
Отвечай кратко, по делу, уважительно и с заботой.
Контекст:
– Среднее число задач в день: {client_profile['average_tasks_per_day']}
– Основные "пожиратели времени": {', '.join(client_profile['time_wasters'])}
– Цели: {', '.join(client_profile['goals'])}
– Контролирует лично: {', '.join(client_profile['personally_controlled_tasks'])}
Вот новое сообщение от клиента (обрезано до 500 символов):
{message_text[:500]}
Дай ответ в рамках своей роли AI-секретаря.
Если видишь, что клиент тратит время из-за отсутствия регламентов, делегирования или KPI — подсвети это, и предложи вежливо внедрить такие инструменты с помощью команды "Метод Куфтырева".
"""

# === Проверка срока доступа (7 дней) ===
def is_access_valid():
    start_date = datetime.datetime.strptime(client_profile['activation_date'], "%Y-%m-%d")
    return (datetime.datetime.now() - start_date).days < 7

# === Обработка остальных сообщений ===
@dp.message_handler()
async def handle_message(message: types.Message):
    if not is_access_valid():
        await message.reply("⏳ Пробный период завершён. Хотите продолжить работу с AI-секретарём? Напишите менеджеру Метод Куфтырева.")
        return

    prompt = build_prompt(message.text)
    try:
        print("👉 PROMPT:\n", prompt)
    except Exception as e:
        print("Ошибка логирования промта:", e)

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
