"""Vérifie les parcours création / liste / modification / suppression du matériel."""

import uuid

from common import API_V1, Report, call, login, require_env

EQUIPMENT = f"{API_V1}/equipment"


def main() -> None:
    env = require_env()
    token, _ = login(env["ADMIN_EMAIL"], env["ADMIN_PASSWORD"])
    report = Report("Matériel — API")

    name = f"Frigo vérif {uuid.uuid4().hex[:6]}"
    status, created = call("POST", EQUIPMENT, token=token, body={"name": name, "type": "fridge"})
    report.status("création avec seuils par défaut", status, 201)
    equipment_id = created["id"] if isinstance(created, dict) else None
    if isinstance(created, dict):
        report.info(
            f"seuils retenus : {created['min_temperature_celsius']} / "
            f"{created['max_temperature_celsius']} °C"
        )

    status, payload = call(
        "POST", EQUIPMENT, token=token, body={"name": name.upper(), "type": "fridge"}
    )
    report.status("doublon insensible à la casse refusé", status, 409)
    if isinstance(payload, dict):
        report.equals("code d'erreur", payload.get("code"), "equipment_name_conflict")

    status, _ = call(
        "POST",
        EQUIPMENT,
        token=token,
        body={
            "name": f"{name} bis",
            "type": "fridge",
            "min_temperature_celsius": 6,
            "max_temperature_celsius": 2,
        },
    )
    report.status("seuils incohérents refusés", status, 422)

    status, _ = call(
        "PUT",
        f"{EQUIPMENT}/{equipment_id}",
        token=token,
        body={
            "name": f"{name} (modifié)",
            "type": "freezer",
            "min_temperature_celsius": -25,
            "max_temperature_celsius": -18,
            "location": "Réserve",
        },
    )
    report.status("modification", status, 200)

    status, listing = call("GET", EQUIPMENT, token=token)
    report.status("liste", status)
    if isinstance(listing, list):
        names = [item["name"] for item in listing]
        report.check("modification visible dans la liste", f"{name} (modifié)" in names)

    status, _ = call("DELETE", f"{EQUIPMENT}/{equipment_id}", token=token)
    report.status("suppression douce", status, 204)
    status, payload = call("DELETE", f"{EQUIPMENT}/{equipment_id}", token=token)
    report.status("seconde suppression refusée", status, 404)
    if isinstance(payload, dict):
        report.equals("code d'erreur", payload.get("code"), "equipment_not_found")

    status, _ = call("GET", EQUIPMENT)
    report.status("accès sans jeton refusé", status, 401)
    report.finish()


if __name__ == "__main__":
    main()
