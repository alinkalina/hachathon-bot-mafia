import telebot

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import BOT_TOKEN, LINK_TO_BOT, SHORT_RULES, FULL_RULES, COMMANDS

from database import add_user

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

    # add_group() TODO функция добавления группы в БД ещё не готова


@bot.message_handler(commands=["start"], chat_types=["private"])
def handle_private_start(message):
    link_to_group = get_group_link()

    # создаем кнопку для перехода в группу
    return_to_group_btn = InlineKeyboardButton(text="Вернуться в группу", url=link_to_group)
    keyboard = InlineKeyboardMarkup().add(return_to_group_btn)

    text = ("Привет! Я бот, позволяющий играть в мафию. Здесь ты можешь ознакомиться с правилами игры "
            "по команде /rules или можешь вернуться в группу.")

    bot.send_message(message.chat.id, text, reply_markup=keyboard)

    add_user(message.chat.id)


def get_group_link():
    # group_id = get_group_id() TODO функция получения айди группы еще не готова
    group_id = "Временный вариант (заменить на айди группы)"

    link_to_group = bot.export_chat_invite_link(chat_id=group_id)  # Создаем ссылку для группы
    return link_to_group


@bot.message_handler(commands=["rules"], chat_types=["private"])
def send_rules(message):
    bot.send_message(message.chat.id, FULL_RULES)


if __name__ == "__main__":
    bot.set_my_commands(COMMANDS)  # Добавляем команды в меню

    bot.infinity_polling()
