"""Vérifie que les pages du frontend rendent les données et restent protégées."""

import uuid

from common import API_V1, Report, call, fetch_page, login, require_env

#: chemin, texte attendu uniquement quand la page est rendue avec une session
PAGES: list[tuple[str, str]] = [
    ("/equipment", "Matériel"),
    ("/readings", "Relevés de température"),
    ("/cleaning", "Nettoyage"),
    ("/pasteurisation", "Pasteurisation"),
    ("/transport", "Transport"),
    ("/cash-sessions", "Suivi de caisse"),
    ("/export", "Export"),
    ("/history", "Historique"),
]


def main() -> None:
    env = require_env()
    token, cookie = login(env["ADMIN_EMAIL"], env["ADMIN_PASSWORD"])
    report = Report("Frontend — pages et protection")

    for path, marker in PAGES:
        status, html = fetch_page(path, cookie=cookie)
        report.status(f"{path} avec session", status)
        report.check(f"{path} rend son contenu", marker in html)

    for path, marker in PAGES:
        status, html = fetch_page(path)
        report.status(f"{path} sans session", status)
        report.check(f"{path} renvoie vers la connexion", "Connexion" in html)
        report.check(f"{path} ne fuit aucune donnée", marker not in html)

    status, html = fetch_page("/cleaning", cookie=cookie)
    for label in (
        "Matériel",
        "Relevés",
        "Nettoyage",
        "Plan de nettoyage",
        "Pasteurisation",
        "Suivi de caisse",
    ):
        report.check(f"onglet « {label} » présent", f">{label}<" in html)

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
    for label in (
        "Véhicules",
        "Nouveau véhicule",
        "Caisses",
        "Nouvelle caisse",
    ):
        report.check(f"page Matériel : « {label} » rendu", label in html)

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
            ):
                report.check(f"« {label} » rendu", label in html)

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

    report.finish()


if __name__ == "__main__":
    main()
