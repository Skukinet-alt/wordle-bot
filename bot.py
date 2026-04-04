import os
import random
import json
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = "8589671232:AAEovF72xAAODgTKWUUtCQT3XmQbAjZJmmk"  # Твой токен
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Словарь слов (5-6 букв, русские)
WORDS = [
    "КОТ",
    "ДОМ",
    "ЛЕС",
    "МОРЕ",
    "СОЛНЦЕ",
    "ЗВЕЗДА",
    "РОБОТ",
    "ПИТОН",
    "КНИГА",
    "СТОЛ",
    "СТУЛ",
    "ОКНО",
    "ДВЕРЬ",
    "МАШИНА",
    "УЧИТЕЛЬ",
    "ДРУГ",
    "СЧАСТЬЕ",
    "РАДОСТЬ",
    "СВЕТ",
    "ТЬМА",
    "ВЕТЕР",
    "ДОЖДЬ",
]
MIN_WORD_LEN = 3
MAX_WORD_LEN = 6

# Хранилище игр (в реальном проекте используй БД)
games = {}
stats = {}

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========


def send_message(chat_id, text, reply_to=None):
    """Отправка сообщения в Telegram"""
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_to:
        payload["reply_to_message_id"] = reply_to
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Ошибка отправки: {e}")


def get_random_word():
    """Выбирает случайное слово из словаря"""
    return random.choice(WORDS).upper()


def check_guess(guess, target):
    """
    Проверяет догадку и возвращает:
    - результат (с эмодзи: 🟩 зелёная, 🟨 жёлтая, ⬛ серая)
    - список угаданных букв на своих местах
    - список найденных букв (не на своих местах)
    - список отсутствующих букв
    """
    guess = guess.upper()
    target = target.upper()

    if len(guess) != len(target):
        return None, None, None, None

    result = []
    green_letters = []
    yellow_letters = []
    wrong_letters = []

    # Сначала ищем точные совпадения (зелёные)
    target_copy = list(target)
    guess_copy = list(guess)

    for i in range(len(guess)):
        if guess[i] == target[i]:
            result.append("🟩")
            green_letters.append(guess[i])
            target_copy[i] = None  # Помечаем как использованную
            guess_copy[i] = None

    # Теперь ищем буквы, которые есть, но не на своих местах (жёлтые)
    for i in range(len(guess)):
        if guess_copy[i] is not None and guess_copy[i] in target_copy:
            result.append("🟨")
            yellow_letters.append(guess[i])
            # Удаляем первое вхождение из target_copy
            idx = target_copy.index(guess[i])
            target_copy[idx] = None
        elif guess_copy[i] is not None:
            result.append("⬛")
            wrong_letters.append(guess[i])

    # Для пустых мест, где не было буквы
    while len(result) < len(guess):
        result.append("⬛")

    return "".join(result), green_letters, yellow_letters, wrong_letters


def format_game_state(game):
    """Форматирует текущее состояние игры для отправки пользователю"""
    target_len = len(game["target"])
    attempts = game["attempts"]
    max_attempts = game["max_attempts"]

    message = f"🎮 <b>Игра Wordle</b>\n"
    message += f"📏 Длина слова: {target_len} букв\n"
    message += f"📝 Попыток использовано: {len(attempts)}/{max_attempts}\n\n"

    # Показываем предыдущие попытки
    if attempts:
        message += "<b>Твои попытки:</b>\n"
        for attempt in attempts:
            message += f"<code>{attempt['word']}</code> {attempt['result']}\n"

    # Показываем подсказки
    all_green = set()
    all_yellow = set()
    all_wrong = set()

    for attempt in attempts:
        all_green.update(attempt.get("green", []))
        all_yellow.update(attempt.get("yellow", []))
        all_wrong.update(attempt.get("wrong", []))

    if all_green:
        message += f"\n✅ <b>На своих местах:</b> {', '.join(sorted(all_green))}\n"
    if all_yellow:
        message += (
            f"🟡 <b>Есть в слове (не на месте):</b> {', '.join(sorted(all_yellow))}\n"
        )
    if all_wrong:
        message += f"❌ <b>Нет в слове:</b> {', '.join(sorted(all_wrong))}\n"

    return message


def save_stats(user_id, won):
    """Сохраняет статистику пользователя"""
    if user_id not in stats:
        stats[user_id] = {"wins": 0, "losses": 0, "total": 0}

    stats[user_id]["total"] += 1
    if won:
        stats[user_id]["wins"] += 1
    else:
        stats[user_id]["losses"] += 1


# ========== ОБРАБОТЧИКИ КОМАНД ==========


def start_game(user_id, chat_id):
    """Начинает новую игру"""
    target_word = get_random_word()
    games[user_id] = {
        "target": target_word,
        "attempts": [],
        "max_attempts": 6,
        "game_over": False,
        "won": False,
    }

    message = f"🎯 <b>Новая игра началась!</b>\n\n"
    message += f"Я загадал слово из <b>{len(target_word)} букв</b>.\n"
    message += f"У тебя {games[user_id]['max_attempts']} попыток.\n\n"
    message += f"📝 Отправь слово командой: <code>/guess ТВОЁ_СЛОВО</code>\n"
    message += f"❓ Не знаешь слово? Отправь <code>/giveup</code>\n\n"
    message += f"💡 <b>Совет:</b> Начни с простых слов, чтобы проверить буквы!"

    send_message(chat_id, message)


def make_guess(user_id, chat_id, guess_word):
    """Обрабатывает догадку пользователя"""
    # Проверяем, есть ли активная игра
    if user_id not in games or games[user_id].get("game_over", False):
        send_message(chat_id, "❌ У тебя нет активной игры! Начни новую командой /new")
        return

    game = games[user_id]
    target = game["target"]

    # Проверяем длину слова
    if len(guess_word) != len(target):
        send_message(
            chat_id,
            f"⚠️ Слово должно быть из <b>{len(target)} букв</b>! Ты отправил {len(guess_word)}.",
        )
        return

    # Проверяем, не заканчивалась ли игра
    if len(game["attempts"]) >= game["max_attempts"]:
        send_message(
            chat_id,
            f"💀 Игра окончена! Загаданное слово было: <b>{target}</b>\nНачни новую игру командой /new",
        )
        game["game_over"] = True
        return

    # Проверяем догадку
    result, green, yellow, wrong = check_guess(guess_word, target)

    if result is None:
        send_message(chat_id, f"⚠️ Что-то пошло не так... Попробуй ещё раз.")
        return

    # Сохраняем попытку
    game["attempts"].append(
        {
            "word": guess_word.upper(),
            "result": result,
            "green": green,
            "yellow": yellow,
            "wrong": wrong,
        }
    )

    # Проверяем победу
    if guess_word.upper() == target:
        game["game_over"] = True
        game["won"] = True
        save_stats(user_id, True)

        message = f"🎉 <b>ПОЗДРАВЛЯЮ! Ты угадал слово!</b>\n\n"
        message += f"Загаданное слово: <b>{target}</b>\n"
        message += (
            f"Попыток использовано: {len(game['attempts'])}/{game['max_attempts']}\n\n"
        )
        message += format_game_state(game)
        message += f"\n📊 Твоя статистика: Побед: {stats[user_id]['wins']} | Поражений: {stats[user_id]['losses']}"

        send_message(chat_id, message)
        return

    # Проверяем конец игры (проигрыш)
    if len(game["attempts"]) >= game["max_attempts"]:
        game["game_over"] = True
        save_stats(user_id, False)

        message = f"💀 <b>Ты проиграл!</b>\n\n"
        message += f"Загаданное слово было: <b>{target}</b>\n\n"
        message += format_game_state(game)
        message += f"\n📊 Твоя статистика: Побед: {stats[user_id]['wins']} | Поражений: {stats[user_id]['losses']}"

        send_message(chat_id, message)
        return

    # Продолжаем игру — показываем текущее состояние
    message = format_game_state(game)
    message += f"\n📝 Осталось попыток: {game['max_attempts'] - len(game['attempts'])}"
    send_message(chat_id, message)


def give_up(user_id, chat_id):
    """Сдаться и завершить игру"""
    if user_id not in games or games[user_id].get("game_over", False):
        send_message(chat_id, "❌ У тебя нет активной игры!")
        return

    game = games[user_id]
    target = game["target"]
    game["game_over"] = True
    save_stats(user_id, False)

    message = f"😢 <b>Ты сдался!</b>\n\n"
    message += f"Загаданное слово было: <b>{target}</b>\n\n"
    message += format_game_state(game)
    message += f"\n📊 Твоя статистика: Побед: {stats[user_id]['wins']} | Поражений: {stats[user_id]['losses']}"

    send_message(chat_id, message)


def show_stats(user_id, chat_id):
    """Показывает статистику пользователя"""
    if user_id not in stats:
        stats[user_id] = {"wins": 0, "losses": 0, "total": 0}

    win_rate = 0
    if stats[user_id]["total"] > 0:
        win_rate = (stats[user_id]["wins"] / stats[user_id]["total"]) * 100

    message = f"📊 <b>Твоя статистика</b>\n\n"
    message += f"🎮 Всего игр: {stats[user_id]['total']}\n"
    message += f"✅ Побед: {stats[user_id]['wins']}\n"
    message += f"❌ Поражений: {stats[user_id]['losses']}\n"
    message += f"📈 Процент побед: {win_rate:.1f}%"

    send_message(chat_id, message)


# ========== ОСНОВНОЙ ОБРАБОТЧИК ==========


@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    """Обработчик вебхука от Telegram"""
    try:
        data = request.get_json()

        if "message" in data:
            msg = data["message"]
            chat_id = msg["chat"]["id"]
            user_id = str(msg["from"]["id"])

            # Текст сообщения
            if "text" in msg:
                text = msg["text"].strip()

                # Обработка команд
                if text == "/start":
                    welcome = (
                        "🎯 <b>Добро пожаловать в Wordle-бота!</b>\n\n"
                        "Правила простые:\n"
                        "1️⃣ Я загадываю слово\n"
                        "2️⃣ Ты пытаешься его угадать\n"
                        "3️⃣ После каждой попытки я показываю:\n"
                        "   🟩 — буква на своём месте\n"
                        "   🟨 — буква есть, но не на этом месте\n"
                        "   ⬛ — такой буквы нет\n\n"
                        "📝 <b>Команды:</b>\n"
                        "/new — начать новую игру\n"
                        "/guess [слово] — сделать догадку\n"
                        "/giveup — сдаться\n"
                        "/stats — моя статистика\n\n"
                        "💡 Начни с команды /new!"
                    )
                    send_message(chat_id, welcome)

                elif text == "/new":
                    start_game(user_id, chat_id)

                elif text.startswith("/guess"):
                    parts = text.split(maxsplit=1)
                    if len(parts) < 2:
                        send_message(
                            chat_id,
                            "❌ Используй: /guess [твоё слово]\nНапример: /guess КОТ",
                        )
                    else:
                        make_guess(user_id, chat_id, parts[1].strip())

                elif text == "/giveup":
                    give_up(user_id, chat_id)

                elif text == "/stats":
                    show_stats(user_id, chat_id)

                else:
                    # Если не команда, но есть активная игра — подсказываем
                    if user_id in games and not games[user_id].get("game_over", False):
                        send_message(
                            chat_id,
                            "❓ Используй /guess [слово] чтобы угадать!\nНапример: /guess КОТ",
                        )
                    else:
                        send_message(
                            chat_id,
                            "❓ Я не понял команду. Используй /start для справки.",
                        )

        return jsonify({"status": "ok"})

    except Exception as e:
        print(f"Ошибка в вебхуке: {e}")
        return jsonify({"status": "error"}), 500


@app.route("/")
def index():
    return "Wordle Bot is running!"


# ========== ЗАПУСК ==========
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
