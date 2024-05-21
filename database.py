import sqlite3
from config import ROLES


def open_db():
    con = sqlite3.connect('sqlite.db', check_same_thread=False)
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
def change_db(sql: str):
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
        connection, cursor = open_db()
        try:
            sql = f'INSERT INTO roles (name) VALUES ("{role}");'
            cursor.execute(sql)
        except sqlite3.IntegrityError:
            pass
        finally:
            connection.commit()
            cursor.close()
            connection.close()


# добавляет нового пользователя в таблицу users если его там ещё нет
def add_user(chat_id: int):
    connection, cursor = open_db()
    sql = f'INSERT INTO users (chat_id) VALUES ({chat_id});'
    try:
        cursor.execute(sql)
    except sqlite3.IntegrityError:
        pass
    finally:
        connection.commit()
        cursor.close()
        connection.close()


# возвращает False, если юзера нет в users => он должен написать старт боту в личке
# True - если юзер записан
def check_user_exists(chat_id: int) -> bool:
    sql = f'SELECT id FROM users WHERE chat_id = {chat_id};'
    result = get_from_db(sql)
    return bool(result)


# добавляет новую группу в таблицу groups если её там ещё нет
def add_group(group_chat_id: int):
    connection, cursor = open_db()
    sql = f'INSERT INTO groups (group_chat_id) VALUES ({group_chat_id});'
    try:
        cursor.execute(sql)
    except sqlite3.IntegrityError:
        pass
    finally:
        connection.commit()
        cursor.close()
        connection.close()


# возвращает True, если группа сейчас играет, False - если нет
def is_group_playing(group_chat_id: int) -> bool:
    sql = f'SELECT is_playing FROM groups WHERE group_chat_id = {group_chat_id};'
    result = get_from_db(sql)
    return bool(result[0][0])


# возвращает текущее кол-во сессий группы
def get_group_current_session(group_chat_id: int) -> int:
    sql = f'SELECT session FROM groups WHERE group_chat_id = {group_chat_id};'
    result = get_from_db(sql)
    return result[0][0]


# переводит статус группы is_playing в нужный, state = 0 - не играет, 1 - играет
def change_group_state(group_chat_id: int, state: int):
    sql = f'UPDATE groups SET is_playing = {state} WHERE group_chat_id = {group_chat_id};'
    change_db(sql)


# увеличивает сессию на 1
def increase_session(group_chat_id: int):
    current_session = get_group_current_session(group_chat_id)
    sql = f'UPDATE groups SET session = {current_session + 1} WHERE group_chat_id = {group_chat_id};'
    change_db(sql)


# должна использоваться только в этом файле
def get_one_by_other(param_1: str, param_2: str, value: int, table_name: str) -> int:
    sql = f'SELECT {param_1} FROM {table_name} WHERE {param_2} = {value};'
    result = get_from_db(sql)
    return int(result[0][0])


# возвращает True, если юзер сейчас играет, False - если нет
def is_user_playing(chat_id: int) -> bool:
    user_id = get_one_by_other('id', 'chat_id', chat_id, table_name='users')
    sql = f'SELECT group_id, session FROM games WHERE user_id = {user_id} ORDER BY id DESC LIMIT 1;'
    result = get_from_db(sql)
    if not result:
        return False
    group_id, session = result[0]
    group_chat_id = get_one_by_other('group_chat_id', 'id', group_id, table_name='groups')
    if is_group_playing(group_chat_id) and get_group_current_session(group_chat_id) == session:
        return True
    return False


# добавляет пользователя в таблицу games
def add_user_to_games(group_chat_id: int, user_chat_id: int):
    group_id = get_one_by_other('id', 'group_chat_id', group_chat_id, table_name='groups')
    user_id = get_one_by_other('id', 'chat_id', user_chat_id, table_name='users')
    session = get_group_current_session(group_chat_id)
    sql = f'INSERT INTO games (group_id, session, user_id) VALUES ({group_id}, {session}, {user_id});'
    change_db(sql)


# подсчитывает кол-во присоединившихся к игре пользователей
def count_session_users(group_chat_id: int) -> int:
    current_session = get_group_current_session(group_chat_id)
    group_id = get_one_by_other('id', 'group_chat_id', group_chat_id, table_name='groups')
    sql = f'SELECT COUNT(*) FROM games WHERE group_id = {group_id} and session = {current_session};'
    result = get_from_db(sql)
    return result[0][0]


# возвращает group_chat_id группы, в которой пользователь сейчас играет, если такая существует, если нет, то False
def get_user_current_group_chat_id(chat_id: int) -> int | bool:
    user_id = get_one_by_other('id', 'chat_id', chat_id, table_name='users')
    sql = f'SELECT group_id, session FROM games WHERE user_id = {user_id} ORDER BY id DESC LIMIT 1;'
    result = get_from_db(sql)
    if not result:
        return False
    print(result)
    group_id, session = result[0]
    group_chat_id = get_one_by_other('group_chat_id', 'id', group_id, table_name='groups')
    if is_group_playing(group_chat_id) and get_group_current_session(group_chat_id) == session:
        return group_chat_id
    return False


create_tables()
update_roles()
