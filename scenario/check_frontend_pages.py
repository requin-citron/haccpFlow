"""Vérifie que les pages du frontend rendent les données et restent protégées."""

import re
import sys
import uuid

from common import API_V1, Report, call, fetch_page, login, read_env, require_env

#: chemin, texte attendu uniquement quand la page est rendue avec une session
PAGES: list[tuple[str, str]] = [
    ("/equipment", "Matériel"),
    ("/readings", "Relevés de température"),
    ("/cleaning", "Nettoyage"),
    ("/pasteurisation", "Pasteurisation"),
    ("/transport", "Transport"),
    ("/cash-sessions", "Suivi de caisse"),
    ("/export", "Export"),
    ("/templates", "Modèles LaTeX"),
    ("/documents", "Documents générés"),
    ("/history", "Historique"),
    ("/users", "Utilisateurs"),
]

ENGLISH_PAGES: list[tuple[str, str]] = [
    ("/equipment", "Equipment"),
    ("/readings", "Temperature readings"),
    ("/cleaning", "Cleaning"),
    ("/pasteurisation", "Pasteurisation"),
    ("/transport", "Transport"),
    ("/cash-sessions", "Cash tracking"),
    ("/export", "Export"),
    ("/templates", "LaTeX templates"),
    ("/documents", "Generated documents"),
    ("/history", "History"),
    ("/users", "Users"),
]

NAV_MODULES: list[tuple[str, str]] = [
    ("MODULE_EQUIPMENT", "Matériel"),
    ("MODULE_READINGS", "Relevés"),
    ("MODULE_CLEANING", "Nettoyage"),
    ("MODULE_CLEANING", "Plan de nettoyage"),
    ("MODULE_PASTEURISATION", "Pasteurisation"),
    ("MODULE_TRANSPORT", "Transport"),
    ("MODULE_CASH_SESSIONS", "Suivi de caisse"),
    ("MODULE_EXPORT", "Export"),
    ("MODULE_DOCUMENTS", "Modèles LaTeX"),
    ("MODULE_DOCUMENTS", "Documents générés"),
    ("MODULE_HISTORY", "Historique"),
    ("MODULE_USERS", "Utilisateurs"),
]

ENGLISH_NAV_MODULES: list[tuple[str, str]] = [
    ("MODULE_EQUIPMENT", "Equipment"),
    ("MODULE_READINGS", "Readings"),
    ("MODULE_CLEANING", "Cleaning"),
    ("MODULE_CLEANING", "Cleaning plan"),
    ("MODULE_PASTEURISATION", "Pasteurisation"),
    ("MODULE_TRANSPORT", "Transport"),
    ("MODULE_CASH_SESSIONS", "Cash tracking"),
    ("MODULE_EXPORT", "Export"),
    ("MODULE_DOCUMENTS", "LaTeX templates"),
    ("MODULE_DOCUMENTS", "Generated documents"),
    ("MODULE_HISTORY", "History"),
    ("MODULE_USERS", "Users"),
]

EXPORT_DATASETS: list[tuple[str, str]] = [
    ("MODULE_READINGS", "readings"),
    ("MODULE_CLEANING", "cleanings"),
    ("MODULE_PASTEURISATION", "pasteurisations"),
    ("MODULE_TRANSPORT", "transports"),
    ("MODULE_CASH_SESSIONS", "cash-registers"),
    ("MODULE_DOCUMENTS", "documents"),
]

HISTORY_SOURCES: list[tuple[str, str]] = [
    ("MODULE_READINGS", "temperature_reading"),
    ("MODULE_CLEANING", "cleaning_record"),
    ("MODULE_PASTEURISATION", "pasteurisation_phase"),
    ("MODULE_TRANSPORT", "transport"),
]


def raw_module_enabled(env: dict[str, str], key: str) -> bool:
    value = env.get(key, "1")
    if value not in {"0", "1"}:
        sys.exit(f"{key} doit valoir 0 ou 1 dans le .env (valeur reçue : {value!r})")
    return value == "1"


def module_enabled(env: dict[str, str], key: str) -> bool:
    enabled = raw_module_enabled(env, key)
    if key == "MODULE_EQUIPMENT":
        return enabled or any(
            raw_module_enabled(env, dependency)
            for dependency in (
                "MODULE_READINGS",
                "MODULE_TRANSPORT",
                "MODULE_CASH_SESSIONS",
            )
        )
    return enabled


def main() -> None:
    env = require_env()
    module_env = read_env()
    token, cookie = login(env["ADMIN_EMAIL"], env["ADMIN_PASSWORD"])
    report = Report("Frontend — pages et protection")

    status, html = fetch_page("/login")
    report.status("/login en français par défaut", status)
    report.check("langue HTML française par défaut", '<html lang="fr"' in html)
    report.check("connexion française rendue", "Connexion" in html)
    report.check("sélecteur de langue sur la connexion", "FR / EN" in html)

    status, html = fetch_page("/login", cookie="haccp_locale=en")
    report.status("/login en anglais", status)
    report.check("langue HTML anglaise", '<html lang="en"' in html)
    report.check("connexion anglaise rendue", "Sign in" in html)

    status, html = fetch_page("/login", cookie="haccp_locale=de")
    report.status("/login avec cookie invalide", status)
    report.check("repli sur le français", '<html lang="fr"' in html and "Connexion" in html)

    for path, marker in PAGES:
        status, html = fetch_page(path, cookie=cookie)
        report.status(f"{path} avec session", status)
        report.check(f"{path} rend son contenu", marker in html)

    english_cookie = f"{cookie}; haccp_locale=en"
    for path, marker in ENGLISH_PAGES:
        status, html = fetch_page(path, cookie=english_cookie)
        report.status(f"{path} avec session en anglais", status)
        report.check(f"{path} rend son contenu anglais", marker in html)
        report.check(f"{path} déclare lang=en", '<html lang="en"' in html)

    status, html = fetch_page("/cleaning", cookie=english_cookie)
    report.check("sélecteur de langue dans le shell", "FR / EN" in html)
    english_navigation = re.search(
        r'<nav aria-label="Main navigation".*?</nav>',
        html,
        re.DOTALL,
    )
    report.check("navigation principale anglaise présente", english_navigation is not None)
    english_navigation_html = english_navigation.group(0) if english_navigation else ""
    for env_key, label in ENGLISH_NAV_MODULES:
        visible = f">{label}<" in english_navigation_html
        expected = module_enabled(module_env, env_key)
        report.check(
            f"onglet anglais « {label} » {'présent' if expected else 'masqué'}",
            visible == expected,
        )

    invalid_cookie = f"{cookie}; haccp_locale=es"
    status, html = fetch_page("/equipment", cookie=invalid_cookie)
    report.status("/equipment avec cookie langue invalide", status)
    report.check(
        "cookie langue invalide : repli français",
        '<html lang="fr"' in html and "Parc matériel" in html,
    )

    for path, marker in PAGES:
        status, html = fetch_page(path)
        report.status(f"{path} sans session", status)
        report.check(f"{path} renvoie vers la connexion", "Connexion" in html)
        report.check(f"{path} ne fuit aucune donnée", marker not in html)

    status, html = fetch_page("/cleaning", cookie=cookie)
    navigation = re.search(
        r'<nav aria-label="Navigation principale".*?</nav>',
        html,
        re.DOTALL,
    )
    report.check("navigation principale présente", navigation is not None)
    navigation_html = navigation.group(0) if navigation else ""
    for env_key, label in NAV_MODULES:
        visible = f">{label}<" in navigation_html
        expected = module_enabled(module_env, env_key)
        report.check(
            f"onglet « {label} » {'présent' if expected else 'masqué'}",
            visible == expected,
        )

    status, batches = call("GET", f"{API_V1}/pasteurisations", token=token)
    report.status("registre de pasteurisation", status)
    if isinstance(batches, list) and batches:
        batch = batches[0]
        status, html = fetch_page(f"/pasteurisation/{batch['id']}", cookie=cookie)
        report.status("/pasteurisation/{id}", status)
        for label in (
            "Préchauffage",
            "Palier (pasteurisation)",
            "Refroidissement",
            "Durée calculée",
        ):
            report.check(f"« {label} » rendu", label in html)
    else:
        report.info("aucun lot : lance seed_pasteurisation.py pour voir le détail rempli")

    status, html = fetch_page("/equipment", cookie=cookie)
    for env_key, label in (
        ("MODULE_TRANSPORT", "Véhicules"),
        ("MODULE_TRANSPORT", "Nouveau véhicule"),
        ("MODULE_CASH_SESSIONS", "Caisses"),
        ("MODULE_CASH_SESSIONS", "Nouvelle caisse"),
    ):
        visible = label in html
        expected = module_enabled(module_env, env_key)
        report.check(
            f"page Matériel : « {label} » {'rendu' if expected else 'masqué'}",
            visible == expected,
        )

    status, html = fetch_page("/users", cookie=cookie)
    for label in ("Nouvel utilisateur", "Comptes", "Administrateur", "Supprimer"):
        report.check(f"page Utilisateurs : « {label} » rendu", label in html)

    status, transports = call("GET", f"{API_V1}/transports", token=token)
    report.status("registre des transports", status)
    if isinstance(transports, list) and transports:
        status, html = fetch_page(f"/transport/{transports[0]['id']}", cookie=cookie)
        report.status("/transport/{id}", status)
        for label in ("Relevés de température", "Départ", "Arrivée", "Observation"):
            report.check(f"« {label} » rendu", label in html)
    else:
        report.info("aucun transport : lance seed_transport.py pour voir le détail rempli")

    status, html = fetch_page("/export", cookie=cookie)
    report.check("page d'export : bouton de téléchargement", "Télécharger le CSV" in html)
    for env_key, dataset in EXPORT_DATASETS:
        visible = f"/api/exports/{dataset}" in html
        expected = module_enabled(module_env, env_key)
        report.check(
            f"export « {dataset} » {'proposé' if expected else 'masqué'}",
            visible == expected,
        )

    status, html = fetch_page("/history", cookie=cookie)
    report.status("sources d'historique", status)
    source_select = re.search(
        r'<select id="entity".*?</select>',
        html,
        re.DOTALL,
    )
    source_html = source_select.group(0) if source_select else ""
    for env_key, entity in HISTORY_SOURCES:
        visible = f'value="{entity}"' in source_html
        expected = module_enabled(module_env, env_key)
        report.check(
            f"source d'historique « {entity} » {'présente' if expected else 'masquée'}",
            visible == expected,
        )

    status, csv_text = fetch_page("/api/exports/readings", cookie=cookie)
    report.status("téléchargement via le frontend", status)
    report.check("  BOM conservé", csv_text.startswith("\ufeff"))
    report.check("  en-tête français", "Matériel;Type;Date" in csv_text)

    # Suivi de caisse : le détail d'un suivi ouvert doit proposer les frais et
    # la clôture. La caisse et le suivi créés ici sont supprimés ensuite.
    suffix = uuid.uuid4().hex[:6].upper()
    status, cash_register = call(
        "POST",
        f"{API_V1}/cash-registers",
        token=token,
        body={"name": f"Caisse front {suffix}", "coins_1_euro": 2},
    )
    report.status("caisse de test créée", status, 201)
    if isinstance(cash_register, dict):
        status, session = call(
            "POST",
            f"{API_V1}/cash-sessions",
            token=token,
            body={"cash_register_id": cash_register["id"]},
        )
        report.status("suivi de test ouvert", status, 201)
        if isinstance(session, dict):
            status, html = fetch_page(f"/cash-sessions/{session['id']}", cookie=cookie)
            report.status("/cash-sessions/{id}", status)
            for label in (
                cash_register["name"],
                "Fond d'ouverture",
                "Comptage d'ouverture",
                "Ajouter un frais",
                "Clôturer le suivi",
                "Télécharger le CSV",
            ):
                report.check(f"« {label} » rendu", label in html)

            # Le CSV du suivi se télécharge à travers le frontend.
            status, csv_text = fetch_page(
                f"/api/cash-sessions/{session['id']}/export", cookie=cookie
            )
            report.status("extract du suivi via le frontend", status)
            report.check("  bloc d'ouverture", "Comptage d'ouverture" in csv_text)

            # Un frais puis la clôture : l'état figé doit aussi se rendre.
            call(
                "POST",
                f"{API_V1}/cash-sessions/{session['id']}/expenses",
                token=token,
                body={
                    "kind": "professional",
                    "name": "Sacs poubelle",
                    "quantity": 2,
                    "unit_price_cents": 250,
                    "vat_rate": "20.00",
                },
            )
            call(
                "POST",
                f"{API_V1}/cash-sessions/{session['id']}/close",
                token=token,
                body={
                    "closing_counts": dict.fromkeys(
                        (
                            "coins_1_cent",
                            "coins_2_cent",
                            "coins_5_cent",
                            "coins_10_cent",
                            "coins_20_cent",
                            "coins_50_cent",
                            "coins_1_euro",
                            "coins_2_euro",
                            "notes_5_euro",
                            "notes_10_euro",
                            "notes_20_euro",
                            "notes_50_euro",
                        ),
                        0,
                    )
                    | {"notes_20_euro": 1}
                },
            )
            status, html = fetch_page(f"/cash-sessions/{session['id']}", cookie=cookie)
            for label in ("Sacs poubelle", "Frais pro", "Comptage de clôture", "Clôturé par"):
                report.check(f"suivi clôturé : « {label} » rendu", label in html)

            call("DELETE", f"{API_V1}/cash-sessions/{session['id']}", token=token)
        call("DELETE", f"{API_V1}/cash-registers/{cash_register['id']}", token=token)
        report.info("caisse et suivi de test nettoyés")

    status, templates = call("GET", f"{API_V1}/templates", token=token)
    report.status("modèles LaTeX", status)
    if isinstance(templates, list) and templates:
        status, html = fetch_page(f"/templates/{templates[0]['id']}", cookie=cookie)
        report.status("/templates/{id}", status)
        report.check("page modèle : formulaire de génération", "Générer le document" in html)
        report.check("page modèle : éditeur de variables", "Variables du modèle" in html)
        report.check("page modèle : renommage", "Renommer" in html)
    else:
        report.info("aucun modèle LaTeX : la page de détail n'est pas vérifiée")

    report.finish()


if __name__ == "__main__":
    main()
