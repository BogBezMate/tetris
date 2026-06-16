"""Единственный источник правды про поля Jira (проект ITP).

Все customfield_id выверены по fields.json и response_example.json (ITP-3085).
Менять маппинг — только здесь.
"""

# Скалярные поля задачи.
CF_GOAL_TYPE = "customfield_11508"          # Тип цели (option .value)
CF_COMPANY_EFFECT = "customfield_12501"     # Эффект для компании, руб. (number, полный)
CF_ADJUSTED_EBITDA = "customfield_13601"    # Приведённая EBITDA (number, может быть null)
CF_ETA_MONTHS = "customfield_11300"         # ETA, мес. (array option -> [0].value)
CF_STORY_POINTS = "customfield_10106"       # Story Points (number)
CF_CONTRACTOR_COST = "customfield_12611"    # Оценка подрядчиков, руб. (number)
CF_COEFFICIENT = "customfield_12502"        # Коэффициент (option .value) — только хранение
CF_CEO_PRIORITY = "customfield_12400"       # Приоритет CEO (number)
CF_BUSINESS_UNIT = "customfield_11400"      # Business unit (option .value)
CF_CHANGE_SCOPE = "customfield_11001"       # Охват изменений (array string -> join)
CF_DOD = "customfield_11201"                # Definition of Done (text)
CF_SPRINT = "customfield_10100"             # Sprint (array «грязных» строк greenhopper)
CF_PLATFORM_SELECTOR = "customfield_12613"  # Platform (array option .value) — какие нужны
CF_END_DATE = "customfield_10816"           # End date (date)
CF_BASELINE_END_DATE = "customfield_10818"  # Baseline end date (date)

# 17 платформ: имя -> id поля «Оценка …» в Jira (number).
PLATFORM_FIELDS: dict[str, str] = {
    "1С ЗУП": "customfield_12601",
    "1С ERP": "customfield_12604",
    "1С POS": "customfield_12606",
    "1С WMS": "customfield_12610",
    "1С А Контур": "customfield_12700",
    "Askona.ru": "customfield_12602",
    "BPMSoft": "customfield_12603",
    "Cognos/DWH": "customfield_12612",
    "Directum": "customfield_12609",
    "Аналитика IT BP": "customfield_12663",
    "Галактика": "customfield_12600",
    "Инфраструктура": "customfield_12664",
    "СНГ": "customfield_12662",
    "WebTutor": "customfield_12702",
    "PIM/MDM": "customfield_12605",
    "MP": "customfield_12608",
    "OMNI": "customfield_12607",
}

# Типы целей: имя как в Jira -> участвует ли в расчёте приведённого эффекта.
# Имена точно как приходят (с «, руб.»), иначе не сматчатся с задачами.
GOAL_TYPES: dict[str, bool] = {
    "Продажи, руб.": True,
    "Операционная эффективность, руб.": True,
    "Снижение рисков, руб.": False,
    "Cash, руб.": False,
    "Кэш, руб.": False,
    "Удовлетворённость клиента, руб.": False,
}

# Четыре колодца планирования (в Jira не приходят — наши внутренние).
ZONES: list[str] = ["MetaSprint", "AlphaSprint", "OpenSprint", "To be allocated"]
