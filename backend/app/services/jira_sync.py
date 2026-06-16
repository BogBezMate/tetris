"""JiraSyncService — единая точка приёма изменений из Jira и записи обратно.

handle_webhook и load_from_file ведут в один и тот же loader.load_payload — поэтому
переход с файла (этап 5) на живой вебхук (этап 12) не меняет логику загрузки.
"""
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import JiraSyncLog
from app.services import loader
from app.services.jira_client import JiraClient


class JiraSyncService:
    def __init__(self, db: Session):
        self.db = db

    def load_from_file(self, path: str | Path | None = None) -> dict:
        path = Path(path) if path else get_settings().jira_sample_path
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return loader.load_payload(self.db, payload)

    def handle_webhook(self, payload: dict) -> dict:
        return loader.load_payload(self.db, payload)

    def push_to_jira(self, jira_key: str, fields: dict) -> None:
        try:
            JiraClient().update_issue(jira_key, fields)
            self.db.add(JiraSyncLog(
                sync_direction="out", sync_payload={"key": jira_key, "fields": fields},
                sync_status="ok",
            ))
        except Exception as exc:  # noqa: BLE001
            self.db.add(JiraSyncLog(
                sync_direction="out", sync_payload={"key": jira_key, "fields": fields},
                sync_status="error", sync_error_message=str(exc),
            ))
        self.db.commit()
