"""Vérifie le registre de pasteurisation : lot, trois phases et audit."""

import uuid
from typing import Any

from common import API_V1, Report, call, iso_days_ahead, login, require_env, today

BATCHES = f"{API_V1}/pasteurisations"
PHASES = ("preheating", "holding", "cooling")


def _phase(body: dict[str, Any], name: str) -> dict[str, Any]:
    return next(item for item in body["phases"] if item["phase"] == name)


def main() -> None:
    env = require_env()
    token, _ = login(env["ADMIN_EMAIL"], env["ADMIN_PASSWORD"])
    report = Report("Pasteurisation — API")

    lot = f"LOT-VERIF-{uuid.uuid4().hex[:6].upper()}"
    status, batch = call(
        "POST",
        BATCHES,
        token=token,
        body={
            "batch_date": today().isoformat(),
            "product_name": "Crème anglaise",
            "lot_number": lot,
            "quantity": 120,
        },
    )
    report.status(f"création du lot {lot}", status, 201)
    if not isinstance(batch, dict):
        report.finish()
        return

    batch_id = batch["id"]

    def phase_url(name: str) -> str:
        return f"{BATCHES}/{batch_id}/phases/{name}"

    report.equals(
        "les trois phases sont présentes dans l'ordre",
        [item["phase"] for item in batch["phases"]],
        list(PHASES),
    )
    report.equals("aucune phase remplie", batch["filled_phases"], 0)
    report.check("lot incomplet", batch["is_complete"] is False)

    status, body = call("PUT", phase_url("preheating"), token=token, body={"started_at": "09:00"})
    report.status("début du préchauffage seul", status)
    if isinstance(body, dict):
        report.check("fin encore vide", _phase(body, "preheating")["ended_at"] is None)
        report.equals("phase comptée comme entamée", body["filled_phases"], 1)

    status, body = call("PUT", phase_url("preheating"), token=token, body={"ended_at": "09:30"})
    report.status("fin du préchauffage", status)
    if isinstance(body, dict):
        preheating = _phase(body, "preheating")
        report.equals("début conservé", preheating["started_at"], "09:00:00")
        report.equals("durée calculée", preheating["duration_minutes"], 30)

    for phase, start, end, temperature in (
        ("preheating", "09:00", "09:30", 85),
        ("holding", "09:30", "10:05", 85),
        ("cooling", "10:05", "10:50", 4),
    ):
        status, body = call(
            "PUT",
            phase_url(phase),
            token=token,
            body={
                "started_at": start,
                "ended_at": end,
                "target_temperature_celsius": temperature,
                "observation": "RAS" if phase == "holding" else None,
            },
        )
        report.status(f"phase {phase} complétée", status)

    if isinstance(body, dict):
        report.equals("trois phases remplies", body["filled_phases"], 3)
        report.check("lot complet", body["is_complete"] is True)
        report.equals("durée du palier", _phase(body, "holding")["duration_minutes"], 35)

    status, _ = call(
        "PUT", phase_url("holding"), token=token, body={"started_at": "09:40"}
    )
    report.status("correction de l'heure de début", status)
    status, history = call("GET", f"{phase_url('holding')}/history", token=token)
    report.status("journal de la phase", status)
    if isinstance(history, list):
        report.equals(
            "correction tracée",
            [entry["action"] for entry in history][:2],
            ["updated", "created"],
        )
        report.equals(
            "ancienne heure conservée", history[0]["previous_started_at"], "09:30:00"
        )

    status, _ = call(
        "PUT", phase_url("holding"), token=token, body={"started_at": "09:40"}
    )
    status, history = call("GET", f"{phase_url('holding')}/history", token=token)
    if isinstance(history, list):
        report.check("réécriture identique non journalisée", len(history) == 2)

    status, payload = call(
        "PUT",
        phase_url("cooling"),
        token=token,
        body={"started_at": "11:00", "ended_at": "10:00"},
    )
    report.status("fin avant le début refusée", status, 422)
    if isinstance(payload, dict):
        report.equals("code d'erreur", payload.get("code"), "pasteurisation_phase_time_invalid")

    status, _ = call("PUT", phase_url("holding"), token=token, body={})
    report.status("corps de phase vide refusé", status, 422)

    status, _ = call(
        "PUT", phase_url("fermentation"), token=token, body={"observation": "x"}
    )
    report.status("phase inconnue refusée", status, 422)

    status, payload = call(
        "POST",
        BATCHES,
        token=token,
        body={
            "batch_date": iso_days_ahead(2),
            "product_name": "Crème",
            "lot_number": "LOT-FUTUR",
            "quantity": 10,
        },
    )
    report.status("date de lot trop future refusée", status, 422)
    if isinstance(payload, dict):
        report.equals("code d'erreur", payload.get("code"), "pasteurisation_date_out_of_range")

    status, _ = call(
        "POST",
        BATCHES,
        token=token,
        body={
            "batch_date": today().isoformat(),
            "product_name": "Crème",
            "lot_number": "LOT-ZERO",
            "quantity": 0,
        },
    )
    report.status("quantité nulle refusée", status, 422)

    status, listing = call("GET", f"{BATCHES}?lot={lot}", token=token)
    report.status("recherche par numéro de lot", status)
    if isinstance(listing, list):
        report.equals("lot retrouvé", [item["lot_number"] for item in listing], [lot])

    status, _ = call("GET", BATCHES)
    report.status("accès sans jeton refusé", status, 401)

    status, _ = call("DELETE", f"{BATCHES}/{batch_id}", token=token)
    report.status("désactivation du lot", status, 204)
    status, _ = call("GET", f"{BATCHES}/{batch_id}", token=token)
    report.status("lot désactivé inaccessible", status, 404)

    report.finish()


if __name__ == "__main__":
    main()
