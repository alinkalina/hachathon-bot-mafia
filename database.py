import sqlite3


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


create_tables()
