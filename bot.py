import telebot

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import BOT_TOKEN, LINK_TO_BOT, SHORT_RULES, FULL_RULES, COMMANDS, MIN_PLAYERS

from database import (add_user, add_group, is_group_playing, add_user_to_games, is_user_playing,
                      change_group_state, check_user_exists, increase_session, count_session_users,
                      get_user_current_group_chat_id, update_user_data)

import threading

bot = telebot.TeleBot(token=BOT_TOKEN)


@bot.message_handler(commands=["start"], chat_types=["supergroup"])
def handle_group_start(message):
    add_group(message.chat.id)

    # создаем кнопку для перехода в чат с ботом
    return_to_private_btn = InlineKeyboardButton(text="Чат с ботом", url=LINK_TO_BOT)
    keyboard = InlineKeyboardMarkup().add(return_to_private_btn)

    text = ("Привет! Я бот, позволяющий играть в мафию. Если хотите начать игру, "
            "то используйте команду /start_game.\n\n"
            "Перед началом игры прошу вас убедиться, что все игроки написали мне /start в личные сообщения.\n\n")

    full_text = text + "<b>Правила:</b>\n" + SHORT_RULES  # добавляем краткие правила к приветственному сообщению

    bot.send_message(message.chat.id, full_text, reply_markup=keyboard, parse_mode="html")


@bot.message_handler(commands=["start"], chat_types=["private"])
def handle_private_start(message):
    add_user(message.chat.id)

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


def get_group_link(user_id):
    group_id = get_user_current_group_chat_id(user_id)

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

    if not check_user_exists(user_id):
        return_to_private_btn = InlineKeyboardButton(text="Чат с ботом", url=LINK_TO_BOT)
        keyboard = InlineKeyboardMarkup().add(return_to_private_btn)

        bot.send_message(call.message.chat.id, f"{call.from_user.username}, "
                                               f"пожалуйста, напишите /start в чате со мной.",
                         reply_markup=keyboard)

    elif is_user_playing(user_id):
        bot.answer_callback_query(call.id, "Вы уже присоединились к игре")

    else:
        add_user_to_games(call.message.chat.id, user_id)

        bot.send_message(call.message.chat.id, f"Пользователь {call.from_user.username} готов к игре!")


# функция таймера для начала игры
def start_game_timer(message, delay=30):
    def timer_func():
        joined_players = count_session_users(message.chat.id)

        if joined_players < MIN_PLAYERS:
            bot.send_message(message.chat.id, "Недостаточно игроков для начала игры! Начните набор заново!")

            change_group_state(message.chat.id, 0)

        else:
            # TODO добавить функцию начала игры
            pass

        bot.delete_message(message.chat.id, message.message_id)

    threading.Timer(delay, timer_func).start()


# функция начала игры
@bot.message_handler(commands=["start_game"], chat_types=["supergroup"])
def start_game_handler(message):
    c_id = message.chat.id

    add_group(c_id)

    if is_group_playing(c_id):
        bot.send_message(c_id, "Игра уже начата!")

    else:
        change_group_state(c_id, 1)

        increase_session(c_id)

        bot.send_message(c_id, "Началась подготовка к игре!")

        markup = InlineKeyboardMarkup()
        play_button = InlineKeyboardButton("Готов!", callback_data="ready")
        markup.add(play_button)

        sent_message = bot.send_message(c_id, "Нажмите на кнопку, когда будете готовы!", reply_markup=markup)
        start_game_timer(sent_message)


@bot.callback_query_handler(func=lambda call: call.data is int)
def process_user_votes(call):
    c_id = call.message.chat.id

    voted_user_id = call.from_user.id
    chosen_user_id = call.data

    # add_user_choice(voted_user_id, chosen_user_id) TODO Функция добавления выбора игрока по его айди

    group_chat_id = get_user_current_group_chat_id(voted_user_id)

    # TODO нужно что-то сделать с айди выбранного игрока
    update_user_data(voted_user_id, group_chat_id, "choice", chosen_user_id)

    link_to_group = get_group_link(voted_user_id)

    # создаем кнопку для перехода в группу
    return_to_group_btn = InlineKeyboardButton(text="Вернуться в группу", url=link_to_group)
    return_to_group_keyboard = InlineKeyboardMarkup().add(return_to_group_btn)

    chosen_user_name = bot.get_chat_member(c_id, chosen_user_id)
    bot.edit_message_text(text=f"Ваш выбор: {chosen_user_name}", reply_markup=return_to_group_keyboard)

    voted_user_name = bot.get_chat_member(c_id, voted_user_id)
    bot.send_message(c_id, f"Игрок {voted_user_name} сделал свой выбор.")


def start_voting_timer(message, delay=30):
    def timer_func():
        c_id = message.chat.id

        bot.send_message(c_id, "Голосование завершено!")

        # получаем статус и user_id
        # voting_result = get_voting_results() TODO Функция подсчета голосов на дневном голосовании
        voting_result = []  # временный вариант

        if not voting_result[0]:
            bot.send_message(c_id, "Жители решили никого не убивать сегодня.")

        else:
            killed_user_id = voting_result[1]

            killed_user_name = bot.get_chat_member(c_id, killed_user_id).user.username

            # killed_user_role = get_user_data().role TODO Добавить функцию получения данных об игроке
            killed_user_role = "какая-то роль"

            bot.send_message(c_id, f"Сегодня был изгнан игрок {killed_user_name} с ролью {killed_user_role}")

            update_user_data(voting_result[1], message.chat.id, "killed", 1)

            # make_night_stage() TODO снова переходим в функцию начала ночи

    threading.Timer(delay, timer_func).start()


def make_voting(message, alive_users):
    alive_players_keyboard = InlineKeyboardMarkup()

    for user_info in alive_users:
        btn = InlineKeyboardButton(text=user_info[1], callback_data=user_info[0])
        alive_players_keyboard.add(btn)

    return_to_private_btn = InlineKeyboardButton(text="Чат с ботом", url=LINK_TO_BOT)
    return_to_private_keyboard = InlineKeyboardMarkup().add(return_to_private_btn)

    bot.send_message(message.chat.id, "Настало время голосования! Всех живых игроков прошу перейти в чат со мной.",
                     reply_markup=return_to_private_keyboard)

    for user_info in alive_users:
        bot.send_message(user_info[0], "Пришло время кого-нибудь изгнать! "
                                       "У вас есть 30 секунд на то, чтобы сделать выбор",
                         reply_markup=alive_players_keyboard)

    start_voting_timer(message)


def start_discussion_timer(message, alive_users, delay=180):
    def timer_func():
        make_voting(message, alive_users)

    threading.Timer(delay, timer_func).start()


def make_day_stage(message, killed_user_list: list):
    c_id = message.chat.id
    is_user_killed = killed_user_list[0]

    if not is_user_killed:
        bot.send_message(c_id, "Кажется, мафия не смогла договориться и этой ночью никто не был убит.")

    else:
        killed_user_id = killed_user_list[1]

        killed_user_name = bot.get_chat_member(c_id, killed_user_id).user.username

        bot.send_message(c_id, f"Этой ночью был зверски убит игрок по имени {killed_user_name}")

        update_user_data(killed_user_id, message.chat.id, "killed", 1)

    # alive_users_ids = get_alive_users() TODO Функция для получения списка из телеграм айди живых игроков
    alive_user_ids = []  # временный вариант
    alive_user_names = []

    for user_id in alive_user_ids:
        # delete_choice(user_id) TODO Функция удаления информации и выборе у игрока

        user_name = bot.get_chat_member(message.chat.id, user_id)
        alive_user_names.append(user_name)

    text = "Этой ночью остались в живых:\n\n"

    for i, user_name in enumerate(alive_user_names):
        text += f"{i}. {user_name}\n"

    bot.send_message(c_id, text)

    bot.send_message(c_id, "Настало время для обсуждения! Даю вам 3 минуты!")

    alive_users = []

    for i in range(len(alive_user_ids)):
        alive_users.append([alive_user_ids[i], alive_user_names[i]])

    start_discussion_timer(message, alive_users)


if __name__ == "__main__":
    bot.set_my_commands(COMMANDS)  # Добавляем команды в меню

    bot.infinity_polling()
