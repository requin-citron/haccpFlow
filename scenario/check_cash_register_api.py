"""Vérifie l'enrôlement des caisses et le calcul du montant total."""

import uuid

from common import API_V1, Report, call, login, require_env

CASH_REGISTERS = f"{API_V1}/cash-registers"


def main() -> None:
    env = require_env()
    token, _ = login(env["ADMIN_EMAIL"], env["ADMIN_PASSWORD"])
    report = Report("Caisses — API")

    suffix = uuid.uuid4().hex[:6].upper()
    name = f"Caisse vérif {suffix}"

    status, cash_register = call(
        "POST",
        CASH_REGISTERS,
        token=token,
        body={
            "name": name,
            "coins_1_cent": 12,
            "coins_50_cent": 2,
            "coins_1_euro": 3,
            "notes_50_euro": 1,
        },
    )
    report.status(f"enrôlement ({name})", status, 201)
    if isinstance(cash_register, dict):
        report.equals("compteurs repris", cash_register["coins_1_cent"], 12)
        report.equals("coupures absentes à zéro", cash_register["notes_20_euro"], 0)
        report.equals("total en centimes", cash_register["total_cents"], 5412)

    status, _ = call("POST", CASH_REGISTERS, token=token, body={"name": name.lower()})
    report.status("nom déjà pris", status, 409)

    status, _ = call(
        "POST", CASH_REGISTERS, token=token, body={"name": f"{name} bis", "coins_1_euro": -1}
    )
    report.status("compteur négatif refusé", status, 422)

    status, _ = call(
        "POST", CASH_REGISTERS, token=token, body={"name": f"{name} ter", "notes_100_euro": 2}
    )
    report.status("coupure inconnue refusée", status, 422)

    if isinstance(cash_register, dict):
        status, updated = call(
            "PUT",
            f"{CASH_REGISTERS}/{cash_register['id']}",
            token=token,
            body={"name": name, "notes_10_euro": 2},
        )
        report.status("correction du comptage", status)
        if isinstance(updated, dict):
            # Le PUT remplace toute la caisse : les compteurs non fournis
            # repartent donc à zéro.
            report.equals("total recalculé", updated["total_cents"], 2000)
            report.equals("compteurs absents remis à zéro", updated["coins_1_euro"], 0)

        status, listing = call("GET", CASH_REGISTERS, token=token)
        report.status("liste des caisses", status)
        if isinstance(listing, list):
            report.check("caisse retrouvée", any(item["name"] == name for item in listing))

        status, _ = call("DELETE", f"{CASH_REGISTERS}/{cash_register['id']}", token=token)
        report.status("désactivation", status, 204)
        status, _ = call(
            "PUT",
            f"{CASH_REGISTERS}/{cash_register['id']}",
            token=token,
            body={"name": name},
        )
        report.status("caisse désactivée inaccessible", status, 404)
        status, _ = call("POST", CASH_REGISTERS, token=token, body={"name": name})
        report.status("nom libéré", status, 201)
        if status == 201:
            _, listing = call("GET", CASH_REGISTERS, token=token)
            leftover = (
                next((item for item in listing if item["name"] == name), None)
                if isinstance(listing, list)
                else None
            )
            if leftover is not None:
                call("DELETE", f"{CASH_REGISTERS}/{leftover['id']}", token=token)
            report.info("caisses de test désactivées")

    status, _ = call("GET", CASH_REGISTERS)
    report.status("accès sans jeton refusé", status, 401)
    report.finish()


if __name__ == "__main__":
    main()
