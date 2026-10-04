"""Télécharge les cinq exports CSV et l'extract d'un suivi de caisse."""

import uuid

from common import API_V1, Report, call, call_bytes, login, require_env

EXPORTS = f"{API_V1}/exports"
CASH_REGISTERS = f"{API_V1}/cash-registers"
CASH_SESSIONS = f"{API_V1}/cash-sessions"

#: jeu de données, début de la ligne d'en-tête attendue
EXPECTED_HEADERS = {
    "readings": "Matériel;Type;Date;Créneau",
    "cleanings": "Plan;Fréquence;Produits",
    "pasteurisations": "Date;Produit;N° de lot;Quantité;Préchauffage — début",
    "transports": "Date;Produit;N° de lot;Lieu;Véhicule",
    "cash-registers": "Caisse;Date;Fond — total (€);Fond — 1 centime",
}

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
    report = Report("Export CSV")

    for dataset, expected_header in EXPECTED_HEADERS.items():
        status, payload, headers = call_bytes("GET", f"{EXPORTS}/{dataset}", token=token)
        report.status(f"export {dataset}", status)
        report.check("  BOM UTF-8", payload.startswith(b"\xef\xbb\xbf"))
        if not payload:
            continue

        lines = payload.decode("utf-8-sig").splitlines()
        report.check(
            "  en-tête conforme",
            lines[0].startswith(expected_header),
            lines[0][:60],
        )
        report.check(
            "  séparateur point-virgule",
            ";" in lines[0],
        )
        report.info(
            f"  {len(lines) - 1} ligne(s) · {headers.get('content-disposition', '')}"
        )

    # L'extract d'un seul suivi : caisse + frais + clôture, puis nettoyage.
    suffix = uuid.uuid4().hex[:6].upper()
    status, cash_register = call(
        "POST",
        CASH_REGISTERS,
        token=token,
        body={"name": f"Caisse export {suffix}", "coins_1_euro": 3},
    )
    report.status("caisse de test créée", status, 201)
    if isinstance(cash_register, dict):
        status, session = call(
            "POST",
            CASH_SESSIONS,
            token=token,
            body={"cash_register_id": cash_register["id"]},
        )
        report.status("suivi de test ouvert", status, 201)
        if isinstance(session, dict):
            call(
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
            call(
                "POST",
                f"{CASH_SESSIONS}/{session['id']}/close",
                token=token,
                body={"closing_counts": counts(coins_1_euro=5, notes_10_euro=2)},
            )

            status, payload, headers = call_bytes(
                "GET", f"{CASH_SESSIONS}/{session['id']}/export", token=token
            )
            report.status("extract d'un suivi", status)
            report.check("  BOM UTF-8", payload.startswith(b"\xef\xbb\xbf"))
            disposition = headers.get("content-disposition", "")
            report.check("  nom de fichier", "caisse-caisse-export-" in disposition, disposition)
            text = payload.decode("utf-8-sig") if payload else ""
            for block in (
                f"Suivi de caisse;Caisse export {suffix}",
                "Comptage d'ouverture",
                "Total;;3,00",
                "Frais pro;Sacs poubelle;3;2,50;20,00;7,50",
                "Total des frais (€);7,50",
                "Comptage de clôture",
                "Total;;25,00",
            ):
                report.check(f"  bloc « {block} »", block in text)

            call("DELETE", f"{CASH_SESSIONS}/{session['id']}", token=token)
        call("DELETE", f"{CASH_REGISTERS}/{cash_register['id']}", token=token)
        report.info("caisse et suivi de test nettoyés")

    status, _, _ = call_bytes("GET", f"{EXPORTS}/readings")
    report.status("accès sans jeton refusé", status, 401)
    report.finish()


if __name__ == "__main__":
    main()
