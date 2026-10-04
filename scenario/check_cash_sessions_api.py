"""Vérifie le suivi de caisse : ouverture, frais, unicité et clôture."""

import uuid

from common import API_V1, Report, call, login, require_env

CASH_REGISTERS = f"{API_V1}/cash-registers"
CASH_SESSIONS = f"{API_V1}/cash-sessions"

DENOMINATIONS = (
    "coins_1_cent",
    "coins_2_cent",
    "coins_5_cent",
    "coins_10_cent",
    "coins_20_cent",
    "coins_50_cent",
    "coins_1_euro",
    "coins_2_euro",
    "notes_5_euro",
    "notes_10_euro",
    "notes_20_euro",
    "notes_50_euro",
)


def counts(**overrides):
    """Les douze coupures, pour un comptage toujours complet."""

    full = dict.fromkeys(DENOMINATIONS, 0)
    full.update(overrides)
    return full


def main() -> None:
    env = require_env()
    token, _ = login(env["ADMIN_EMAIL"], env["ADMIN_PASSWORD"])
    report = Report("Suivi de caisse — API")

    suffix = uuid.uuid4().hex[:6].upper()
    name = f"Caisse suivi {suffix}"

    status, cash_register = call(
        "POST",
        CASH_REGISTERS,
        token=token,
        body={"name": name, "coins_1_euro": 3, "notes_10_euro": 2},
    )
    report.status(f"enrôlement ({name})", status, 201)
    if not isinstance(cash_register, dict):
        report.finish()
        return
    register_id = cash_register["id"]

    # Ouverture : le fond de caisse est repris de la caisse elle-même.
    status, session = call(
        "POST", CASH_SESSIONS, token=token, body={"cash_register_id": register_id}
    )
    report.status("ouverture du suivi", status, 201)
    if not isinstance(session, dict):
        report.finish()
        return
    report.equals("fonds repris de la caisse", session["opening_counts"]["notes_10_euro"], 2)
    report.equals("total d'ouverture", session["opening_total_cents"], 2300)
    report.equals("suivi ouvert", session["is_open"], True)
    report.check("comptage de clôture vide", session["closing_counts"] is None)
    report.check("auteur de l'ouverture renseigné", bool(session["opened_by_email"]))

    status, _ = call("POST", CASH_SESSIONS, token=token, body={"cash_register_id": register_id})
    report.status("deuxième suivi refusé", status, 409)

    status, _ = call(
        "POST",
        CASH_SESSIONS,
        token=token,
        body={
            "cash_register_id": register_id,
            "opening_counts": counts(notes_20_euro=1),
        },
    )
    report.status("suivi ouvert toujours refusé", status, 409)

    status, _ = call("DELETE", f"{CASH_REGISTERS}/{register_id}", token=token)
    report.status("caisse désactivée impossible pendant un suivi", status, 409)

    # Frais professionnels puis personnels.
    status, session = call(
        "POST",
        f"{CASH_SESSIONS}/{session['id']}/expenses",
        token=token,
        body={
            "kind": "professional",
            "name": "Sacs poubelle",
            "quantity": 3,
            "unit_price_cents": 250,
            "vat_rate": "20.00",
        },
    )
    report.status("frais professionnel ajouté", status, 201)
    if isinstance(session, dict):
        report.equals("total de la ligne", session["expenses"][0]["total_cents"], 750)
        report.equals("tva conservée", session["expenses"][0]["vat_rate"], "20.00")
        report.equals("total des frais pro", session["expenses_professional_total_cents"], 750)

    status, session = call(
        "POST",
        f"{CASH_SESSIONS}/{session['id']}/expenses",
        token=token,
        body={
            "kind": "personal",
            "name": "Prélèvement",
            "quantity": 1,
            "unit_price_cents": 1000,
            "vat_rate": "0.00",
        },
    )
    report.status("frais personnel ajouté", status, 201)
    if not isinstance(session, dict):
        report.finish()
        return

    report.equals("total des frais perso", session["expenses_personal_total_cents"], 1000)
    report.equals("total des frais", session["expenses_total_cents"], 1750)
    expense_id = session["expenses"][1]["id"]

    status, session = call(
        "PUT",
        f"{CASH_SESSIONS}/{session['id']}/expenses/{expense_id}",
        token=token,
        body={
            "kind": "personal",
            "name": "Prélèvement corrigé",
            "quantity": 2,
            "unit_price_cents": 500,
            "vat_rate": "0.00",
        },
    )
    report.status("frais personnel corrigé", status, 200)
    if isinstance(session, dict):
        report.equals("total des frais après correction", session["expenses_total_cents"], 1750)

    status, _ = call(
        "POST",
        f"{CASH_SESSIONS}/{session['id']}/expenses",
        token=token,
        body={
            "kind": "professional",
            "name": "Frais invalide",
            "quantity": 0,
            "unit_price_cents": 100,
        },
    )
    report.status("quantité nulle refusée", status, 422)

    status, _ = call(
        "POST",
        f"{CASH_SESSIONS}/{session['id']}/close",
        token=token,
        body={"closing_counts": {"coins_1_euro": 1}},
    )
    report.status("comptage incomplet refusé", status, 422)

    # Clôture : le comptage devient l'état de la caisse.
    status, closed = call(
        "POST",
        f"{CASH_SESSIONS}/{session['id']}/close",
        token=token,
        body={"closing_counts": counts(coins_1_euro=5, notes_10_euro=2, notes_50_euro=1)},
    )
    report.status("clôture", status, 200)
    if not isinstance(closed, dict):
        report.finish()
        return

    report.equals("suivi fermé", closed["is_open"], False)
    report.equals("total de clôture", closed["closing_total_cents"], 7500)
    report.check("auteur de la clôture renseigné", bool(closed["closed_by_email"]))
    report.equals("frais conservés", closed["expenses_total_cents"], 1750)

    status, _ = call(
        "POST",
        f"{CASH_SESSIONS}/{session['id']}/expenses",
        token=token,
        body={
            "kind": "professional",
            "name": "Trop tard",
            "quantity": 1,
            "unit_price_cents": 100,
        },
    )
    report.status("frais refusés après clôture", status, 409)

    status, _ = call(
        "POST",
        f"{CASH_SESSIONS}/{session['id']}/close",
        token=token,
        body={"closing_counts": counts()},
    )
    report.status("double clôture refusée", status, 409)

    status, listing = call("GET", CASH_REGISTERS, token=token)
    if isinstance(listing, list):
        register = next((item for item in listing if item["id"] == register_id), None)
        if register is not None:
            report.equals("caisse mise à jour", register["notes_50_euro"], 1)
            report.equals("total de la caisse", register["total_cents"], 7500)

    status, listing = call("GET", f"{CASH_SESSIONS}?status=closed", token=token)
    report.status("liste des suivis clôturés", status, 200)
    if isinstance(listing, list):
        report.check(
            "suivi clôturé retrouvé",
            any(item["id"] == session["id"] for item in listing),
        )

    # La caisse n'a plus de suivi ouvert : la nouvelle ouverture reprend le
    # comptage de clôture.
    status, reopened = call(
        "POST", CASH_SESSIONS, token=token, body={"cash_register_id": register_id}
    )
    report.status("nouveau suivi après clôture", status, 201)
    if isinstance(reopened, dict):
        report.equals("fonds repris du comptage", reopened["opening_counts"]["notes_50_euro"], 1)
        call("DELETE", f"{CASH_SESSIONS}/{reopened['id']}", token=token)

    status, _ = call("DELETE", f"{CASH_SESSIONS}/{session['id']}", token=token)
    report.status("suppression d'un suivi clôturé", status, 204)

    status, _ = call("DELETE", f"{CASH_REGISTERS}/{register_id}", token=token)
    report.status("caisse désactivée", status, 204)
    report.info("caisse et suivis de test nettoyés")

    status, _ = call("GET", CASH_SESSIONS)
    report.status("accès sans jeton refusé", status, 401)
    report.finish()


if __name__ == "__main__":
    main()
