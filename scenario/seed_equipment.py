"""Crée trois équipements de démonstration.

Idempotent : un équipement dont le nom existe déjà est ignoré.
"""

from common import API_V1, Report, call, login, require_env

EQUIPMENT = f"{API_V1}/equipment"

DEMO_EQUIPMENT: list[dict[str, object]] = [
    {
        "name": "Frigo cuisine",
        "type": "fridge",
        "location": "Cuisine",
        "notes": "Sous le plan de travail, à côté de la chambre froide",
    },
    {
        "name": "Frigo bar",
        "type": "fridge",
        "min_temperature_celsius": 2,
        "max_temperature_celsius": 6,
        "location": "Salle",
    },
    {"name": "Congélateur réserve", "type": "freezer", "location": "Réserve"},
]


def main() -> None:
    env = require_env()
    token, _ = login(env["ADMIN_EMAIL"], env["ADMIN_PASSWORD"])
    report = Report("Jeu de démonstration — matériel")

    for payload in DEMO_EQUIPMENT:
        name = str(payload["name"])
        status, created = call("POST", EQUIPMENT, token=token, body=payload)
        if status == 409:
            report.info(f"{name} : déjà présent, ignoré")
            continue
        report.status(f"{name} créé", status, 201)
        if status == 201 and isinstance(created, dict):
            report.info(
                f"seuils retenus : {created['min_temperature_celsius']} / "
                f"{created['max_temperature_celsius']} °C"
            )

    status, listing = call("GET", EQUIPMENT, token=token)
    report.status("liste du matériel", status)
    if isinstance(listing, list):
        report.info(f"{len(listing)} équipement(s) actif(s)")
    report.finish()


if __name__ == "__main__":
    main()
