"""Vérifie le référentiel des véhicules et le registre des transports."""

import uuid

from common import API_V1, Report, call, iso_days_ahead, login, require_env, today

VEHICLES = f"{API_V1}/vehicles"
TRANSPORTS = f"{API_V1}/transports"
HISTORY = f"{API_V1}/history"


def main() -> None:
    env = require_env()
    token, _ = login(env["ADMIN_EMAIL"], env["ADMIN_PASSWORD"])
    report = Report("Véhicules et transports — API")

    suffix = uuid.uuid4().hex[:6].upper()
    plate = f"VR-{suffix[:3]}-{suffix[3:]}"

    status, vehicle = call(
        "POST",
        VEHICLES,
        token=token,
        body={"name": f"Camion vérif {suffix}", "plate": plate},
    )
    report.status(f"véhicule créé ({plate})", status, 201)

    status, _ = call(
        "POST", VEHICLES, token=token, body={"name": "Doublon", "plate": plate.lower()}
    )
    report.status("plaque déjà prise", status, 409)

    status, _ = call("POST", VEHICLES, token=token, body={"name": None, "plate": None})
    report.status("véhicule sans nom ni plaque refusé", status, 422)

    transport_id = None
    if isinstance(vehicle, dict):
        status, transport = call(
            "POST",
            TRANSPORTS,
            token=token,
            body={
                "transport_date": today().isoformat(),
                "place": "Boulangerie Martin",
                "product_name": "Crème anglaise",
                "lot_number": f"LOT-{suffix}",
                "vehicle_id": vehicle["id"],
                "departure_time": "08:00",
                "departure_temperature_celsius": 3.5,
            },
        )
        report.status("transport créé avec le départ", status, 201)
        if isinstance(transport, dict):
            transport_id = transport["id"]
            report.equals(
                "véhicule repris du référentiel",
                transport["vehicle"],
                {"id": vehicle["id"], "name": vehicle["name"], "plate": plate},
            )
            report.check("transport encore incomplet", transport["is_complete"] is False)

            status, completed = call(
                "PUT",
                f"{TRANSPORTS}/{transport_id}/readings",
                token=token,
                body={"arrival_time": "10:15", "arrival_temperature_celsius": 4},
            )
            report.status("arrivée enregistrée", status)
            if isinstance(completed, dict):
                report.check("transport complet", completed["is_complete"] is True)
                report.equals(
                    "départ conservé",
                    completed["departure_temperature_celsius"],
                    3.5,
                )

    status, other = call(
        "POST",
        TRANSPORTS,
        token=token,
        body={
            "transport_date": today().isoformat(),
            "place": "Épicerie Dubois",
            "product_name": "Glace vanille",
            "vehicle_label": "Transporteur externe 1234 XYZ",
        },
    )
    report.status("transport avec un véhicule externe", status, 201)
    if isinstance(other, dict):
        report.equals("aucune référence", other["vehicle"]["id"], None)
        report.equals(
            "libellé libre repris", other["vehicle"]["name"], "Transporteur externe 1234 XYZ"
        )

    status, _ = call(
        "POST",
        TRANSPORTS,
        token=token,
        body={
            "transport_date": today().isoformat(),
            "place": "Sans véhicule",
            "product_name": "Crème",
        },
    )
    report.status("transport sans véhicule refusé", status, 422)

    status, _ = call(
        "POST",
        TRANSPORTS,
        token=token,
        body={
            "transport_date": iso_days_ahead(2),
            "place": "Trop tard",
            "product_name": "Crème",
            "vehicle_label": "Camion X",
        },
    )
    report.status("date trop future refusée", status, 422)

    status, edited = call(
        "PUT",
        f"{TRANSPORTS}/{transport_id}/readings",
        token=token,
        body={"arrival_temperature_celsius": 8},
    )
    report.status("correction d'un relevé", status)

    status, entries = call("GET", f"{HISTORY}?entity=transport", token=token)
    report.status("journal des transports", status)
    if isinstance(entries, list):
        corrected = next(entry for entry in entries if entry["action"] == "updated")
        report.equals(
            "correction tracée avec l'ancienne valeur",
            corrected["changes"],
            [
                {
                    "field": "arrival_temperature_celsius",
                    "label": "Température d'arrivée",
                    "previous": "4.00",
                    "new": "8.00",
                }
            ],
        )

    status, listing = call("GET", f"{TRANSPORTS}?lot=LOT-{suffix}", token=token)
    report.status("recherche par numéro de lot", status)
    if isinstance(listing, list):
        report.check("transport retrouvé", len(listing) == 1)

    if transport_id is not None:
        status, _ = call("DELETE", f"{TRANSPORTS}/{transport_id}", token=token)
        report.status("désactivation du transport", status, 204)
        status, _ = call("GET", f"{TRANSPORTS}/{transport_id}", token=token)
        report.status("transport désactivé inaccessible", status, 404)
    if isinstance(vehicle, dict):
        call("DELETE", f"{VEHICLES}/{vehicle['id']}", token=token)
        report.info("véhicule de test désactivé")

    status, _ = call("GET", VEHICLES)
    report.status("accès sans jeton refusé", status, 401)
    report.finish()


if __name__ == "__main__":
    main()
