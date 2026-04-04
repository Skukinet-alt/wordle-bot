import os
import random
import json
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = "8589671232:AAEovF72xAAODgTKWUUtCQT3XmQbAjZJmmk"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# РАСШИРЕННЫЙ СЛОВАРЬ (более 100 слов)
WORDS = [
    # 3 буквы
    "КОТ", "ДОМ", "ЛЕС", "ПОЛ", "РОТ", "НОС", "СОН", "ДЕНЬ", "НОЧЬ", "ШАР", 
    "МИР", "ГОД", "ЧАС", "БОГ", "РАЙ", "СУП", "ЧАЙ", "СОК", "БАК", "МАК",
    "ЛУК", "ЖУК", "ДУБ", "ЗУБ", "ЛОБ", "ХВОСТ", "БОК", "ТОК", "ВЕК", "ПЕС",
    
    # 4 буквы
    "ТЕНЬ", "ПЕНЬ", "СВЕТ", "ТЬМА", "СНЕГ", "ДОЖДЬ", "КНИГА", "СТОЛ", "СТУЛ", 
    "ОКНО", "ДВЕРЬ", "СТЕНА", "ПОЛКА", "ЛАМПА", "КОСТЬ", "МОСТ", "ХЛЕБ", "МЯСО",
    "РЫБА", "ПТИЦА", "ВОДА", "ЗЕМЛЯ", "НЕБО", "ВЕТЕР", "ГРОЗА", "РЕКА", "ГОРА",
    
    # 5 букв
    "СОЛНЦЕ", "ЗВЕЗДА", "ОБЛАКО", "РЕЧКА", "ПОЛЕ", "ОКЕАН", "РОБОТ", "ПИТОН", 
    "МАШИНА", "ШКОЛА", "КЛАСС", "ПАРТА", "ДОСКА", "МЕЛОК", "РУЧКА", "КНИГА",
    "УЧИТЕЛЬ", "СТУДЕНТ", "ДРУГ", "РАДОСТЬ", "СЧАСТЬЕ", "МЫСЛЬ", "ЖИЗНЬ",
    
    # 6 букв
    "КОМПЬЮТЕР", "ТЕЛЕФОН", "КЛАВИАТУРА", "МЫШКА", "МОНИТОР", "ПАМЯТЬ", 
    "ПРОЦЕССОР", "ДИСК", "ФАЙЛ", "ПАПКА", "КНОПКА", "ЭКРАН", "КЛАВИША",
]

MIN_WORD_LEN = 3
MAX_WORD_LEN = 6

# Хранилище
games = {}
stats = {}

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def send_message(chat_id, text, reply_markup=None):
    """Отправка сообщения с поддержкой кнопок"""
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Ошибка отправки: {e}")
        return None

def send_typing_action(chat_id):
    """Показывает, что бот печатает"""
    url = f"{TELEGRAM_API}/sendChatAction"
    try:
        requests.post(url, json={"chat_id": chat_id, "action": "typing"}, timeout=5)
    except:
        pass

def get_main_keyboard():
    """Главное меню с кнопками"""
    return {
        "keyboard": [
            [{"text": "🎮 Новая игра"}, {"text": "📊 Статистика"}],
            [{"text": "😢 Сдаться"}, {"text": "❓ Помощь"}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }

def get_inline_keyboard(game):
    """Инлайн-кнопки для игры (подсказки)"""
    return {
        "inline_keyboard": [
            [{"text": "🎲 Сдаться", "callback_data": "giveup"}],
            [{"text": "📊 Статистика", "callback_data": "stats"}]
        ]
    }

def get_random_word():
    """Выбирает случайное слово из словаря"""
    return random.choice(WORDS).upper()

def check_guess(guess, target):
    """Проверяет догадку и возвращает результат"""
    guess = guess.upper()
    target = target.upper()
    
    if len(guess) != len(target):
        return None, [], [], []
    
    result = []
    green_letters = []
    yellow_letters = []
    wrong_letters = []
    
    # Находим точные совпадения
    target_copy = list(target)
    guess_copy = list(guess)
    
    for i in range(len(guess)):
        if guess[i] == target[i]:
            result.append("🟩")
            green_letters.append(guess[i])
            target_copy[i] = None
            guess_copy[i] = None
    
    # Находим буквы не на своих местах
    for i in range(len(guess)):
        if guess_copy[i] is not None and guess_copy[i] in target_copy:
            result.append("🟨")
            yellow_letters.append(guess[i])
            idx = target_copy.index(guess[i])
            target_copy[idx] = None
        elif guess_copy[i] is not None:
            result.append("⬛")
            wrong_letters.append(guess[i])
    
    while len(result) < len(guess):
        result.append("⬛")
    
    return "".join(result), green_letters, yellow_letters, wrong_letters

def format_game_state(game):
    """Форматирует текущее состояние игры"""
    target_len = len(game["target"])
    attempts = game["attempts"]
    max_attempts = game["max_attempts"]
    
    # Заголовок
    message = f"<b>🎮 ИГРА WORDLE</b>\n\n"
    message += f"Попытка: <b>{len(attempts) + 1}</b>/{max_attempts}\n"
    message += f"Длина слова: <b>{target_len}</b> букв\n\n"
    
    # Маскировка слова
    if attempts:
        last_attempt = attempts[-1]["word"]
        mask = ""
        for i, letter in enumerate(last_attempt):
            if letter in game["green_positions"] and game["green_positions"][i] == letter:
                mask += f"<b>{letter}</b> "
            elif letter in game["found_letters"]:
                mask += f"<i>{letter}</i> "
            else:
                mask += "_ "
        message += f"<code>{mask.strip()}</code>\n\n"
    else:
        message += f"<code>{'_ ' * target_len}</code>\n\n"
    
    # Список попыток
    if attempts:
        message += "<b>📝 Твои попытки:</b>\n"
        for i, attempt in enumerate(attempts, 1):
            message += f"{i}. {attempt['word']} {attempt['result']}\n"
        message += "\n"
    
    # Подсказки
    all_green = set()
    all_yellow = set()
    all_wrong = set()
    
    for attempt in attempts:
        all_green.update(attempt.get("green", []))
        all_yellow.update(attempt.get("yellow", []))
        all_wrong.update(attempt.get("wrong", []))
    
    if all_green:
        message += f"<b>✅ На своих местах:</b> {', '.join(sorted(all_green))}\n"
    if all_yellow:
        message += f"<b>🟡 Есть в слове:</b> {', '.join(sorted(all_yellow))}\n"
    if all_wrong:
        message += f"<b>❌ Нет в слове:</b> {', '.join(sorted(all_wrong))}\n"
    
    return message

def save_stats(user_id, won):
    """Сохраняет статистику"""
    if user_id not in stats:
        stats[user_id] = {"wins": 0, "losses": 0, "total": 0}
    
    stats[user_id]["total"] += 1
    if won:
        stats[user_id]["wins"] += 1
    else:
        stats[user_id]["losses"] += 1

# ========== ОБРАБОТЧИКИ ==========

def start_game(user_id, chat_id):
    """Начинает новую игру"""
    target_word = get_random_word()
    games[user_id] = {
        "target": target_word,
        "attempts": [],
        "max_attempts": 6,
        "game_over": False,
        "won": False,
        "green_positions": {},
        "found_letters": set()
    }
    
    message = f"<b>🎯 НОВАЯ ИГРА!</b>\n\n"
    message += f"Я загадал слово из <b>{len(target_word)} букв</b>.\n"
    message += f"У тебя <b>{games[user_id]['max_attempts']} попыток</b>.\n\n"
    message += f"💡 <b>Совет:</b> Просто напиши слово, чтобы угадать!\n"
    message += f"❓ Не знаешь слово? Используй кнопку «Сдаться»"
    
    send_message(chat_id, message, get_main_keyboard())

def make_guess(user_id, chat_id, guess_word):
    """Обрабатывает догадку"""
    if user_id not in games or games[user_id].get("game_over", False):
        send_message(chat_id, "❌ У тебя нет активной игры! Нажми «Новая игра»", get_main_keyboard())
        return
    
    game = games[user_id]
    target = game["target"]
    
    # Проверка длины
    if len(guess_word) != len(target):
        send_message(chat_id, f"⚠️ Слово должно быть из <b>{len(target)} букв</b>! Ты отправил {len(guess_word)}.", get_main_keyboard())
        return
    
    # Проверка на окончание игры
    if len(game["attempts"]) >= game["max_attempts"]:
        message = f"💀 <b>ИГРА ОКОНЧЕНА!</b>\n\nЗагаданное слово: <b>{target}</b>\n\nНачни новую игру кнопкой «Новая игра»"
        send_message(chat_id, message, get_main_keyboard())
        game["game_over"] = True
        return
    
    # Проверка догадки
    result, green, yellow, wrong = check_guess(guess_word, target)
    
    if result is None:
        send_message(chat_id, "⚠️ Ошибка! Попробуй ещё раз.", get_main_keyboard())
        return
    
    # Обновляем найденные буквы
    for i, letter in enumerate(guess_word.upper()):
        if letter == target[i]:
            game["green_positions"][i] = letter
            game["found_letters"].add(letter)
        elif letter in target:
            game["found_letters"].add(letter)
    
    # Сохраняем попытку
    game["attempts"].append({
        "word": guess_word.upper(),
        "result": result,
        "green": green,
        "yellow": yellow,
        "wrong": wrong
    })
    
    # ПРОВЕРКА ПОБЕДЫ
    if guess_word.upper() == target:
        game["game_over"] = True
        game["won"] = True
        save_stats(user_id, True)
        
        message = f"<b>🎉 ПОБЕДА! 🎉</b>\n\n"
        message += f"Ты угадал слово <b>{target}</b>!\n"
        message += f"Попыток использовано: <b>{len(game['attempts'])}</b>/{game['max_attempts']}\n\n"
        message += format_game_state(game)
        
        win_rate = 0
        if stats[user_id]["total"] > 0:
            win_rate = (stats[user_id]["wins"] / stats[user_id]["total"]) * 100
        
        message += f"\n📊 <b>Статистика:</b> {stats[user_id]['wins']} побед / {stats[user_id]['losses']} поражений ({win_rate:.0f}%)"
        
        send_message(chat_id, message, get_main_keyboard())
        return
    
    # ПРОВЕРКА ПРОИГРЫША
    if len(game["attempts"]) >= game["max_attempts"]:
        game["game_over"] = True
        save_stats(user_id, False)
        
        message = f"<b>💀 ПОРАЖЕНИЕ!</b>\n\n"
        message += f"Загаданное слово: <b>{target}</b>\n\n"
        message += format_game_state(game)
        
        win_rate = 0
        if stats[user_id]["total"] > 0:
            win_rate = (stats[user_id]["wins"] / stats[user_id]["total"]) * 100
        
        message += f"\n📊 <b>Статистика:</b> {stats[user_id]['wins']} побед / {stats[user_id]['losses']} поражений ({win_rate:.0f}%)"
        
        send_message(chat_id, message, get_main_keyboard())
        return
    
    # ПРОДОЛЖАЕМ ИГРУ
    message = format_game_state(game)
    send_message(chat_id, message, get_main_keyboard())

def give_up(user_id, chat_id):
    """Сдаться"""
    if user_id not in games or games[user_id].get("game_over", False):
        send_message(chat_id, "❌ У тебя нет активной игры!", get_main_keyboard())
        return
    
    game = games[user_id]
    target = game["target"]
    game["game_over"] = True
    save_stats(user_id, False)
    
    message = f"<b>😢 ТЫ СДАЛСЯ</b>\n\n"
    message += f"Загаданное слово: <b>{target}</b>\n\n"
    message += format_game_state(game)
    
    win_rate = 0
    if stats[user_id]["total"] > 0:
        win_rate = (stats[user_id]["wins"] / stats[user_id]["total"]) * 100
    
    message += f"\n📊 <b>Статистика:</b> {stats[user_id]['wins']} побед / {stats[user_id]['losses']} поражений ({win_rate:.0f}%)"
    
    send_message(chat_id, message, get_main_keyboard())

def show_stats(user_id, chat_id):
    """Показывает статистику"""
    if user_id not in stats:
        stats[user_id] = {"wins": 0, "losses": 0, "total": 0}
    
    win_rate = 0
    if stats[user_id]["total"] > 0:
        win_rate = (stats[user_id]["wins"] / stats[user_id]["total"]) * 100
    
    message = f"<b>📊 ТВОЯ СТАТИСТИКА</b>\n\n"
    message += f"🎮 Всего игр: <b>{stats[user_id]['total']}</b>\n"
    message += f"✅ Побед: <b>{stats[user_id]['wins']}</b>\n"
    message += f"❌ Поражений: <b>{stats[user_id]['losses']}</b>\n"
    message += f"📈 Процент побед: <b>{win_rate:.1f}%</b>\n\n"
    
    if stats[user_id]["wins"] > stats[user_id]["losses"]:
        message += "🏆 <i>Ты крут! Продолжай в том же духе!</i>"
    elif stats[user_id]["wins"] == stats[user_id]["losses"]:
        message += "🤝 <i>Поровну! Вперёд к победам!</i>"
    else:
        message += "💪 <i>Ничего, следующая игра будет твоей!</i>"
    
    send_message(chat_id, message, get_main_keyboard())

def show_help(chat_id):
    """Показывает помощь"""
    message = f"<b>❓ ПРАВИЛА ИГРЫ WORDLE</b>\n\n"
    message += f"🎯 <b>Цель:</b> Угадать загаданное слово за 6 попыток\n\n"
    message += f"<b>📝 Как играть:</b>\n"
    message += f"• Просто напиши слово (например: <code>КОТ</code>)\n"
    message += f"• Длина слова подсказывается в начале игры\n"
    message += f"• После каждой попытки ты получаешь подсказки\n\n"
    message += f"<b>🎨 Обозначения:</b>\n"
    message += f"🟩 — буква на своём месте\n"
    message += f"🟨 — буква есть в слове, но не здесь\n"
    message += f"⬛ — такой буквы нет в слове\n\n"
    message += f"<b>🎮 Команды (или кнопки):</b>\n"
    message += f"• Новая игра — начать заново\n"
    message += f"• Статистика — твои успехи\n"
    message += f"• Сдаться — узнать слово и закончить\n\n"
    message += f"💡 <b>Совет:</b> Начинай со слов, которые содержат разные буквы!"
    
    send_message(chat_id, message, get_main_keyboard())

# ========== ВЕБХУК ==========

@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        
        if "message" in data:
            msg = data["message"]
            chat_id = msg["chat"]["id"]
            user_id = str(msg["from"]["id"])
            
            # Показываем, что бот печатает
            send_typing_action(chat_id)
            
            if "text" in msg:
                text = msg["text"].strip()
                
                # Обработка команд и кнопок
                if text == "/start" or text == "❓ Помощь":
                    show_help(chat_id)
                
                elif text == "/new" or text == "🎮 Новая игра":
                    start_game(user_id, chat_id)
                
                elif text == "/stats" or text == "📊 Статистика":
                    show_stats(user_id, chat_id)
                
                elif text == "/giveup" or text == "😢 Сдаться":
                    give_up(user_id, chat_id)
                
                else:
                    # Если есть активная игра — пытаемся угадать
                    if user_id in games and not games[user_id].get("game_over", False):
                        make_guess(user_id, chat_id, text)
                    else:
                        send_message(chat_id, "❓ Нет активной игры! Нажми «Новая игра»", get_main_keyboard())
        
        # Обработка нажатий на инлайн-кнопки
        elif "callback_query" in data:
            callback = data["callback_query"]
            chat_id = callback["message"]["chat"]["id"]
            user_id = str(callback["from"]["id"])
            data_callback = callback["data"]
            
            send_typing_action(chat_id)
            
            if data_callback == "giveup":
                give_up(user_id, chat_id)
            elif data_callback == "stats":
                show_stats(user_id, chat_id)
            
            # Ответ на callback
            requests.post(f"{TELEGRAM_API}/answerCallbackQuery", json={"callback_query_id": callback["id"]})
        
        return jsonify({"status": "ok"})
    
    except Exception as e:
        print(f"Ошибка: {e}")
        return jsonify({"status": "error"}), 500

@app.route("/")
def index():
    return "Wordle Bot is running!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
