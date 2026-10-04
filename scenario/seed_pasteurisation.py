"""Crée trois lots de pasteurisation couvrant tous les états de l'interface.

Idempotent : un lot dont le numéro existe déjà est ignoré, mais ses phases
restent celles déjà saisies.
"""

from typing import Any

from common import API_V1, Report, call, login, require_env, today

BATCHES = f"{API_V1}/pasteurisations"

#: produit, lot, quantité, phases (début, fin, température cible)
DEMO_BATCHES: list[tuple[str, str, int, dict[str, tuple[str, str, float]]]] = [
    (
        "Crème anglaise",
        "LOT-2026-042",
        120,
        {
            "preheating": ("09:00", "09:30", 85),
            "holding": ("09:30", "10:05", 85),
            "cooling": ("10:05", "10:50", 4),
        },
    ),
    (
        "Glace vanille",
        "LOT-2026-043",
        80,
        {"preheating": ("14:00", "14:25", 85)},
    ),
    ("Crème brûlée", "LOT-2026-044", 60, {}),
]


def main() -> None:
    env = require_env()
    token, _ = login(env["ADMIN_EMAIL"], env["ADMIN_PASSWORD"])
    report = Report("Jeu de démonstration — pasteurisation")

    for product, lot, quantity, phases in DEMO_BATCHES:
        status, batch = call(
            "POST",
            BATCHES,
            token=token,
            body={
                "batch_date": today().isoformat(),
                "product_name": product,
                "lot_number": lot,
                "quantity": quantity,
            },
        )
        if status == 201 and isinstance(batch, dict):
            report.status(f"lot {lot} créé ({product})", status, 201)
        else:
            _, listing = call("GET", f"{BATCHES}?lot={lot}", token=token)
            batch = listing[0] if isinstance(listing, list) and listing else None
            report.info(f"lot {lot} : déjà présent, réutilisé")
        if not isinstance(batch, dict):
            continue

        for phase, (start, end, temperature) in phases.items():
            status, body = call(
                "PUT",
                f"{BATCHES}/{batch['id']}/phases/{phase}",
                token=token,
                body={
                    "started_at": start,
                    "ended_at": end,
                    "target_temperature_celsius": temperature,
                },
            )
            report.status(f"  {lot} · phase {phase}", status)
            if phase == "holding" and isinstance(body, dict):
                holding = next(item for item in body["phases"] if item["phase"] == "holding")
                report.info(f"durée du palier : {holding['duration_minutes']} min")

    status, listing = call("GET", BATCHES, token=token)
    report.status("registre", status)
    if isinstance(listing, list):
        for batch in listing:
            report.info(
                f"{batch['lot_number']} — {batch['product_name']} · "
                f"{batch['filled_phases']}/{len(batch['phases'])} phases"
            )
    report.finish()


if __name__ == "__main__":
    main()
