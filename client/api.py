"""Локальное хранилище: все данные лежат в SQLite-файле на устройстве, сервер не нужен.

Интерфейс (ApiClient / ApiError) сохранён, поэтому экраны приложения не менялись.
"""
import hashlib
import hmac
import os
import re
import sqlite3

WEAPONS = ("рапира", "сабля", "шпага", "меч", "кинжал")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PBKDF2_ROUNDS = 100_000

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS fighters (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name        TEXT NOT NULL,
    weapon           TEXT NOT NULL,
    club             TEXT,
    experience_years INTEGER NOT NULL DEFAULT 0,
    rating           INTEGER NOT NULL DEFAULT 0,
    bio              TEXT,
    user_id          INTEGER REFERENCES users(id) ON DELETE SET NULL
);
"""

DEMO = [
    ("Иван Громов", "шпага", "Клуб «Эфес»", 7, 920, "Победитель фестиваля «Стальной ветер»."),
    ("Мария Волкова", "рапира", "Клуб «Эфес»", 5, 870, "Любит театральные дуэты."),
    ("Алексей Соколов", "сабля", "Школа «Дамаск»", 3, 640, None),
    ("Ольга Морозова", "меч", "Школа «Дамаск»", 9, 990, "Постановщик групповых боёв."),
]


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def _hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ROUNDS)
    return f"{salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$")
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(),
                                     bytes.fromhex(salt_hex), PBKDF2_ROUNDS)
    except ValueError:
        return False
    return hmac.compare_digest(digest.hex(), digest_hex)


def _int_field(data, key, low, high, label):
    try:
        value = int(data.get(key, 0) or 0)
    except (TypeError, ValueError):
        raise ApiError(400, f"{label}: нужно целое число")
    if not low <= value <= high:
        raise ApiError(400, f"{label}: допустимо от {low} до {high}")
    return value


def _clean_fighter(data: dict) -> dict:
    name = (data.get("full_name") or "").strip()
    if not 2 <= len(name) <= 120:
        raise ApiError(400, "ФИО: от 2 до 120 символов")
    weapon = data.get("weapon")
    if weapon not in WEAPONS:
        raise ApiError(400, "Оружие: выберите из списка")
    club = (data.get("club") or "").strip() or None
    bio = (data.get("bio") or "").strip() or None
    if club and len(club) > 80:
        raise ApiError(400, "Клуб: не более 80 символов")
    if bio and len(bio) > 1000:
        raise ApiError(400, "О себе: не более 1000 символов")
    return {
        "full_name": name,
        "weapon": weapon,
        "club": club,
        "experience_years": _int_field(data, "experience_years", 0, 80, "Опыт"),
        "rating": _int_field(data, "rating", 0, 10000, "Рейтинг"),
        "bio": bio,
    }


class ApiClient:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.user_id = None
        self.email = None
        self.token = None  # «вошёл ли пользователь»; оставлено для совместимости
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        with self._db() as db:
            db.executescript(SCHEMA)
            if db.execute("SELECT 1 FROM fighters LIMIT 1").fetchone() is None:
                db.executemany(
                    "INSERT INTO fighters (full_name, weapon, club, experience_years, rating, bio)"
                    " VALUES (?, ?, ?, ?, ?, ?)", DEMO)

    def _db(self):
        """Соединение: with-блок делает commit/rollback, closing() закрывает файл."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return _Conn(conn)

    # --- авторизация (локальные аккаунты) ---
    def _login_as(self, row):
        self.user_id = row["id"]
        self.email = row["email"]
        self.token = "local"

    def register(self, email, password):
        email = (email or "").strip().lower()
        if not EMAIL_RE.match(email) or len(email) > 120:
            raise ApiError(400, "Некорректный email")
        if not 6 <= len(password or "") <= 64:
            raise ApiError(400, "Пароль: от 6 до 64 символов")
        try:
            with self._db() as db:
                cur = db.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)",
                                 (email, _hash_password(password)))
                row = db.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
        except sqlite3.IntegrityError:
            raise ApiError(400, "Пользователь с таким email уже существует")
        self._login_as(row)

    def login(self, email, password):
        email = (email or "").strip().lower()
        with self._db() as db:
            row = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if row is None or not _verify_password(password or "", row["password_hash"]):
            raise ApiError(401, "Неверный email или пароль")
        self._login_as(row)

    def logout(self):
        self.user_id = self.email = self.token = None

    def _require_login(self):
        if self.user_id is None:
            raise ApiError(401, "Требуется авторизация")

    # --- фехтовальщики ---
    def list_fighters(self, search="", weapon=None):
        self._require_login()
        sql, params = "SELECT * FROM fighters", []
        if weapon:
            sql += " WHERE weapon = ?"
            params.append(weapon)
        sql += " ORDER BY rating DESC, full_name"
        with self._db() as db:
            items = [dict(r) for r in db.execute(sql, params)]
        if search:
            # SQLite не умеет регистронезависимый поиск по кириллице — фильтруем в Python
            s = search.strip().casefold()
            items = [f for f in items
                     if s in f["full_name"].casefold() or s in (f["club"] or "").casefold()]
        return items

    def get_fighter(self, fighter_id):
        self._require_login()
        with self._db() as db:
            row = db.execute("SELECT * FROM fighters WHERE id = ?", (fighter_id,)).fetchone()
        if row is None:
            raise ApiError(404, "Фехтовальщик не найден")
        return dict(row)

    def create_fighter(self, data):
        self._require_login()
        f = _clean_fighter(data)
        with self._db() as db:
            cur = db.execute(
                "INSERT INTO fighters (full_name, weapon, club, experience_years, rating, bio, user_id)"
                " VALUES (:full_name, :weapon, :club, :experience_years, :rating, :bio, :uid)",
                {**f, "uid": self.user_id})
            fighter_id = cur.lastrowid
        return self.get_fighter(fighter_id)

    def update_fighter(self, fighter_id, data):
        current = self.get_fighter(fighter_id)
        f = _clean_fighter({**current, **data})
        with self._db() as db:
            db.execute(
                "UPDATE fighters SET full_name=:full_name, weapon=:weapon, club=:club,"
                " experience_years=:experience_years, rating=:rating, bio=:bio WHERE id=:id",
                {**f, "id": fighter_id})
        return self.get_fighter(fighter_id)

    def delete_fighter(self, fighter_id):
        self.get_fighter(fighter_id)  # 404, если записи нет
        with self._db() as db:
            db.execute("DELETE FROM fighters WHERE id = ?", (fighter_id,))


class _Conn:
    """Обёртка: commit при успехе, rollback при ошибке и обязательное закрытие файла."""

    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self.conn

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
        finally:
            self.conn.close()
        return False
