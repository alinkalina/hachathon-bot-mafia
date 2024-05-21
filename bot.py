import telebot

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import BOT_TOKEN, LINK_TO_BOT, SHORT_RULES, FULL_RULES, COMMANDS, MIN_PLAYERS

from database import add_user, add_group, is_group_playing, add_user_to_games, is_user_playing, get_group_current_session, start_game_for_group, check

import threading

bot = telebot.TeleBot(token=BOT_TOKEN)


@bot.message_handler(commands=["start"], chat_types=["supergroup"])
def handle_group_start(message):
    # создаем кнопку для перехода в чат с ботом
    return_to_private_btn = InlineKeyboardButton(text="Чат с ботом", url=LINK_TO_BOT)
    keyboard = InlineKeyboardMarkup().add(return_to_private_btn)

    text = ("Привет! Я бот, позволяющий играть в мафию. Если хотите начать игру, "
            "то используйте команду /start_game.\n\n"
            "Перед началом игры прошу вас убедиться, что все игроки написали мне /start в личные сообщения.\n\n")

    full_text = text + "<b>Правила:</b>\n" + SHORT_RULES  # добавляем краткие правила к приветственному сообщению

    bot.send_message(message.chat.id, full_text, reply_markup=keyboard, parse_mode="html")

    add_group(message.chat.id)


@bot.message_handler(commands=["start"], chat_types=["private"])
def handle_private_start(message):
    user_id = message.from_user.id
    link_to_group = get_group_link(user_id)

    text = ("Привет! Я бот, позволяющий играть в мафию. Здесь ты можешь ознакомиться с правилами игры "
            "по команде /rules или можешь вернуться в группу.")

    if link_to_group:
        # создаем кнопку для перехода в группу
        return_to_group_btn = InlineKeyboardButton(text="Вернуться в группу", url=link_to_group)
        keyboard = InlineKeyboardMarkup().add(return_to_group_btn)

        bot.send_message(message.chat.id, text, reply_markup=keyboard)

    else:
        bot.send_message(message.chat.id, text)

    add_user(message.chat.id)


def get_group_link(user_id):
    # group_id = get_group_id(user_id) TODO функция получения айди группы еще не готова
    group_id = ""  # Временный вариант (убрать, когда функция выше будет готова)

    if group_id:
        link_to_group = bot.export_chat_invite_link(chat_id=group_id)  # Создаем ссылку для группы

        return link_to_group


@bot.message_handler(commands=["rules"], chat_types=["private"])
def send_rules(message):
    bot.send_message(message.chat.id, FULL_RULES)


# обработка нажатия на кнопку "Готов!"
@bot.callback_query_handler(func=lambda call: call.data == "ready")
def ready_handler(call):
    user_id = call.from_user.id
    # TODO здесь проверки пользователя на нахождение в базе
    if not check_user_exist(user_id):
        return_to_private_btn = InlineKeyboardButton(text="Чат с ботом", url=LINK_TO_BOT)
        keyboard = InlineKeyboardMarkup().add(return_to_private_btn)
        bot.send_message(call.message.chat.id, "Пожалуйста, напишите /start в чате со мной.", reply_markup=keyboard)
    elif is_user_playing(user_id):
        bot.answer_callback_query(call.id, "Вы уже нажали на кнопку!")
    else:
        add_user_to_games(user_id)
        bot.send_message(call.message.chat.id, f"Пользователь {call.from_user.username} готов к игре!")


# функция таймера для начала игры
def start_game_timer(message, delay=60):
    def timer_func():
        # TODO сделать функцию get_joined_players
        joined_players = get_joined_players(message.chat.id)
        if joined_players < MIN_PLAYERS:
            bot.send_message(message.chat.id, "Недостаточно игроков для начала игры!")
            return
        else:
            # TODO добавить функцию начала игры
            pass
        bot.delete_message(message.chat.id, message.message_id)

    threading.Timer(delay, timer_func).start()


# функция начала игры
@bot.message_handler(commands=["start_game"], chat_types=["supergroup"]
def start_game_handler(message):
    if is_group_playing(message.chat.id):
        bot.send_message(message.chat.id, "Игра уже начата!")
    else:
        start_game_for_group(message.chat.id)
        session = get_group_current_session(message.chat.id)
        bot.send_message(message.chat.id, "Началась подготовка к игре!")
        markup = InlineKeyboardMarkup()
        play_button = InlineKeyboardButton("Готов!", callback_data="ready")
        markup.add(play_button)
        sent_message = bot.send_message(message.chat.id, "Нажмите на кнопку, когда будете готовы!", reply_markup=markup)
        start_game_timer(sent_message)


if __name__ == "__main__":
    bot.set_my_commands(COMMANDS)  # Добавляем команды в меню

    bot.infinity_polling()
