"""Télécharge les quatre exports CSV et vérifie leur format."""

from common import API_V1, Report, call_bytes, login, require_env

EXPORTS = f"{API_V1}/exports"

#: jeu de données, début de la ligne d'en-tête attendue
EXPECTED_HEADERS = {
    "readings": "Matériel;Type;Date;Créneau",
    "cleanings": "Plan;Fréquence;Produits",
    "pasteurisations": "Date;Produit;N° de lot;Quantité;Préchauffage — début",
    "transports": "Date;Produit;N° de lot;Lieu;Véhicule",
}


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

    status, _, _ = call_bytes("GET", f"{EXPORTS}/readings")
    report.status("accès sans jeton refusé", status, 401)
    report.finish()


if __name__ == "__main__":
    main()
