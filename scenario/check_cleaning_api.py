"""Vérifie les plans de nettoyage, les déclarations et le planning calculé."""

import uuid

from common import (
    API_V1,
    Report,
    call,
    iso_days_ago,
    iso_days_ahead,
    login,
    require_env,
    today,
)

PLANS = f"{API_V1}/cleaning-plans"
SCHEDULE = f"{API_V1}/cleaning-schedule"


def main() -> None:
    env = require_env()
    token, _ = login(env["ADMIN_EMAIL"], env["ADMIN_PASSWORD"])
    report = Report("Plan de nettoyage — API")

    suffix = uuid.uuid4().hex[:6]
    daily_name = f"Zone vérif {suffix}"
    weekly_name = f"Chambre vérif {suffix}"
    per_use_name = f"Trancheuse vérif {suffix}"
    created_plans: list[str] = []

    status, daily = call(
        "POST",
        PLANS,
        token=token,
        body={"name": daily_name, "frequency": "daily", "products": "Détergent alimentaire"},
    )
    report.status("création d'un plan quotidien", status, 201)
    if isinstance(daily, dict):
        created_plans.append(daily["id"])
        report.equals("dû dès sa création", daily["next_due_date"], today().isoformat())

    status, payload = call(
        "POST", PLANS, token=token, body={"name": daily_name.upper(), "frequency": "daily"}
    )
    report.status("doublon insensible à la casse refusé", status, 409)
    if isinstance(payload, dict):
        report.equals("code d'erreur", payload.get("code"), "cleaning_plan_name_conflict")

    status, weekly = call(
        "POST", PLANS, token=token, body={"name": weekly_name, "frequency": "weekly"}
    )
    report.status("création d'un plan hebdomadaire", status, 201)
    if isinstance(weekly, dict):
        created_plans.append(weekly["id"])

    status, per_use = call(
        "POST", PLANS, token=token, body={"name": per_use_name, "frequency": "after_each_use"}
    )
    report.status("création d'un plan après chaque usage", status, 201)
    if isinstance(per_use, dict):
        created_plans.append(per_use["id"])
        report.check("aucune échéance pour un après-usage", per_use["next_due_date"] is None)

    record_id = None
    if isinstance(daily, dict):
        status, record = call(
            "POST",
            f"{PLANS}/{daily['id']}/records",
            token=token,
            body={"cleaning_date": today().isoformat(), "comment": "  nettoyé  "},
        )
        report.status("déclaration d'un nettoyage", status, 201)
        if isinstance(record, dict):
            record_id = record["id"]
            report.equals("commentaire nettoyé", record["comment"], "nettoyé")
            report.check("auteur enregistré", bool(record["performed_by_email"]))

        status, _ = call(
            "POST",
            f"{PLANS}/{daily['id']}/records",
            token=token,
            body={"cleaning_date": today().isoformat()},
        )
        report.status("plusieurs nettoyages le même jour", status, 201)

        status, payload = call(
            "POST",
            f"{PLANS}/{daily['id']}/records",
            token=token,
            body={"cleaning_date": iso_days_ahead(2)},
        )
        report.status("déclaration future refusée", status, 422)
        if isinstance(payload, dict):
            report.equals("code d'erreur", payload.get("code"), "cleaning_date_out_of_range")

        status, day = call("GET", f"{PLANS}/{daily['id']}/records", token=token)
        report.status("déclarations listées", status)

    status, schedule = call("GET", SCHEDULE, token=token)
    report.status("prévisionnel", status)
    if isinstance(schedule, list):
        scheduled_names = [entry["name"] for entry in schedule]
        report.check("le plan après usage est exclu", per_use_name not in scheduled_names)
        report.check("le plan nettoyé passe en à venir", daily_name in scheduled_names)
        daily_entry = next((e for e in schedule if e["name"] == daily_name), None)
        if daily_entry is not None:
            report.equals("échéance quotidienne à J+1", daily_entry["next_due_date"], iso_days_ahead(1))
            report.equals("statut à venir", daily_entry["status"], "upcoming")

    if isinstance(weekly, dict):
        call(
            "POST",
            f"{PLANS}/{weekly['id']}/records",
            token=token,
            body={"cleaning_date": iso_days_ago(10), "comment": "il y a 10 jours"},
        )
        status, overdue = call("GET", f"{SCHEDULE}/overdue", token=token)
        report.status("liste du retard", status)
        if isinstance(overdue, list):
            overdue_names = [entry["name"] for entry in overdue]
            report.check("le plan hebdomadaire est en retard", weekly_name in overdue_names)
            report.check("le plan à jour ne l'est pas", daily_name not in overdue_names)
            entry = next((item for item in overdue if item["name"] == weekly_name), None)
            if entry is not None:
                report.equals("retard calculé", entry["days_late"], 3)

        status, schedule = call("GET", SCHEDULE, token=token)
        if isinstance(schedule, list):
            names = [item["name"] for item in schedule]
            if weekly_name in names and daily_name in names:
                report.check(
                    "le retard passe avant le à-venir",
                    names.index(weekly_name) < names.index(daily_name),
                )

    if record_id is not None and isinstance(daily, dict):
        status, _ = call(
            "PUT",
            f"{PLANS}/{daily['id']}/records/{record_id}",
            token=token,
            body={"cleaning_date": iso_days_ago(1)},
        )
        report.status("correction d'une déclaration", status)

        status, history = call(
            "GET", f"{PLANS}/{daily['id']}/records/{record_id}/history", token=token
        )
        report.status("journal de la déclaration", status)
        if isinstance(history, list):
            report.equals(
                "correction tracée",
                [entry["action"] for entry in history],
                ["updated", "created"],
            )
            report.equals(
                "ancienne date conservée",
                history[0]["previous_cleaning_date"],
                today().isoformat(),
            )

        status, _ = call(
            "DELETE", f"{PLANS}/{daily['id']}/records/{record_id}", token=token
        )
        report.status("suppression d'une déclaration", status, 204)
        status, history = call(
            "GET", f"{PLANS}/{daily['id']}/records/{record_id}/history", token=token
        )
        if isinstance(history, list):
            report.equals(
                "suppression tracée et historique conservé",
                [entry["action"] for entry in history],
                ["deleted", "updated", "created"],
            )

    status, payload = call("GET", f"{PLANS}/{uuid.uuid4()}/records", token=token)
    report.status("plan inconnu", status, 404)
    if isinstance(payload, dict):
        report.equals("code d'erreur", payload.get("code"), "cleaning_plan_not_found")

    status, _ = call("GET", PLANS)
    report.status("accès sans jeton refusé", status, 401)

    for plan_id in created_plans:
        call("DELETE", f"{PLANS}/{plan_id}", token=token)
    report.info(f"{len(created_plans)} plan(s) de test désactivé(s)")
    report.finish()


if __name__ == "__main__":
    main()
