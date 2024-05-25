import telebot
from telebot.storage import StateMemoryStorage
from telebot import custom_filters
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import (BOT_TOKEN, LINK_TO_BOT, SHORT_RULES, FULL_RULES, COMMANDS, MIN_NUM_PLAYERS, ROLES, CONTENT_TYPES,
                    MyStates, START_GAME_DELAY, MAFIA_DELAY, COMMISSAR_DELAY, DISCUSSION_DELAY, VOTING_DELAY)

from database import (add_user, add_group, is_group_playing, add_user_to_games, is_user_playing,
                      change_group_state, check_user_exists, increase_session, get_players_list,
                      get_user_current_group_chat_id, update_user_data, get_user_data, get_alive_users,
                      get_users_with_role)

from process_votes import count_votes
import random
import threading

storage = StateMemoryStorage()

bot = telebot.TeleBot(token=BOT_TOKEN, state_storage=storage)
bot.add_custom_filter(custom_filters.StateFilter(bot))


@bot.message_handler(commands=["start"], chat_types=["supergroup"])
def handle_group_start(message):
    group_chat_id = message.chat.id

    add_group(group_chat_id)

    if is_group_playing(group_chat_id):
        bot.delete_message(group_chat_id, message.message_id)
        return

    bot_link_keyboard = get_bot_link_keyboard()

    text = ("Привет! Я бот, позволяющий играть в мафию. Если хотите начать игру, "
            "то используйте команду /start_game.\n\n"
            "Перед началом игры прошу вас убедиться, что все игроки написали мне /start в личные сообщения.\n\n")

    full_text = text + "<b>Правила:</b>\n" + SHORT_RULES  # добавляем краткие правила к приветственному сообщению

    bot.send_message(group_chat_id, full_text, reply_markup=bot_link_keyboard, parse_mode="html")


@bot.message_handler(commands=["start"], chat_types=["private"])
def handle_private_start(message):
    user_id = message.from_user.id

    if not check_user_exists(user_id):
        add_user(user_id)

    text = ("Привет! Я бот, позволяющий играть в мафию. Здесь ты можешь ознакомиться с правилами игры "
            "по команде /rules или можешь вернуться в группу.")

    group_link_keyboard = get_group_link_keyboard(user_id)

    if group_link_keyboard:
        bot.send_message(message.chat.id, text, reply_markup=group_link_keyboard)

    else:
        bot.send_message(message.chat.id, text)


# создаем кнопку для перехода в группу
def get_group_link_keyboard(user_id):
    group_chat_id = get_user_current_group_chat_id(user_id)

    if group_chat_id:
        group_link = bot.create_chat_invite_link(chat_id=group_chat_id).invite_link

        group_link_button = InlineKeyboardButton(text="Вернуться в группу", url=group_link)
        group_link_keyboard = InlineKeyboardMarkup().add(group_link_button)

        return group_link_keyboard


# создаем кнопку для перехода в чат с ботом
def get_bot_link_keyboard():
    bot_link_button = InlineKeyboardButton(text="Чат с ботом", url=LINK_TO_BOT)
    bot_link_keyboard = InlineKeyboardMarkup().add(bot_link_button)

    return bot_link_keyboard


@bot.message_handler(commands=["rules"])
def send_rules(message):
    if message.chat.type == "private":  # отправляем полные правила только в личных сообщениях
        bot.send_message(message.chat.id, FULL_RULES, parse_mode="html")

    else:
        bot_link_keyboard = get_bot_link_keyboard()
        bot.send_message(message.chat.id, "Для того, чтобы узнать полные правила "
                                          "используйте команду /rules в чате со мной.", reply_markup=bot_link_keyboard)


# функция начала игры
@bot.message_handler(commands=["start_game"], chat_types=["supergroup"])
def start_game_handler(message):
    group_chat_id = message.chat.id

    add_group(group_chat_id)

    if is_group_playing(group_chat_id):
        bot.send_message(group_chat_id, "Игра уже начата!")

    else:
        change_group_state(group_chat_id, 1)

        increase_session(group_chat_id)

        bot.send_message(group_chat_id, "Началась подготовка к игре!")

        ready_keyboard = InlineKeyboardMarkup()
        ready_button = InlineKeyboardButton("Готов!", callback_data="ready")
        ready_keyboard.add(ready_button)

        msg_with_button = bot.send_message(group_chat_id, "Нажмите на кнопку, когда будете готовы!",
                                           reply_markup=ready_keyboard)

        start_game_timer(message, msg_with_button)


# функция таймера для начала игры
def start_game_timer(message, msg_with_button):
    def start_the_game():
        group_chat_id = message.chat.id

        num_joined_players = len(get_players_list(group_chat_id))

        if num_joined_players < MIN_NUM_PLAYERS:
            bot.send_message(group_chat_id, "Недостаточно игроков для начала игры! Начните набор заново!")

            change_group_state(group_chat_id, 0)

        else:
            assign_roles(group_chat_id)
            make_mafia_stage(message)

        bot.delete_message(group_chat_id, msg_with_button.message_id)

    threading.Timer(START_GAME_DELAY, start_the_game).start()


# функция назначения ролей для игры
def assign_roles(group_chat_id):
    player_chat_ids = get_players_list(group_chat_id)
    num_players = len(player_chat_ids)
    num_mafia = num_players // 3
    num_citizens = num_players - num_mafia - (len(ROLES) - 2)

    roles = []
    for role in ROLES:
        if role == "Мафия":
            for i in range(num_mafia):
                roles.append(role)

        elif role == "Комиссар":
            roles.append(role)

        else:
            for i in range(num_citizens):
                roles.append(role)

    random.shuffle(roles)

    for user_id, role in zip(player_chat_ids, roles):
        update_user_data(user_id, group_chat_id, "role", role)

        bot.send_message(user_id, f"Ваша роль - {role}")


# функция ночной фазы
def make_mafia_stage(message):
    group_chat_id = message.chat.id

    alive_players = get_alive_users(group_chat_id)
    mafia_chat_ids = get_users_with_role(group_chat_id, "Мафия")

    for user_id in alive_players:  # удаление выбора при наступлении ночи
        update_user_data(user_id, group_chat_id, param="choice", data=None)

    bot_link_keyboard = get_bot_link_keyboard()

    bot.send_message(group_chat_id, "Наступила ночь! Мафия, просыпайтесь и выберите жертву!",
                     reply_markup=bot_link_keyboard)

    for mafia_chat_id in mafia_chat_ids:
        players_to_kill_keyboard = InlineKeyboardMarkup()

        for alive_player_id in alive_players:  # создаем клавиатуру для мафии
            if alive_player_id not in mafia_chat_ids:  # мафия не должна быть в этом списке
                player_to_kill_name = str(bot.get_chat_member(group_chat_id, alive_player_id).user.username)

                player_to_kill_btn = InlineKeyboardButton(text=player_to_kill_name,
                                                          callback_data=f"mafia {alive_player_id}")

                players_to_kill_keyboard.add(player_to_kill_btn)

        msg_with_button = bot.send_message(mafia_chat_id, "Выберите жертву!", reply_markup=players_to_kill_keyboard)

        save_message_id(mafia_chat_id, msg_with_button)

    start_mafia_timer(message)


# функция ночного таймера
def start_mafia_timer(message):
    def end_mafia_stage():

        for mafia_chat_id in mafia_chat_ids:
            choice = get_user_data(mafia_chat_id, group_chat_id, "choice")

            if choice is None:  # если игрок мафии ничего не выбрал
                group_link_keyboard = get_group_link_keyboard(mafia_chat_id)

                with bot.retrieve_data(mafia_chat_id, mafia_chat_id) as data:  # достаем id сообщения с кнопками
                    msg_with_button_id = data["msg_with_button_id"]

                    bot.edit_message_text(chat_id=mafia_chat_id, message_id=msg_with_button_id,
                                          text="Этой ночью вы никого не выбрали!",
                                          reply_markup=group_link_keyboard)

        for alive_chat_id in alive_players:
            bot.delete_state(alive_chat_id, alive_chat_id)

        bot.send_message(group_chat_id, "Мафия закончила обсуждение.")

        start_commissar_timer(message)

    group_chat_id = message.chat.id

    alive_players = get_alive_users(group_chat_id)

    for alive_player_id in alive_players:  # добавляем состояние живым пользователям, чтобы они не могли писать ночью
        bot.set_state(alive_player_id, MyStates.message_to_delete, group_chat_id)

    mafia_chat_ids = get_users_with_role(group_chat_id, "Мафия")

    for mafia_chat_id in mafia_chat_ids:

        if len(mafia_chat_ids) > 1:  # если в игре больше одной мафии, добавляем для них чат
            bot.send_message(mafia_chat_id, "Даю вам минуту на то, чтобы сделать свой выбор!\n\n"
                                            "P.S. вы можете обсудить его прямо тут с другими участниками мафии.")

            bot.set_state(mafia_chat_id, MyStates.mafia_chat, mafia_chat_id)  # создаем состояние для общения мафии

    threading.Timer(MAFIA_DELAY, end_mafia_stage).start()


# таймер для комиссара
def start_commissar_timer(message):
    def end_commissar_stage():

        if commissar_chat_id in alive_players:

            group_link_keyboard = get_group_link_keyboard(commissar_chat_id)

            with bot.retrieve_data(commissar_chat_id, commissar_chat_id) as data:
                msg_with_button_id = data["msg_with_button_id"]

                bot.edit_message_text(chat_id=commissar_chat_id, message_id=msg_with_button_id,
                                      text="Возвращайтесь в группу",
                                      reply_markup=group_link_keyboard)

            bot.delete_state(commissar_chat_id, commissar_chat_id)

        bot.send_message(group_chat_id, "Комиссар проверил игрока")

        for alive_chat_id in alive_players:
            bot.delete_state(alive_chat_id, group_chat_id)

        mafia_chat_ids = get_users_with_role(group_chat_id, "Мафия")
        killed_player = count_votes(group_chat_id, mafia_chat_ids)

        if killed_player is not None:
            update_user_data(killed_player, group_chat_id, "killed", 1)
            bot.send_message(group_chat_id,
                             f"Мафия убила игрока "
                             f"{str(bot.get_chat_member(group_chat_id, killed_player).user.username)}")
        else:
            bot.send_message(group_chat_id, "Мафия не смогла договориться и никого не убила")

        make_day_stage(message)

    group_chat_id = message.chat.id
    alive_players = get_alive_users(group_chat_id)

    bot_link_keyboard = get_bot_link_keyboard()

    bot.send_message(group_chat_id, "Комиссар, просыпайся и проверь игрока!",
                     reply_markup=bot_link_keyboard)

    commissar_chat_id = get_users_with_role(group_chat_id, "Комиссар")[0]

    if commissar_chat_id in alive_players:
        players_to_check_keyboard = InlineKeyboardMarkup()

        for alive_player_id in alive_players:  # создаем кнопки для комиссара
            if alive_player_id != commissar_chat_id:
                player_to_check_name = str(bot.get_chat_member(group_chat_id, alive_player_id).user.username)

                player_to_check_btn = InlineKeyboardButton(text=player_to_check_name,
                                                           callback_data=f"commissar {alive_player_id}")

                players_to_check_keyboard.add(player_to_check_btn)

        msg_with_button = bot.send_message(commissar_chat_id, "Проверьте роль игрока!",
                                           reply_markup=players_to_check_keyboard)

        save_message_id(commissar_chat_id, msg_with_button)

    threading.Timer(COMMISSAR_DELAY, end_commissar_stage).start()


# функция для удаления сообщений во время ночи
@bot.message_handler(state=MyStates.message_to_delete)
def delete_forbidden_messages(message):
    user_id = message.from_user.id
    group_chat_id = get_user_current_group_chat_id(user_id)

    if message.chat.type == "supergroup":
        bot.delete_message(group_chat_id, message.message_id)


def save_message_id(user_id, msg_with_buttons):  # запоминаем id сообщения с кнопкой для будущего взаимодействия с ним
    bot.set_state(user_id, MyStates.msg_with_buttons, user_id)

    with bot.retrieve_data(user_id, user_id) as data:
        data["msg_with_button_id"] = msg_with_buttons.message_id


# функция для чата мафии
@bot.message_handler(state=MyStates.mafia_chat)
def mafia_chat(message):
    user_id = message.from_user.id
    group_chat_id = get_user_current_group_chat_id(user_id)

    mafia_chat_ids = get_users_with_role(group_chat_id, "Мафия")

    for mafia_chat_id in mafia_chat_ids:
        if mafia_chat_id != user_id:
            bot.send_message(mafia_chat_id, f"{message.from_user.username}: {message.text}")


def make_day_stage(message):
    group_chat_id = message.chat.id

    alive_players = get_alive_users(group_chat_id)

    for alive_player_id in alive_players:  # удаляем выбор игрока при наступлении дня
        update_user_data(alive_player_id, group_chat_id, "choice", None)

    # проверяем, не закончилась ли игра
    is_game_end = check_game_end(group_chat_id)

    if is_game_end:
        return

    text = "Этой ночью остались в живых:\n\n"

    for i, alive_player_id in enumerate(alive_players):  # выводим список живых игроков с нумерацией
        alive_player_name = str(bot.get_chat_member(group_chat_id, alive_player_id).user.username)

        text += f"{i + 1}. {alive_player_name}\n"

    bot.send_message(group_chat_id, text)

    bot.send_message(group_chat_id, "Настало время для обсуждения! Даю вам 3 минуты!")

    start_discussion_timer(message)


def start_discussion_timer(message):
    def timer_func():  # начинаем голосование по окончании таймера
        make_voting(message)

    threading.Timer(DISCUSSION_DELAY, timer_func).start()


def make_voting(message):
    group_chat_id = message.chat.id

    alive_players = get_alive_users(group_chat_id)

    alive_players_keyboard = InlineKeyboardMarkup()

    for alive_player_id in alive_players:  # создаем список живых игроков для голосования
        alive_player_name = str(bot.get_chat_member(group_chat_id, alive_player_id).user.username)

        alive_players_btn = InlineKeyboardButton(text=alive_player_name, callback_data=f"all {alive_player_id}")

        alive_players_keyboard.add(alive_players_btn)

    bot_link_keyboard = get_bot_link_keyboard()

    bot.send_message(message.chat.id, "Настало время голосования! Всех живых игроков прошу перейти в чат со мной.",
                     reply_markup=bot_link_keyboard)

    for alive_player_id in alive_players:
        msg_with_button = bot.send_message(alive_player_id, "Пришло время кого-нибудь изгнать! "
                                                            "У вас есть 30 секунд на то, чтобы сделать выбор",
                                           reply_markup=alive_players_keyboard)

        save_message_id(alive_player_id, msg_with_button)

    start_voting_timer(message)


def start_voting_timer(message):
    def end_voting():
        group_chat_id = message.chat.id

        bot.send_message(group_chat_id, "Голосование завершено!")

        alive_players = get_alive_users(group_chat_id)

        exiled_player = count_votes(group_chat_id, alive_players)

        for alive_user_chat_id in alive_players:  # получаем выбор живых игроков на голосовании
            choice = get_user_data(alive_user_chat_id, group_chat_id, "choice")

            if choice is None:  # если игрок ничего не выбрал
                group_link_keyboard = get_group_link_keyboard(alive_user_chat_id)

                with bot.retrieve_data(alive_user_chat_id, alive_user_chat_id) as data:
                    msg_with_button_id = data["msg_with_button_id"]

                    bot.edit_message_text(chat_id=alive_user_chat_id, message_id=msg_with_button_id,
                                          text="Сегодня вы решили никого не выгонять.",
                                          reply_markup=group_link_keyboard)

        if not exiled_player:
            bot.send_message(group_chat_id, "Жители решили никого не убивать сегодня.")

        else:
            exiled_player_name = str(bot.get_chat_member(group_chat_id, exiled_player).user.username)

            text = f"Сегодня был изгнан игрок {exiled_player_name}.\n\n"

            exiled_player_role = get_user_data(exiled_player, group_chat_id, "role")

            if exiled_player_role.lower() == "мафия":
                text += "Он был мафией."  # не раскрываем роль полностью

            else:
                text += "Он не был мафией."

            bot.send_message(group_chat_id, text)

            update_user_data(exiled_player, message.chat.id, "killed", 1)

            # проверяем, не закончилась ли игра
            is_game_end = check_game_end(group_chat_id)

            if is_game_end:
                return

        make_mafia_stage(message)

    threading.Timer(VOTING_DELAY, end_voting).start()


def check_game_end(group_chat_id):
    winners_list = []
    text = ""

    alive_players = get_alive_users(group_chat_id)

    mafia_chat_ids = get_users_with_role(group_chat_id, "Мафия")

    pieceful_player_ids = sorted(list(set(alive_players) - set(mafia_chat_ids)))

    if len(pieceful_player_ids) <= len(mafia_chat_ids):
        text = "Мафия выиграла!\n\n"
        winners_list = mafia_chat_ids

    elif len(mafia_chat_ids) == 0:
        text = "Мирные жители смогли побороть мафию!\n\n"
        winners_list = pieceful_player_ids

    if winners_list:  # если условия выше выполнены
        text += "Победившие игроки:\n"

        for i, user_id in enumerate(winners_list):
            winner_name = str(bot.get_chat_member(group_chat_id, user_id).user.username)

            text += f"{i + 1}. {winner_name}\n"

        bot.send_message(group_chat_id, text)

        change_group_state(group_chat_id, 0)

        return True

    return False


# обработка нажатия на кнопку "Готов!"
@bot.callback_query_handler(func=lambda call: call.data == "ready")
def ready_handler(call):
    user_id = call.from_user.id
    c_id = call.message.chat.id
    m_id = call.message.message_id

    if not check_user_exists(user_id):
        bot_link_keyboard = get_bot_link_keyboard()

        bot.send_message(c_id, f"{call.from_user.username}, пожалуйста, напишите /start в чате со мной.",
                         reply_markup=bot_link_keyboard)

    elif is_user_playing(user_id):
        bot.answer_callback_query(call.id, "Вы уже присоединились к игре")

    else:
        add_user_to_games(c_id, user_id)

        ready_user_ids = get_players_list(c_id)

        text = ("Нажмите на кнопку, когда будете готовы!\n\n"
                "Присоединившиеся игроки:\n")

        for i, ready_user_id in enumerate(ready_user_ids):
            ready_user_name = str(bot.get_chat_member(c_id, ready_user_id).user.username)

            text += f"{i + 1}. {ready_user_name}\n"

        ready_keyboard = InlineKeyboardMarkup()
        ready_button = InlineKeyboardButton("Готов!", callback_data="ready")
        ready_keyboard.add(ready_button)

        bot.edit_message_text(text=text, chat_id=c_id, message_id=m_id, reply_markup=ready_keyboard)


@bot.callback_query_handler(func=lambda call: call.data.split()[1].isdigit())
def process_user_votes(call):
    c_id = call.message.chat.id
    m_id = call.message.message_id
    data = call.data.split()

    try:

        voted_user_id = call.from_user.id
        chosen_user_id = int(data[1])

        group_chat_id = get_user_current_group_chat_id(voted_user_id)

        update_user_data(voted_user_id, group_chat_id, "choice", chosen_user_id)

        group_link_keyboard = get_group_link_keyboard(voted_user_id)

        chosen_user_name = str(bot.get_chat_member(group_chat_id, chosen_user_id).user.username)

        bot.edit_message_text(chat_id=c_id, message_id=m_id, text=f"Ваш выбор: {chosen_user_name}",
                              reply_markup=group_link_keyboard)

        voted_user_role = data[0]

        if voted_user_role == "commissar":
            checked_user_role = get_user_data(chosen_user_id, group_chat_id, "role")

            if checked_user_role == "Мафия":
                bot.send_message(c_id, f"Игрок {chosen_user_name} - мафия!")

            else:
                bot.send_message(c_id, f"Игрок {chosen_user_name} - не мафия!")

    except IndexError:
        bot.edit_message_text(chat_id=c_id, message_id=m_id, text=f"Кажется, кнопка устарела")


@bot.message_handler(commands=["delete"], chat_types=["supergroup"])
def deleting_group_state(message):
    user_id = message.from_user.id

    admin_ids = [admin.user.id for admin in bot.get_chat_administrators(message.chat.id)]

    if user_id in admin_ids:
        change_group_state(message.chat.id, 0)

    else:
        bot.send_message(message.chat.id, "В доступе отказано!")


@bot.message_handler(content_types=CONTENT_TYPES, chat_types=["supergroup"])
def deleting_messages(message):
    user_id = message.from_user.id
    group_chat_id = message.chat.id

    is_group_in_game = is_group_playing(group_chat_id)

    if is_group_in_game:
        alive_players = get_alive_users(group_chat_id)

        if user_id not in alive_players:
            bot.delete_message(group_chat_id, message.message_id)


if __name__ == "__main__":
    bot.set_my_commands(COMMANDS)  # Добавляем команды в меню

    bot.infinity_polling()
