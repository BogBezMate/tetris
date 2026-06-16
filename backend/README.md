# Тетрис — бэкенд

Сервис квартального планирования портфеля. Python (FastAPI) + PostgreSQL.
При разработке источник данных — файл `../response_example.json` (вместо живого вебхука Jira).

## Установка (один раз)

```bash
cd backend
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt
cp .env.example .env        # при необходимости поправить DATABASE_URL
```

## Проверки без базы (работают уже сейчас)

```bash
# Парсер на эталоне ITP-3085
./.venv/Scripts/python.exe -m scripts.check_parser

# Весь поток seed -> load -> представление на SQLite в памяти
./.venv/Scripts/python.exe -m scripts.smoke_sqlite
```

## Запуск с PostgreSQL

1. Поднять PostgreSQL локально, создать базу:
   ```sql
   CREATE DATABASE tetris;
   ```
2. Прописать строку подключения в `.env` (`DATABASE_URL`).
3. Инициализировать одной командой (таблицы + представление + справочники + задачи из файла + пользователи):
   ```bash
   ./.venv/Scripts/python.exe -m scripts.bootstrap
   ```
4. Запустить API:
   ```bash
   ./.venv/Scripts/uvicorn.exe app.main:app --reload
   ```
   Документация: http://localhost:8000/docs

Тестовые пользователи (создаёт bootstrap): `editor@askona.ru / editor123`, `reader@askona.ru / reader123`.

## Структура

```
app/
  config.py          настройки из .env
  database.py        подключение к БД, сессии
  models.py          11 таблиц (ORM)
  read_models.py     TaskRanked — на представление v_tasks_ranked
  schemas.py         Pydantic-схемы API
  security.py        хеш пароля (bcrypt), JWT
  deps.py            авторизация, проверка роли
  jira_fields.py     ЕДИНЫЙ источник customfield-id (17 платформ, типы целей)
  jira_mapper.py     JiraFieldMapper: JSON задачи -> ParsedTask
  seeds.py           наполнение справочников
  sql/v_tasks_ranked.sql   метрики (логика n8n) в виде представления
  services/          loader, task/auth/plan/auto_placement, jira_client/jira_sync
  routers/           auth, tasks, planning
scripts/
  check_parser.py    сверка парсера с ITP-3085
  smoke_sqlite.py    офлайн-прогон всего потока на SQLite
  bootstrap.py       инициализация боевой базы (PostgreSQL)
```

## Этапы

Сделано: 1–9 (бэкенд целиком, проверен на файле). Дальше: 10 — фронт; 11 — перенос на сервер Аскон; 12 — живой вебхук Jira и запись обратно (структура заложена в `services/jira_sync.py` и `jira_client.py`).
