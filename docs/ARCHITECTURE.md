# Тетрис — описание проекта, запуск и сопровождение

> **Для того, кто открыл этот проект впервые (человек или AI-агент).**
> Прочитав этот файл, можно понять: что это за сервис, из чего состоит, как его запустить,
> как устроены данные и как вносить типовые изменения. Если вы агент — начните с этого файла,
> затем смотрите упомянутые исходники.

## 1. Что это
Веб-сервис **квартального планирования IT-портфеля** по подходу SAFe. Заменяет связку
Google Sheets + n8n + скрипты («Tetris 1.0»). Логика:
1. Задачи приходят из **Jira** (сейчас — из файла-выгрузки; на этапе 12 — живой вебхук).
2. На вкладке **«Автовыгрузка»** они группируются по «колодцам» (MetaSprint / AlphaSprint /
   OpenSprint / To be allocated).
3. Внутри **метаспринта** создаются **планы** (итерации). В план перетаскивают задачи,
   проставляют остаточные оценки, велосити платформ, видят нагрузку/перегруз, считают итоги.
4. Метрики (приведённый эффект, EBITDA к SP, число спринтов, признаки «недооценено» и т.п.)
   **вычисляются на лету** в SQL-представлении, в БД не дублируются.

## 2. Стек
- **Backend:** Python + FastAPI + SQLAlchemy 2.0 + PostgreSQL + Pydantic v2. JWT-аутентификация
  (bcrypt). Роли: `editor` (всё) / `reader` (только просмотр).
- **Frontend:** React 18 + TypeScript + Vite. Drag-and-drop — нативный HTML5. Личные настройки
  пользователя (ширины/порядок столбцов, палитра, фильтры, итоги, выбранный план) — в `localStorage`
  браузера, не в БД.
- **Данные для разработки:** обезличенный `jira_issues_test.json` в корне (≈659 задач).
  Реальные ПД из него вырезаны.

## 3. Как запустить (с нуля)
Нужны: **Python 3.11+**, **Node 18+**, **PostgreSQL**.

### Backend
```bash
cd backend
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt   # Windows; на *nix — .venv/bin/python
cp .env.example .env            # при необходимости поправить DATABASE_URL и JIRA_SAMPLE_FILE
# поднять PostgreSQL и создать БД tetris:  CREATE DATABASE tetris;
./.venv/Scripts/python.exe -m scripts.bootstrap   # таблицы + представление + справочники + пользователи + загрузка задач
./.venv/Scripts/uvicorn.exe app.main:app --reload # API на http://localhost:8000  (Swagger: /docs)
```
`.env` (ключевое): `DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/tetris`,
`JIRA_SAMPLE_FILE=../jira_issues_test.json`, `SECRET_KEY=...`.

### Frontend
```bash
cd frontend
npm install
npm run dev        # http://localhost:5173  (API берёт из VITE_API_URL или http://localhost:8000)
```
Заходите по **одному** адресу (рекомендуется `localhost`, не `127.0.0.1` — у них раздельный localStorage).

### Тестовые пользователи (создаёт bootstrap)
`editor@askona.ru / editor123` (редактор), `reader@askona.ru / reader123` (читатель).

### Обновить данные задач (без вебхука)
Кнопка в шапке **«⟳ из Jira»** или `POST /api/tasks/reload-from-file` — перечитывает
`JIRA_SAMPLE_FILE` (upsert по `jira_internal_id`, дублей не будет).

## 4. Структура репозитория
```
backend/app/
  main.py            точка входа FastAPI, регистрация роутеров
  config.py          настройки из .env
  database.py        engine/SessionLocal, get_db
  models.py          ORM-таблицы (факты)
  read_models.py     TaskRanked — read-only маппинг на представление v_tasks_ranked
  schemas.py         Pydantic-схемы API
  security.py        bcrypt + JWT;  deps.py — авторизация и require_editor
  jira_fields.py     ЕДИНЫЙ источник правды по полям Jira (customfield-id, платформы, алиасы, игнор, типы целей, колодцы)
  jira_mapper.py     JiraFieldMapper.to_task: JSON задачи Jira -> ParsedTask (поля, спринты, платформы)
  seeds.py           заполнение справочников (платформы/типы целей/колодцы) — идемпотентно
  sql/v_tasks_ranked.sql   метрики и признаки качества оценки (вычисляются на лету)
  services/
    loader.py        load_payload -> upsert_parsed_task (общая точка для файла и вебхука)
    jira_sync.py     load_from_file / handle_webhook -> loader  (вебхук = этап 12)
    plan_service.py  планы: создание/форк, items, presentation, остатки, velocity метаспринта
    task_service.py  список ранжированных задач, редактирование задачи
    auto_placement.py  zone_for(labels, has_active_sprint) — раскладка по колодцам
    jira_client.py   запись в Jira (этап 12, пока заглушка)
  routers/           auth, tasks, planning, platforms
backend/scripts/
  bootstrap.py       инициализация боевой БД
  migrate_docNN.py   идемпотентные миграции по доводкам (ALTER/seed/пересоздание view)
frontend/src/
  App.tsx            метаспринты/планы/вкладки, навигация, запоминание выбора
  api.ts             REST-клиент;  types.ts — типы
  components/
    Grid.tsx         таблица плана (drag, кисть, заметки, перегруз, итоги, фильтры, override)
    Autovygruzka.tsx таблица-пул задач по колодцам
    TaskModal.tsx    карточка задачи (вкладки, оценки, остатки в плане)
    FilterMenu.tsx   фильтр по качеству оценки (4 категории, показ строк/значок ⚠)
    ColumnFilter.tsx воронка-фильтр у заголовка столбца
    MetaVelocityModal.tsx  velocity метаспринта (ёмкость + SP/спринт по платформам)
    ColumnsMenu / NoteModal / Login
    columns.ts       описание столбцов + ВСЕ личные настройки в localStorage (ширины, порядок,
                     палитра, фильтры столбцов, промежуточные итоги, видимость)
docs/ARCHITECTURE.md этот файл
```

## 5. Модель данных
Хранятся **факты**; метрики — в представлении `v_tasks_ranked` (не в полях).
- **tasks** — задачи из Jira. `jira_internal_id` — ключ upsert. `has_active_sprint` — есть спринт `state=ACTIVE`.
- **task_platforms** — оценки по платформам: `is_required` (платформа выбрана в задаче), `estimate_story_points`.
- **task_labels** — метки Jira.
- **platforms** — справочник: имя, customfield-id, `sp_per_sprint` (глобальный делитель по умолчанию).
- **goal_types**, **zones** — справочники (типы целей; 4 колодца).
- **quarters** = метаспринты; **plans** = планы (внутри метаспринта). `plans.presentation` (JSON) — «Excel-слой»: порядок строк, заливки, заметки (общий для всех).
- **plan_items** — задачи плана (зона, позиция).
- **plan_task_estimates** — остаточные оценки задачи В РАМКАХ плана (override поверх Jira; «сброс к Jira» = удалить строку).
- **quarter_velocities** — на (метаспринт, платформа): `capacity_sp` (ёмкость → подсветка перегруза) и `sp_per_sprint` (делитель спринтов для этого метаспринта).
- **users**, **jira_sync_log**.

## 6. Ключевые потоки
- **Загрузка из Jira:** `loader.load_payload → load_issues → JiraFieldMapper.to_task → upsert_parsed_task` (upsert по `jira_internal_id`). Один файл = много задач; имена файлов не важны.
- **Колодцы (`auto_placement.zone_for`):** приоритет — **метка** `MetaSprint*`→MetaSprint, `Alpha*`→AlphaSprint; если метки нет, но есть **активный спринт** → **OpenSprint**; иначе **To be allocated**. (Метка важнее активного спринта.)
- **Признаки качества оценки** (в `v_tasks_ranked`, непересекающиеся): `is_underestimated`, `is_unplatformed`, `has_estimate_no_team`, `has_unselected_estimate` — используются в фильтре и пометке ⚠ на фронте.
- **Метрики:** приведённый годовой эффект, `ebitda_per_story_point` (= Приведённая EBITDA ÷ Story Points), `max_sprints` — всё во `v_tasks_ranked`.
- **Планирование:** добавление из автовыгрузки → план; раскладка по колодцам, ручной порядок (в `presentation.order`), остатки, velocity метаспринта, перегруз, итоги, фильтр по столбцам, форк плана «создать на основе».

## 7. Как вносить типовые изменения
- **Любое поле Jira / платформа** — только в `app/jira_fields.py` (единый источник). Платформы:
  `PLATFORM_FIELDS` (имя→customfield-id), `PLATFORM_ALIASES` (нормализация написания селектора),
  `PLATFORM_IGNORE` (значения, которые не платформы). После добавления платформы — миграция,
  вызывающая `seeds.seed_platforms`, и перезалив задач.
- **Новый столбец в таблице** — `frontend/src/components/columns.ts` (`BASE_COLS`), плюс поле в
  `TaskRankedOut`/`TaskRanked`/`v_tasks_ranked`, если данных ещё нет.
- **Метрика/признак** — формула в `app/sql/v_tasks_ranked.sql`; добавить колонку в `read_models.py`
  и `schemas.py`; пересоздать представление миграцией.
- **Миграции** — новый `backend/scripts/migrate_docNN.py` (идемпотентно: `ADD COLUMN IF NOT EXISTS`,
  `CREATE TABLE IF NOT EXISTS`, пересоздание VIEW из `sql/`-файла, вызовы `seed_*`). Запуск
  `python -m scripts.migrate_docNN`. На чистой БД всё ставит `scripts/bootstrap.py`.
- **Эндпоинт** — в `app/routers/*`, логика — в `app/services/*`; права — `Depends(require_editor)`.
- **Личные настройки фронта** — паттерн `load*/save*` в `columns.ts` (localStorage), не в БД.

## 8. Проверки/тесты
- Backend стартует: `python -c "from app.main import app"`. Smoke без БД: `python -m scripts.smoke_sqlite`.
- Фронт: `npx tsc --noEmit` (типы) + `npm run build`.
- Sanity по API: логин `editor@askona.ru`, затем `GET /api/autovygruzka` (колодцы, платформы),
  `GET /api/plans/{id}/grid`.

## 9. Что дальше (этап 12)
- **Живой вебхук Jira:** точка входа `services/jira_sync.handle_webhook` уже ведёт в общий
  `loader.load_payload` — переход с файла на вебхук логику загрузки не меняет.
- **Запись изменений обратно в Jira** (`jira_client`): сейчас заглушка (кнопка «Запись в Jira (этап 12)»).
- Нужны: токен (PAT) и доступ к Jira; деплой на сервер (Docker, ~2 ГБ RAM, пара ядер).
