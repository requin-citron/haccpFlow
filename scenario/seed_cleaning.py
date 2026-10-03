"""Crée un jeu de plans de nettoyage couvrant tous les états de l'interface.

Idempotent : un plan dont le nom existe déjà est réutilisé au lieu d'être
recréé. Les déclarations, elles, sont ajoutées à chaque exécution.
"""

from typing import Any

from common import API_V1, Report, call, iso_days_ago, login, require_env, today

PLANS = f"{API_V1}/cleaning-plans"
SCHEDULE = f"{API_V1}/cleaning-schedule"

#: nom, fréquence, produits
DEMO_PLANS: list[tuple[str, str, str]] = [
    ("Zone de préparation", "daily", "Détergent alimentaire, essuyage, rinçage"),
    ("Chambre froide n°1", "weekly", "Produit désinfectant alimentaire, dosage 0,5 %"),
    ("Trancheuse à jambon", "after_each_use", "Eau chaude + détergent, rinçage, séchage"),
    ("Vitrine pâtisserie", "daily", "Nettoyant vitres alimentaire"),
]


def ensure_plan(token: str, name: str, frequency: str, products: str) -> dict[str, Any] | None:
    status, created = call(
        "POST",
        PLANS,
        token=token,
        body={"name": name, "frequency": frequency, "products": products},
    )
    if status == 201:
        return created
    _, listing = call("GET", PLANS, token=token)
    return next((plan for plan in listing if plan["name"] == name), None)


def main() -> None:
    env = require_env()
    token, _ = login(env["ADMIN_EMAIL"], env["ADMIN_PASSWORD"])
    report = Report("Jeu de démonstration — plan de nettoyage")

    plans = {}
    for name, frequency, products in DEMO_PLANS:
        plan = ensure_plan(token, name, frequency, products)
        report.check(f"plan « {name} » disponible", plan is not None)
        if plan is not None:
            plans[name] = plan

    daily = plans.get("Zone de préparation")
    weekly = plans.get("Chambre froide n°1")
    per_use = plans.get("Trancheuse à jambon")

    if daily is not None:
        status, record = call(
            "POST",
            f"{PLANS}/{daily['id']}/records",
            token=token,
            body={"cleaning_date": iso_days_ago(1), "comment": "Réalisé en fin de service"},
        )
        report.status("Zone de préparation : nettoyage d'hier", status, 201)
        if status == 201 and isinstance(record, dict):
            status, _ = call(
                "PUT",
                f"{PLANS}/{daily['id']}/records/{record['id']}",
                token=token,
                body={
                    "cleaning_date": today().isoformat(),
                    "comment": "Réalisé en fin de service, plan de travail inclus",
                },
            )
            report.status("Zone de préparation : date corrigée (journal)", status)

    if weekly is not None:
        status, _ = call(
            "POST",
            f"{PLANS}/{weekly['id']}/records",
            token=token,
            body={"cleaning_date": iso_days_ago(10), "comment": "Désinfection complète"},
        )
        report.status("Chambre froide : nettoyage il y a 10 jours (retard)", status, 201)

    if per_use is not None:
        for index in (1, 2):
            status, _ = call(
                "POST",
                f"{PLANS}/{per_use['id']}/records",
                token=token,
                body={
                    "cleaning_date": today().isoformat(),
                    "comment": f"Démontage et nettoyage n°{index}",
                },
            )
            report.status(f"Trancheuse : nettoyage n°{index}", status, 201)

    status, schedule = call("GET", SCHEDULE, token=token)
    report.status("prévisionnel", status)
    if isinstance(schedule, list):
        for entry in schedule:
            late = f" · {entry['days_late']} j de retard" if entry["days_late"] else ""
            report.info(
                f"{entry['name']} — échéance {entry['next_due_date']} · {entry['status']}{late}"
            )
    report.finish()


if __name__ == "__main__":
    main()
