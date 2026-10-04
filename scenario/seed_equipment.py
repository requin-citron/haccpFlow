"""Crée trois équipements et deux véhicules de démonstration.

Idempotent : une entrée dont le nom ou la plaque existe déjà est ignorée.
"""

from common import API_V1, Report, call, login, require_env

EQUIPMENT = f"{API_V1}/equipment"
VEHICLES = f"{API_V1}/vehicles"

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

#: nom, plaque
DEMO_VEHICLES: list[tuple[str, str]] = [
    ("Camion frigo 1", "AB-123-CD"),
    ("Camion frigo 2", "EF-456-GH"),
]


def main() -> None:
    env = require_env()
    token, _ = login(env["ADMIN_EMAIL"], env["ADMIN_PASSWORD"])
    report = Report("Jeu de démonstration — matériel et véhicules")

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

    for name, plate in DEMO_VEHICLES:
        status, _ = call(
            "POST", VEHICLES, token=token, body={"name": name, "plate": plate}
        )
        if status == 409:
            report.info(f"véhicule {plate} : déjà présent, ignoré")
            continue
        report.status(f"véhicule {name} créé", status, 201)

    status, listing = call("GET", EQUIPMENT, token=token)
    report.status("liste du matériel", status)
    if isinstance(listing, list):
        report.info(f"{len(listing)} équipement(s) actif(s)")

    status, vehicles = call("GET", VEHICLES, token=token)
    report.status("liste des véhicules", status)
    if isinstance(vehicles, list):
        report.info(f"{len(vehicles)} véhicule(s) actif(s)")
    report.finish()


if __name__ == "__main__":
    main()
