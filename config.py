import os
from dotenv import load_dotenv
from telebot.types import BotCommand

load_dotenv()

# Бот

BOT_TOKEN = os.getenv("BOT_TOKEN")
LINK_TO_BOT = "https://t.me/hackathon_mafia_bot"
COMMANDS = [BotCommand(command="start", description="Запуск бота"),
            BotCommand(command="rules", description="Подробные правила игры в мафию")]


# Игра

SHORT_RULES = "Какие-то правила"  # TODO дописать короткие правила
FULL_RULES = "Какие-то правила"  # TODO дописать подробные правила

MIN_PLAYERS = 6

ROLES = ['Мирный житель', 'Мафия', 'Комиссар']  # сюда будем записывать новые роли, и они автоматически добавятся в БД
