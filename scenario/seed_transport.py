"""Crée trois transports de démonstration couvrant les états de l'interface.

Idempotent : un lot déjà présent est ignoré. Les véhicules référencés viennent
de `seed_equipment.py` ; s'ils manquent, le transport bascule sur un libellé
libre plutôt que d'échouer.
"""

from typing import Any

from common import API_V1, Report, call, login, require_env, today

TRANSPORTS = f"{API_V1}/transports"
VEHICLES = f"{API_V1}/vehicles"

#: lot, produit, lieu, plaque attendue, départ (heure, °C), arrivée ou None
DEMO_TRANSPORTS: list[tuple[str, str, str, str, tuple[str, float], tuple[str, float] | None]] = [
    (
        "LOT-TR-001",
        "Crème anglaise",
        "Boulangerie Martin",
        "AB-123-CD",
        ("08:00", 3.5),
        ("10:15", 4),
    ),
    (
        "LOT-TR-002",
        "Glace vanille",
        "Épicerie Dubois",
        "EF-456-GH",
        ("14:00", -18),
        None,
    ),
    (
        "LOT-TR-003",
        "Crème brûlée",
        "Restaurant Le Comptoir",
        "",
        ("16:30", 2.5),
        None,
    ),
]


def main() -> None:
    env = require_env()
    token, _ = login(env["ADMIN_EMAIL"], env["ADMIN_PASSWORD"])
    report = Report("Jeu de démonstration — transports")

    status, vehicles = call("GET", VEHICLES, token=token)
    by_plate = {
        vehicle["plate"]: vehicle
        for vehicle in (vehicles if isinstance(vehicles, list) else [])
        if vehicle["plate"]
    }

    for lot, product, place, plate, departure, arrival in DEMO_TRANSPORTS:
        existing = call("GET", f"{TRANSPORTS}?lot={lot}", token=token)[1]
        if isinstance(existing, list) and existing:
            report.info(f"transport {lot} : déjà présent, ignoré")
            continue

        vehicle: dict[str, Any] | None = by_plate.get(plate)
        payload: dict[str, Any] = {
            "transport_date": today().isoformat(),
            "place": place,
            "product_name": product,
            "lot_number": lot,
        }
        if vehicle is not None:
            payload["vehicle_id"] = vehicle["id"]
        else:
            payload["vehicle_label"] = f"Transporteur externe {lot[-3:]}"

        status, transport = call("POST", TRANSPORTS, token=token, body=payload)
        report.status(f"transport {lot} créé ({product})", status, 201)
        if status != 201 or not isinstance(transport, dict):
            continue

        start_time, start_temperature = departure
        status, _ = call(
            "PUT",
            f"{TRANSPORTS}/{transport['id']}/readings",
            token=token,
            body={
                "departure_time": start_time,
                "departure_temperature_celsius": start_temperature,
            },
        )
        report.status(f"  {lot} · départ déclaré", status)

        if arrival is not None:
            end_time, end_temperature = arrival
            status, body = call(
                "PUT",
                f"{TRANSPORTS}/{transport['id']}/readings",
                token=token,
                body={
                    "arrival_time": end_time,
                    "arrival_temperature_celsius": end_temperature,
                    "observation": "Produit conforme à l'arrivée",
                },
            )
            report.status(f"  {lot} · arrivée déclarée", status)
            if isinstance(body, dict):
                report.check(f"  {lot} · chaîne du froid complète", body["is_complete"] is True)

    status, listing = call("GET", TRANSPORTS, token=token)
    report.status("registre des transports", status)
    if isinstance(listing, list):
        for transport in listing:
            state = "complet" if transport["is_complete"] else "en cours"
            report.info(
                f"{transport['lot_number']} — {transport['product_name']} · "
                f"{transport['vehicle']['name']} · {state}"
            )
    report.finish()


if __name__ == "__main__":
    main()
