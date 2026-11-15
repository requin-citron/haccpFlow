"""Vérifie les ressources nécessaires à l'installation de la PWA."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from common import Report, WEB_BASE_URL, fetch_page


ICONS = (
    ("/icons/icon-192.png", 192),
    ("/icons/icon-512.png", 512),
    ("/icons/icon-maskable-512.png", 512),
    ("/icons/apple-touch-icon.png", 180),
)


def fetch_bytes(path: str) -> tuple[int, bytes, dict[str, str]]:
    request = urllib.request.Request(f"{WEB_BASE_URL}{path}")
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, response.read(), dict(response.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), dict(exc.headers)
    except urllib.error.URLError:
        return 0, b"", {}


def png_size(payload: bytes) -> tuple[int, int] | None:
    if len(payload) < 24 or not payload.startswith(b"\x89PNG\r\n\x1a\n"):
        return None
    width = int.from_bytes(payload[16:20], "big")
    height = int.from_bytes(payload[20:24], "big")
    return width, height


def main() -> None:
    report = Report("Frontend — installation PWA")

    status, html = fetch_page("/login")
    report.status("/login", status)
    report.check("manifest lié dans le document", "/manifest.webmanifest" in html)
    report.check("theme-color déclaré", 'name="theme-color"' in html)

    status, body = fetch_page("/manifest.webmanifest")
    report.status("manifest.webmanifest", status)
    try:
        manifest = json.loads(body)
    except json.JSONDecodeError:
        manifest = {}
    report.check("manifest JSON valide", isinstance(manifest, dict) and bool(manifest))
    report.equals("nom PWA", manifest.get("name"), "haccpFlow — Gestion HACCP")
    report.equals("affichage standalone", manifest.get("display"), "standalone")
    report.equals("start_url", manifest.get("start_url"), "/")
    report.equals("scope", manifest.get("scope"), "/")
    report.check(
        "icônes 192/512 et maskable",
        any(icon.get("sizes") == "192x192" for icon in manifest.get("icons", []))
        and any(icon.get("sizes") == "512x512" for icon in manifest.get("icons", []))
        and any(icon.get("purpose") == "maskable" for icon in manifest.get("icons", [])),
    )

    status, service_worker = fetch_page("/sw.js")
    report.status("service worker", status)
    report.check("service worker gère les requêtes", 'self.addEventListener("fetch"' in service_worker)
    report.check("fallback hors ligne précaché", "/offline.html" in service_worker)
    report.check("API jamais mise en cache", 'url.pathname.startsWith("/api/")' in service_worker)
    report.check("navigation non mise en cache", 'request.mode === "navigate"' in service_worker)

    status, offline = fetch_page("/offline.html")
    report.status("page hors ligne", status)
    report.check("message français", "Vous êtes hors ligne" in offline)
    report.check("message anglais", "You are offline" in offline)

    for path, expected_size in ICONS:
        status, payload, headers = fetch_bytes(path)
        report.status(path, status)
        report.equals(f"{path} dimensions", png_size(payload), (expected_size, expected_size))
        report.check(
            f"{path} type MIME",
            headers.get("Content-Type", "").startswith("image/png"),
            headers.get("Content-Type", ""),
        )

    report.finish()


if __name__ == "__main__":
    main()
