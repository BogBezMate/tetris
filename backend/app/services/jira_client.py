"""JiraClient — обёртка на requests для чтения/записи в живую Jira.

Используется только на этапе 12 (боевое окружение). При разработке на файле не нужен:
методы вызываются лишь из обратной записи и ручной синхронизации.
"""
from __future__ import annotations

import requests

from app.config import get_settings


class JiraClient:
    def __init__(self) -> None:
        s = get_settings()
        self.base_url = s.jira_base_url.rstrip("/")
        self.token = s.jira_token
        self.timeout = 30

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def get_issue(self, key: str) -> dict:
        url = f"{self.base_url}/rest/api/2/issue/{key}"
        resp = requests.get(url, headers=self._headers(), timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def update_issue(self, key: str, fields: dict) -> None:
        url = f"{self.base_url}/rest/api/2/issue/{key}"
        resp = requests.put(
            url, json={"fields": fields}, headers=self._headers(), timeout=self.timeout
        )
        resp.raise_for_status()
