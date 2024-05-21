import sqlite3
from config import ROLES


def open_db():
    con = sqlite3.connect('db.sqlite', check_same_thread=False)
    cur = con.cursor()
    return con, cur


def create_tables():
    connection, cursor = open_db()

    # список всех пользователей бота
    cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER NOT NULL UNIQUE
    );
    ''')

    # список всех ролей
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS roles(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    );
    ''')

    # список всех групп
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS groups(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_chat_id INTEGER NOT NULL UNIQUE,
        is_playing INTEGER NOT NULL DEFAULT 0,
        session INTEGER NOT NULL DEFAULT 0
    );
    ''')
    # is_playing - 0 если группа не играет, 1 - если играет
    # session - отсчёт сессий начинается с 1, 0 только у групп, которые ни разу не играли

    # описание всех игр (группы, игроки, роли и т.д.)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS games(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id INTEGER NOT NULL,
        session INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        role INTEGER,
        choice INTEGER,
        killed INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (group_id) REFERENCES groups (id),
        FOREIGN KEY (session) REFERENCES groups (session),
        FOREIGN KEY (user_id) REFERENCES users (chat_id),
        FOREIGN KEY (role) REFERENCES roles (id),
        FOREIGN KEY (choice) REFERENCES users (id)
    );
    ''')
    # killed - 0 если игрок жив, 1 - если убит
    # FOREIGN KEY значит что через этот столбец идёт связь с другой таблицей,
    # например, столбец group_id будет взят из таблицы groups из столбца id,
    # то есть там не id группы в тг, а id группы в таблице

    cursor.close()
    connection.commit()
    connection.close()


# эта функция должна использоваться только в этом файле для запросов UPDATE, INSERT и DELETE
def change_db(sql):
    connection, cursor = open_db()
    cursor.execute(sql)
    cursor.close()
    connection.commit()
    connection.close()


# эта функция должна использоваться только в этом файле для запросов SELECT
def get_from_db(sql: str) -> list[tuple]:
    connection, cursor = open_db()
    cursor.execute(sql)
    result = cursor.fetchall()
    cursor.close()
    connection.close()
    return result


# функция вызывается каждый раз при запуске проекта и добавляет в БД новые роли, если они появились
def update_roles():
    for role in ROLES:
        try:
            sql = f'INSERT INTO roles (name) VALUES ("{role}");'
            change_db(sql)
        except sqlite3.IntegrityError:
            pass


# добавляет нового пользователя в таблицу users если его там ещё нет
def add_user(chat_id: int):
    sql = f'INSERT INTO users (chat_id) VALUES ({chat_id});'
    try:
        change_db(sql)
    except sqlite3.IntegrityError:
        pass


# добавляет новую группу в таблицу groups если её там ещё нет
def add_group(group_chat_id: int):
    sql = f'INSERT INTO groups (group_chat_id) VALUES ({group_chat_id});'
    try:
        change_db(sql)
    except sqlite3.IntegrityError:
        pass


create_tables()
update_roles()
