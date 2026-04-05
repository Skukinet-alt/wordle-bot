import os
import random
import json
from flask import Flask, request, jsonify
import requests
from collections import Counter

app = Flask(__name__)

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = "8589671232:AAEovF72xAAODgTKWUUtCQT3XmQbAjZJmmk"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ОСНОВНОЙ СЛОВАРЬ (для случайного и классического режимов)
WORDS = [
    # 3 буквы
    "КОТ", "ДОМ", "ЛЕС", "ПОЛ", "РОТ", "НОС", "СОН", "ДЕНЬ", "НОЧЬ", "ШАР", 
    "МИР", "ГОД", "ЧАС", "БОГ", "РАЙ", "СУП", "ЧАЙ", "СОК", "БАК", "МАК",
    "ЛУК", "ЖУК", "ДУБ", "ЗУБ", "ЛОБ", "БОК", "ТОК", "ВЕК", "ПЕС", "ЛЕВ",
    
    # 4 буквы
    "ТЕНЬ", "ПЕНЬ", "СВЕТ", "ТЬМА", "СНЕГ", "ДОЖДЬ", "СТОЛ", "СТУЛ", 
    "ОКНО", "СТЕНА", "ПОЛКА", "ЛАМПА", "КОСТЬ", "МОСТ", "ХЛЕБ", "МЯСО",
    "РЫБА", "ВОДА", "ЗЕМЛЯ", "НЕБО", "ВЕТЕР", "ГРОЗА", "РЕКА", "ГОРА", "ПОЛЕ",
    
    # 5 букв
    "КНИГА", "СОЛНЦЕ", "ЗВЕЗДА", "ОБЛАКО", "РЕЧКА", "ОКЕАН", "РОБОТ", "ПИТОН", 
    "МАШИНА", "ШКОЛА", "КЛАСС", "ПАРТА", "ДОСКА", "МЕЛОК", "РУЧКА", "ДВЕРЬ",
    "УЧИТЕЛЬ", "СТУДЕНТ", "ДРУГ", "РАДОСТЬ", "СЧАСТЬЕ", "МЫСЛЬ", "ЖИЗНЬ", "СМЕРТЬ",
    "БАНАН", "ЯБЛОКО", "АПЕЛЬСИН", "ЛИМОН", "ВИШНЯ", "ГРУША",
    
    # 6 букв
    "МЫШКА", "ПАМЯТЬ", "ДИСК", "ФАЙЛ", "ПАПКА", "КНОПКА", "ЭКРАН", "КЛАВИША"
]

# МЕДИЦИНСКИЙ СЛОВАРЬ (РЕЖИМ СЛУЧАЙНОЙ ДЛИНЫ - ВСЕГДА)
MEDICAL_WORDS = [
    # 3-4 буквы
    "ЛУЧ", "ДОЗА", "ЙОД", "АТОМ", "СИЗ", "САЗ", "МРТ", "КТ", "УЗИ", "ЭКГ",
    "БИОПСИЯ", "ВЕНА", "КОСТЬ", "ЗУБ", "НОС", "РОТ", "ГЛАЗ", "УХО", "ПЕЧЕНЬ",
    
    # 5-6 букв
    "МАГНИТ", "ШОК", "ФОКУС", "МОНИТОР", "АППАРАТ", "ИСТОЧНИК", "ДУГА", "ЧЕРЕП",
    "СНИМОК", "СТОЙКА", "ИНЖЕКТОР", "КАТЕТЕР", "ФАРТУК", "ЛАБОРАНТ", "КОМЕТА",
    "КРЕАТИНИН", "ГАДОЛИНИЙ", "ВОДОРОД", "УЛЬТРАВИСТ", "ДОЗИМЕТР", "ЗИВЕРТ",
    
    # 7-8 букв
    "РЕНТГЕН", "УКЛАДКА", "КОНТРАСТ", "ПЛОСКОСТЬ", "НАПРАВЛЕНИЕ", "ИССЛЕДОВАНИЕ",
    "РАССТОЯНИЕ", "РЕНТГЕНОЛОГИЯ", "ИРРИГОСКОПИЯ", "ФИСТУЛА", "ЕРИС",
    
    # 9+ букв
    "РЕНТГЕНОЛОГ", "РЕНТГЕНОВСКИЙ", "РЕНТГЕНОДИАГНОСТИКА"
]

# Хранилище
games = {}
stats = {}
user_modes = {}  # "random", "classic", "medical"

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
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Ошибка отправки: {e}")

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
            [{"text": "🎮 Новая игра"}, {"text": "⚙️ Сменить режим"}],
            [{"text": "📊 Статистика"}, {"text": "😢 Сдаться"}],
            [{"text": "❓ Помощь"}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }

def get_mode_keyboard():
    """Клавиатура выбора режима"""
    return {
        "keyboard": [
            [{"text": "🎲 Случайная длина"}, {"text": "📖 Классика (5 букв)"}],
            [{"text": "🏥 Медицинский"}, {"text": "🔙 Назад в меню"}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }

def get_words_by_length(words_list, length):
    """Возвращает список слов заданной длины из указанного словаря"""
    return [word for word in words_list if len(word) == length]

def get_random_word_by_mode(mode):
    """Возвращает слово в зависимости от выбранного режима"""
    if mode == "classic":
        # Классика: только слова из 5 букв из основного словаря
        five_letter_words = get_words_by_length(WORDS, 5)
        if five_letter_words:
            return random.choice(five_letter_words).upper()
        else:
            return random.choice(WORDS).upper()
    elif mode == "medical":
        # Медицинский: случайное слово из медицинского словаря (любой длины)
        return random.choice(MEDICAL_WORDS).upper()
    else:
        # Случайная длина: из основного словаря (от 3 до 6 букв)
        return random.choice(WORDS).upper()

def check_guess(guess, target):
    """Проверка догадки с учётом повторяющихся букв"""
    guess = guess.upper()
    target = target.upper()
    
    if len(guess) != len(target):
        return None, [], [], []
    
    target_letters = Counter(target)
    
    result = ['⬛'] * len(guess)
    green_letters = []
    yellow_letters = []
    
    used_in_target = [False] * len(target)
    
    # Первый проход: зелёные
    for i in range(len(guess)):
        if guess[i] == target[i]:
            result[i] = '🟩'
            green_letters.append(guess[i])
            used_in_target[i] = True
            target_letters[guess[i]] -= 1
    
    # Второй проход: жёлтые
    for i in range(len(guess)):
        if result[i] == '🟩':
            continue
        
        if guess[i] in target and target_letters[guess[i]] > 0:
            for j in range(len(target)):
                if target[j] == guess[i] and not used_in_target[j]:
                    result[i] = '🟨'
                    yellow_letters.append(guess[i])
                    used_in_target[j] = True
                    target_letters[guess[i]] -= 1
                    break
    
    # Неправильные буквы
    wrong_letters = []
    guess_letters = Counter(guess)
    for letter in guess_letters:
        if letter not in target:
            wrong_letters.append(letter)
    
    return "".join(result), list(dict.fromkeys(green_letters)), list(dict.fromkeys(yellow_letters)), wrong_letters

def get_mask(game):
    """Создаёт маску слова на основе всех попыток"""
    target_len = len(game["target"])
    mask = ['_'] * target_len
    
    for attempt in game["attempts"]:
        word = attempt["word"]
        for i, letter in enumerate(word):
            if i < len(mask) and letter == game["target"][i]:
                mask[i] = letter
    
    return ' '.join(mask)

def format_game_state(game):
    """Форматирует текущее состояние игры"""
    target_len = len(game["target"])
    attempts = game["attempts"]
    max_attempts = game["max_attempts"]
    
    message = f"<b>🎮 ИГРА WORDLE</b>\n\n"
    message += f"Попытка: <b>{len(attempts) + 1}</b>/{max_attempts}\n"
    message += f"Длина слова: <b>{target_len}</b> букв\n\n"
    
    mask = get_mask(game)
    message += f"<code>{mask}</code>\n\n"
    
    if attempts:
        message += "<b>📝 Твои попытки:</b>\n"
        for i, attempt in enumerate(attempts, 1):
            message += f"{i}. {attempt['word']} {attempt['result']}\n"
        message += "\n"
    
    all_green = set()
    all_yellow = set()
    all_wrong = set()
    
    for attempt in attempts:
        all_green.update(attempt.get("green", []))
        all_yellow.update(attempt.get("yellow", []))
        all_wrong.update(attempt.get("wrong", []))
    
    all_yellow = all_yellow - all_green
    all_wrong = all_wrong - all_green - all_yellow
    
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

def show_mode_settings(chat_id):
    """Показывает настройки выбора режима"""
    current_mode = user_modes.get(str(chat_id), "random")
    
    if current_mode == "random":
        mode_text = "🎲 Случайная длина"
        mode_desc = "слова от 3 до 6 букв из общего словаря"
    elif current_mode == "classic":
        mode_text = "📖 Классика (5 букв)"
        mode_desc = "слова только из 5 букв"
    else:
        mode_text = "🏥 Медицинский"
        mode_desc = "медицинские термины разной длины"
    
    message = f"<b>⚙️ НАСТРОЙКИ РЕЖИМА</b>\n\n"
    message += f"Текущий режим: <b>{mode_text}</b>\n"
    message += f"({mode_desc})\n\n"
    message += f"<b>📖 Классика (5 букв):</b>\n"
    message += f"• Слова только из 5 букв\n"
    message += f"• Как в оригинальной Wordle\n\n"
    message += f"<b>🎲 Случайная длина:</b>\n"
    message += f"• Слова от 3 до 6 букв\n"
    message += f"• Обычные слова\n\n"
    message += f"<b>🏥 Медицинский:</b>\n"
    message += f"• Медицинские термины\n"
    message += f"• Слова разной длины (3-12+ букв)\n"
    message += f"• Сложный уровень\n\n"
    message += f"Выбери режим кнопкой ниже:"
    
    send_message(chat_id, message, get_mode_keyboard())

def set_mode(chat_id, mode):
    """Устанавливает режим игры для пользователя"""
    user_modes[str(chat_id)] = mode
    
    if mode == "random":
        mode_name = "🎲 Случайная длина"
        mode_desc = "буду загадывать обычные слова от 3 до 6 букв"
    elif mode == "classic":
        mode_name = "📖 Классика (5 букв)"
        mode_desc = "буду загадывать слова только из 5 букв"
    else:
        mode_name = "🏥 Медицинский"
        mode_desc = "буду загадывать медицинские термины (сложный уровень!)"
    
    send_message(chat_id, f"✅ Режим изменён на: <b>{mode_name}</b>\n\n{mode_desc}\n\nНажми «🎮 Новая игра» чтобы начать!", get_main_keyboard())

def start_game(user_id, chat_id):
    """Начинает новую игру с учётом выбранного режима"""
    mode = user_modes.get(str(chat_id), "random")
    target_word = get_random_word_by_mode(mode)
    
    games[user_id] = {
        "target": target_word,
        "attempts": [],
        "max_attempts": 6,
        "game_over": False,
        "won": False
    }
    
    if mode == "random":
        mode_text = "🎲 случайная длина"
        mode_desc = f"Я загадал слово из <b>{len(target_word)} букв</b>"
    elif mode == "classic":
        mode_text = "📖 классика (5 букв)"
        mode_desc = f"Я загадал слово из <b>5 букв</b>"
    else:
        mode_text = "🏥 медицинский"
        mode_desc = f"Я загадал медицинский термин из <b>{len(target_word)} букв</b>"
    
    message = f"<b>🎯 НОВАЯ ИГРА!</b>\n\n"
    message += f"Режим: <b>{mode_text}</b>\n"
    message += f"{mode_desc}\n"
    message += f"У тебя <b>{games[user_id]['max_attempts']} попыток</b>.\n\n"
    message += f"💡 Просто напиши слово, чтобы угадать!\n"
    message += f"❓ Не знаешь слово? Используй кнопку «Сдаться»\n"
    message += f"Попытка 1/{games[user_id]['max_attempts']}"
    
    send_message(chat_id, message, get_main_keyboard())

def make_guess(user_id, chat_id, guess_word):
    """Обрабатывает догадку"""
    if user_id not in games or games[user_id].get("game_over", False):
        send_message(chat_id, "❌ У тебя нет активной игры! Нажми «Новая игра»", get_main_keyboard())
        return
    
    game = games[user_id]
    target = game["target"]
    
    if len(guess_word) != len(target):
        send_message(chat_id, f"⚠️ Слово должно быть из <b>{len(target)} букв</b>! Ты отправил {len(guess_word)}.", get_main_keyboard())
        return
    
    if len(game["attempts"]) >= game["max_attempts"]:
        message = f"💀 <b>ИГРА ОКОНЧЕНА!</b>\n\nЗагаданное слово: <b>{target}</b>\n\nНачни новую игру кнопкой «Новая игра»"
        send_message(chat_id, message, get_main_keyboard())
        game["game_over"] = True
        return
    
    result, green, yellow, wrong = check_guess(guess_word, target)
    
    if result is None:
        send_message(chat_id, "⚠️ Ошибка! Попробуй ещё раз.", get_main_keyboard())
        return
    
    game["attempts"].append({
        "word": guess_word.upper(),
        "result": result,
        "green": green,
        "yellow": yellow,
        "wrong": wrong
    })
    
    # Победа
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
    
    # Поражение
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
    
    # Продолжаем
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
    message += f"<b>⚙️ Режимы игры:</b>\n"
    message += f"• <b>Классика (5 букв)</b> — всегда слова из 5 букв\n"
    message += f"• <b>Случайная длина</b> — слова от 3 до 6 букв\n"
    message += f"• <b>Медицинский</b> — медицинские термины (сложный уровень)\n\n"
    message += f"<b>🎨 Обозначения:</b>\n"
    message += f"🟩 — буква на своём месте\n"
    message += f"🟨 — буква есть в слове, но не здесь\n"
    message += f"⬛ — такой буквы нет в слове\n\n"
    message += f"<b>💡 Важно:</b>\n"
    message += f"• Если буква встречается в слове один раз, а ты ввёл её дважды — вторая будет ⬛\n"
    message += f"• Маска показывает только угаданные буквы на своих местах\n\n"
    message += f"<b>🎮 Команды (или кнопки):</b>\n"
    message += f"• Новая игра — начать заново\n"
    message += f"• Сменить режим — выбрать сложность\n"
    message += f"• Статистика — твои успехи\n"
    message += f"• Сдаться — узнать слово и закончить"
    
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
            
            send_typing_action(chat_id)
            
            if "text" in msg:
                text = msg["text"].strip()
                
                if text == "/start" or text == "❓ Помощь":
                    show_help(chat_id)
                
                elif text == "/new" or text == "🎮 Новая игра":
                    start_game(user_id, chat_id)
                
                elif text == "/mode" or text == "⚙️ Сменить режим":
                    show_mode_settings(chat_id)
                
                elif text == "🎲 Случайная длина":
                    set_mode(chat_id, "random")
                
                elif text == "📖 Классика (5 букв)":
                    set_mode(chat_id, "classic")
                
                elif text == "🏥 Медицинский":
                    set_mode(chat_id, "medical")
                
                elif text == "🔙 Назад в меню":
                    send_message(chat_id, "🔙 Возврат в главное меню", get_main_keyboard())
                
                elif text == "/stats" or text == "📊 Статистика":
                    show_stats(user_id, chat_id)
                
                elif text == "/giveup" or text == "😢 Сдаться":
                    give_up(user_id, chat_id)
                
                else:
                    if user_id in games and not games[user_id].get("game_over", False):
                        make_guess(user_id, chat_id, text)
                    else:
                        send_message(chat_id, "❓ Нет активной игры! Нажми «Новая игра»", get_main_keyboard())
        
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
