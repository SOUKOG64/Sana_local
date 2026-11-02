# Арт-Фехтование

Клиент-серверное приложение: **FastAPI + SQLAlchemy ORM** (backend) и **Kivy** (клиент).
Основная сущность — **Фехтовальщик** (Fighter).

## Запуск

```bash
# 1. Сервер
cd backend
pip install -r requirements.txt
uvicorn main:app --reload          # Swagger: http://127.0.0.1:8000/docs

# 2. Клиент (в другом терминале)
cd client
pip install -r requirements.txt
python main.py
```
При первом запуске БД `art_fencing.db` создаётся сама и заполняется демо-фехтовальщиками.

## Сборка APK через GitHub Actions

Workflow `.github/workflows/build-apk.yml` собирает debug APK для Android при push,
pull request или вручную через вкладку **Actions → Build Android APK → Run workflow**.
Готовый APK можно скачать из артефактов завершённого запуска.

### Загрузка проекта на GitHub без команд

1. Создайте на GitHub пустой репозиторий. Не добавляйте при создании README, лицензию
   или `.gitignore`.
2. Распакуйте архив проекта и загрузите **содержимое папки проекта** через
   **Add file → Upload files**. Файл `.github/workflows/build-apk.yml` должен оказаться
   именно по этому пути в корне репозитория, а не внутри дополнительной вложенной папки.
3. Нажмите **Commit changes**. После загрузки GitHub автоматически запустит сборку;
   её статус и APK доступны во вкладке **Actions**.

APK-версия работает **автономно**: все данные (аккаунты и фехтовальщики) хранятся в SQLite-файле
на самом телефоне, сервер и интернет не нужны. Папка `backend/` нужна только для запуска
клиент-серверной версии на ПК и в APK не попадает.

Для локальной сборки установите Buildozer и Android SDK/NDK, затем выполните:

```bash
cd client
buildozer android debug
```

Сборка создаёт Android APK, а не Windows executable из `dist/`.

## Соответствие критериям

### FastAPI
| Критерий | Где |
|---|---|
| GET — список | `GET /api/fighters` (+ `search`, `weapon`) |
| GET /{id} | `GET /api/fighters/{id}` |
| POST — создание | `POST /api/fighters` |
| PATCH — изменение | `PATCH /api/fighters/{id}` |
| DELETE — удаление | `DELETE /api/fighters/{id}` |
| JSON, Pydantic-схемы | `backend/schemas.py` |
| Коды 400 / 401 / 404 / 500 | `backend/main.py` (обработчики) + `security.py` |
| Swagger/OpenAPI | `/docs`, `/redoc` |
| Авторизация | `POST /api/auth/register`, `POST /api/auth/login` (JWT) |
| Kivy работает через API | `client/api.py` |

### SQLAlchemy ORM (`backend/models.py`, `backend/crud.py`)
DeclarativeBase, Mapped, mapped_column, Session, select, ForeignKey, relationship,
CRUD через ORM, commit(), rollback(), без прямого SQL в логике приложения.
Таблицы: users, clubs, fighters, tournaments, nominations, registrations, performances, scores.

### Kivy-экраны (`client/artfencing.kv`, `client/main.py`)
Авторизация, регистрация, главный экран, навигация, список, просмотр, создание,
редактирование, удаление с подтверждением, поиск + фильтр по оружию, кнопка выхода,
единый дизайн, сообщения об ошибках и успехе.
