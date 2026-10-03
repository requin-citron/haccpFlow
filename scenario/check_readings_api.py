"""Vérifie la saisie, la complétion et la correction des relevés de température."""

import uuid

from common import API_V1, Report, call, iso_days_ago, iso_days_ahead, login, require_env, today

EQUIPMENT = f"{API_V1}/equipment"


def main() -> None:
    env = require_env()
    token, _ = login(env["ADMIN_EMAIL"], env["ADMIN_PASSWORD"])
    report = Report("Relevés de température — API")

    name = f"Frigo relevés {uuid.uuid4().hex[:6]}"
    status, equipment = call(
        "POST",
        EQUIPMENT,
        token=token,
        body={
            "name": name,
            "type": "fridge",
            "min_temperature_celsius": 0,
            "max_temperature_celsius": 4,
        },
    )
    report.status("matériel de test créé", status, 201)
    if not isinstance(equipment, dict):
        report.finish()
        return

    equipment_id = equipment["id"]
    day_url = f"{EQUIPMENT}/{equipment_id}/readings/{today().isoformat()}"

    status, day = call("PUT", day_url, token=token, body={"morning_celsius": 2.5})
    report.status("saisie du matin seul", status)
    if isinstance(day, dict):
        report.check("le soir reste vide", day["evening"] is None)

    status, day = call("PUT", day_url, token=token, body={"evening_celsius": 3.5})
    report.status("complétion du soir", status)
    if isinstance(day, dict):
        report.check(
            "le matin n'est pas écrasé",
            day["morning"]["temperature_celsius"] == 2.5,
            f"matin={day['morning']['temperature_celsius']}",
        )

    status, day = call("PUT", day_url, token=token, body={"morning_celsius": 9})
    report.status("correction hors seuils", status)
    if isinstance(day, dict):
        report.check("relevé marqué non conforme", day["morning"]["is_compliant"] is False)

    status, history = call("GET", f"{day_url}/history", token=token)
    report.status("historique", status)
    if isinstance(history, list):
        # L'historique couvre la journée entière, donc les deux créneaux.
        report.equals("la correction est la plus récente", history[0]["action"], "updated")
        report.equals("valeur précédente conservée", history[0]["previous_celsius"], 2.5)
        report.check(
            "les créations sont aussi journalisées",
            sum(1 for entry in history if entry["action"] == "created") == 2,
        )

    status, _ = call(
        "PUT",
        f"{EQUIPMENT}/{equipment_id}/readings/{iso_days_ago(1)}",
        token=token,
        body={"morning_celsius": 1, "evening_celsius": 2},
    )
    report.status("saisie antidatée acceptée", status)

    status, payload = call(
        "PUT",
        f"{EQUIPMENT}/{equipment_id}/readings/{iso_days_ahead(2)}",
        token=token,
        body={"morning_celsius": 1},
    )
    report.status("date trop future refusée", status, 422)
    if isinstance(payload, dict):
        report.equals("code d'erreur", payload.get("code"), "reading_date_out_of_range")

    status, payload = call("PUT", day_url, token=token, body={})
    report.status("saisie vide refusée", status, 422)
    if isinstance(payload, dict):
        report.equals("code d'erreur", payload.get("code"), "reading_value_required")

    status, _ = call("PUT", day_url, token=token, body={"morning_celsius": -300})
    report.status("température impossible refusée", status, 422)

    status, range_days = call(
        "GET", f"{EQUIPMENT}/{equipment_id}/readings", token=token
    )
    report.status("plage par défaut", status)
    if isinstance(range_days, list):
        report.equals("sept jours renvoyés", len(range_days), 7)
        report.equals("dernier jour = aujourd'hui", range_days[-1]["reading_date"], today().isoformat())

    call("DELETE", f"{EQUIPMENT}/{equipment_id}", token=token)
    report.info("matériel de test supprimé")
    report.finish()


if __name__ == "__main__":
    main()
