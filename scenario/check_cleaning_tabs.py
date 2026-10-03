"""Vérifie la séparation entre l'onglet opérationnel et la gestion des plans."""

from common import API_V1, Report, call, fetch_page, login, require_env

PLANS = f"{API_V1}/cleaning-plans"


def main() -> None:
    env = require_env()
    token, cookie = login(env["ADMIN_EMAIL"], env["ADMIN_PASSWORD"])
    report = Report("Nettoyage — onglet opérationnel et gestion des plans")

    status, html = fetch_page("/cleaning", cookie=cookie)
    report.status("/cleaning", status)
    report.check("renvoi vers la gestion des plans", "Gérer les plans" in html)
    report.check("aucun bouton de création", "Nouveau plan" not in html)
    report.check("aucune désactivation", "Désactiver" not in html)
    report.check("onglet Nettoyage", ">Nettoyage<" in html)
    report.check("onglet Plan de nettoyage", ">Plan de nettoyage<" in html)

    status, listing = call("GET", PLANS, token=token)
    has_schedule = isinstance(listing, list) and any(
        plan["next_due_date"] for plan in listing
    )
    if has_schedule:
        report.check("prochaine action mise en avant", "Prochain nettoyage" in html)
        report.check("liste ordonnée par urgence", "Dans l'ordre" in html)
        report.check("bouton de déclaration", "Déclarer" in html)
    else:
        report.info("aucun plan planifié : lance seed_cleaning.py pour remplir l'agenda")

    status, html = fetch_page("/cleaning/plans", cookie=cookie)
    report.status("/cleaning/plans", status)
    report.check("bouton de création", "Nouveau plan" in html)
    report.check("action de modification", "Modifier" in html)
    report.check("colonne d'échéance", "Prochaine échéance" in html)
    report.check("aucun bouton de déclaration", "Déclarer" not in html)
    report.finish()


if __name__ == "__main__":
    main()
