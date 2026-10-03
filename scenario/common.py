"""Helpers partagés par les scripts de scénario.

Bibliothèque standard uniquement : ces scripts tournent sans rien installer,
à côté d'une instance de développement.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
API_BASE_URL = "http://127.0.0.1:8000"
WEB_BASE_URL = "http://127.0.0.1:3000"
API_V1 = "/api/v1"

_ENV_KEYS = ("ADMIN_EMAIL", "ADMIN_PASSWORD")


def read_env() -> dict[str, str]:
    """Lit le .env de la racine du dépôt, sans dépendance externe."""

    values: dict[str, str] = {}
    env_file = REPO_ROOT / ".env"
    if not env_file.exists():
        return values
    for raw_line in env_file.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def require_env() -> dict[str, str]:
    env = read_env()
    missing = [key for key in _ENV_KEYS if not env.get(key)]
    if missing:
        sys.exit(f"Variables absentes du .env : {', '.join(missing)}")
    return env


def _request(
    method: str,
    url: str,
    *,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, str]:
    request = urllib.request.Request(url, data=data, method=method)
    for key, value in (headers or {}).items():
        request.add_header(key, value)
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()
    except urllib.error.URLError:
        # Service injoignable : on renvoie 0 pour que l'appelant le rapporte
        # au lieu de planter sur une trace.
        return 0, ""


def call(
    method: str,
    path: str,
    *,
    token: str | None = None,
    form: dict[str, str] | None = None,
    body: Any = None,
) -> tuple[int, Any]:
    """Appelle l'API, renvoie (statut, corps JSON décodé ou None)."""

    data = None
    headers: dict[str, str] = {}
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    status, payload = _request(method, f"{API_BASE_URL}{path}", data=data, headers=headers)
    return status, (json.loads(payload) if payload else None)


def fetch_page(path: str, *, cookie: str | None = None) -> tuple[int, str]:
    """Récupère une page du frontend, renvoie (statut, HTML)."""

    headers = {"Cookie": cookie} if cookie else None
    return _request("GET", f"{WEB_BASE_URL}{path}", headers=headers)


def login(email: str, password: str) -> tuple[str, str]:
    """Renvoie le jeton d'accès et l'en-tête Cookie de session du frontend."""

    status, payload = call(
        "POST", f"{API_V1}/auth/login", form={"username": email, "password": password}
    )
    if status != 200 or not isinstance(payload, dict):
        sys.exit(f"Connexion impossible (statut {status}). Le backend tourne-t-il ?")
    cookie = (
        f"haccp_access_token={payload['access_token']}; "
        f"haccp_refresh_token={payload['refresh_token']}"
    )
    return str(payload["access_token"]), cookie


def today() -> date:
    return datetime.now(UTC).date()


def iso_days_ago(days: int) -> str:
    return (today() - timedelta(days=days)).isoformat()


def iso_days_ahead(days: int) -> str:
    return (today() + timedelta(days=days)).isoformat()


class Report:
    """Rapport de vérification : affiche, compte les échecs, sort en erreur."""

    def __init__(self, title: str) -> None:
        self.failures = 0
        print(f"\n=== {title}")

    def info(self, message: str) -> None:
        print(f"  · {message}")

    def check(self, label: str, ok: bool, detail: str = "") -> None:
        suffix = f" — {detail}" if detail and not ok else ""
        print(f"  [{'OK' if ok else 'ÉCHEC'}] {label}{suffix}")
        if not ok:
            self.failures += 1

    def status(self, label: str, actual: int, expected: int = 200) -> None:
        self.check(label, actual == expected, f"reçu {actual}, attendu {expected}")

    def equals(self, label: str, actual: Any, expected: Any) -> None:
        self.check(label, actual == expected, f"reçu {actual!r}, attendu {expected!r}")

    def finish(self) -> None:
        if self.failures:
            sys.exit(f"\n{self.failures} vérification(s) en échec")
        print("\n  tout est vert")
