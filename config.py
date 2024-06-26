import os
from dotenv import load_dotenv
from telebot.types import BotCommand
from telebot.handler_backends import StatesGroup, State

load_dotenv()

# Бот

BOT_TOKEN = os.getenv("BOT_TOKEN")

LINK_TO_BOT = "https://t.me/hackathon_mafia_bot"

COMMANDS = [BotCommand(command="start", description="Запуск бота"),
            BotCommand(command="rules", description="Подробные правила игры в мафию"),
            BotCommand(command="start_game", description="Начало игры"),
            BotCommand(command="stats", description="Статистика игроков"),
            BotCommand(command="rating", description="Рейтинг игроков")]

BOT_DESCRIPTION = "Бот, который позволяет играть в Мафию, где ведущий - бот."

CONTENT_TYPES = ["text", "audio", "document", "photo", "sticker", "video", "video_note", "voice"]


class MyStates(StatesGroup):
    message_to_delete = "message to delete"
    mafia_chat = 'chat for mafia'
    msg_with_buttons = State()


# Игра

SHORT_RULES = ("После того, как игра началась, бот напишет вашу роль. Ни в коем случае <b>не сообщайте</b> её никому, "
               "ведь весь смысл игры сразу же теряется. Запомните в игре «Мафия» нельзя никому доверять.")

FULL_RULES = ("<b>Правила игры:</b>\n\n"
              "Игра проходит в две фазы: ночь и день. В течение ночи мафия выбирает жертву, "
              "а утром мирные жители пытаются определить, кто из игроков является мафией.\n\n"
              "<b>👨🏼‍🌾 Мирный житель</b> - это самая многочисленная роль в игре. \n"
              "Их задача — вычислить игроков команды Мафии и устранить их всех на дневном голосовании. "
              "Ночью мирные жители <b>не ходят</b>.\n"
              "<b>Мирные жители побеждают, когда устранены все игроки команды Мафии</b>.\n\n\n"
              "<b>🤵🏻 Мафия</b> - это команда игроков, которая состоит из преступников и "
              "пытается уничтожить мирных жителей и комиссара.\n"
              "Мафия знает друг друга и действует сообща, определяя жертву ночью с помощью обсуждения в боте.\n"
              "<b>Мафия побеждает, когда количество мирных жителей меньше или равно количеству Мафии.</b>\n\n\n"
              "<b>🕵🏻 Комиссар</b> – играет за команду мирных жителей.\n"
              "Его задача - проверять игроков на принадлежность к мафии.\n\n\n"
              "<b>👨🏻‍⚕️ Доктор</b> – играет за команду мирных жителей.\n"
              "Это игрок, который каждую ночь может лечить какого-то одного участника. Им может быть даже мафия. "
              "Доктор может лечить себя только 1 раз. Других участников доктор не может лечить 2 раза подряд.")

MIN_NUM_PLAYERS = 6

# сюда будем записывать новые роли, и они автоматически добавятся в БД
ROLES = ['Мирный житель', 'Мафия', 'Комиссар', 'Доктор']

# таймеры
START_GAME_DELAY = 30

MAFIA_DELAY = 60

COMMISSAR_DELAY = 20

DOCTOR_DELAY = 20

DISCUSSION_DELAY = 180

VOTING_DELAY = 30
