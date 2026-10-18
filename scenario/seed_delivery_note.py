"""Configure le modèle de bon de livraison et toutes ses variables.

Le script remplace le source du modèle « bon-de-livraison » existant (ou le
crée) puis crée ou met à jour ses variables statiques, locales et ses lignes
produits. Il est idempotent.
"""

from __future__ import annotations

import sys
from typing import Any

from common import API_V1, REPO_ROOT, call, call_multipart, login, require_env

TEMPLATE_NAME = "bon-de-livraison"
TEMPLATE_PATH = REPO_ROOT / "templates" / "delivery-note" / "bon-de-livraison.tex"
LOGO_PATH = REPO_ROOT / "templates" / "delivery-note" / "logo-la-legu.jpg"


def variable(
    name: str,
    label: str,
    kind: str,
    *,
    value_type: str = "text",
    value: Any = None,
    description: str | None = None,
) -> dict[str, Any]:
    return {
        "name": name,
        "label": label,
        "description": description,
        "kind": kind,
        "value_type": value_type,
        "value": value,
    }


DEFINITIONS: list[dict[str, Any]] = [
    variable("vendeur_nom", "Nom de l'émetteur", "static", value="La LEGU"),
    variable(
        "vendeur_adresse_1",
        "Adresse de l'émetteur",
        "static",
        value="3 place de la carrière",
    ),
    variable(
        "vendeur_adresse_2",
        "Code postal et ville de l'émetteur",
        "static",
        value="22510 MONCONTOUR",
    ),
    variable("vendeur_pays", "Pays de l'émetteur", "static", value="France"),
    variable(
        "vendeur_email",
        "Email de l'émetteur",
        "static",
        value="eric.oms@hotmail.fr",
    ),
    variable(
        "vendeur_siret",
        "SIRET de l'émetteur",
        "static",
        value="424 366 516 00054",
    ),
    variable("vendeur_ville", "Ville de l'émetteur", "static", value="St BRIEUC"),
    variable(
        "vendeur_tva",
        "TVA de l'émetteur",
        "static",
        value="FR71424366516",
    ),
    variable(
        "vendeur_telephone",
        "Téléphone du service client",
        "static",
        value="07 68 28 40 25",
    ),
    variable(
        "entete_quantite",
        "En-tête de la colonne quantités",
        "static",
        value="NBRE POTS",
    ),
    variable(
        "mention_tva",
        "Mention TVA",
        "static",
        value="TVA non applicable, article 293 B du CGI",
    ),
    variable(
        "mention_bio",
        "Mention agriculture biologique",
        "static",
        value="*Issu agriculture biologique",
    ),
    variable(
        "logo",
        "Logo de l'émetteur",
        "static",
        value_type="image",
    ),
    variable("bl_numero", "Numéro du bon de livraison", "local"),
    variable("bl_reference", "Référence du bon de livraison", "local"),
    variable("client_nom", "Nom du client", "local"),
    variable("client_adresse_1", "Adresse du client", "local"),
    variable("client_adresse_2", "Code postal et ville du client", "local"),
    variable("client_ape", "Code APE du client", "local"),
    variable("client_siret", "SIRET du client", "local"),
    variable(
        "unite_quantite",
        "Unité de la colonne quantités",
        "local",
        value="350g",
        description="Exemple : 350g, 250g, 500g.",
    ),
    variable(
        "lignes_produits",
        "Lignes de produits",
        "local",
        value_type="products",
        value=[
            {"designation": "BOCAL - CORAIL & LEGUMES", "pots": 10, "prix": "3.95"},
            {
                "designation": "BOCAL - HARICOTS ROUGE & EPICES",
                "pots": 10,
                "prix": "3.95",
            },
            {"designation": "BOCAL - POIS CASSES CURCUMA", "pots": 9, "prix": "3.95"},
            {"designation": "BOCAL - SALADE LENTILLES", "pots": 11, "prix": "3.95"},
        ],
        description="Ajoutez ou supprimez autant de lignes que nécessaire.",
    ),
]


def main() -> None:
    env = require_env()
    if not TEMPLATE_PATH.is_file():
        sys.exit(f"Modèle introuvable : {TEMPLATE_PATH}")
    if not LOGO_PATH.is_file():
        sys.exit(f"Logo introuvable : {LOGO_PATH}")

    token, _cookie = login(env["ADMIN_EMAIL"], env["ADMIN_PASSWORD"])
    source = TEMPLATE_PATH.read_bytes()

    status, templates = call("GET", f"{API_V1}/templates", token=token)
    if status != 200 or not isinstance(templates, list):
        sys.exit(f"Impossible de lister les modèles (statut {status}).")

    existing = next(
        (item for item in templates if item.get("name") == TEMPLATE_NAME),
        None,
    )
    if existing:
        status, template = call_multipart(
            "PUT",
            f"{API_V1}/templates/{existing['id']}",
            token=token,
            filename=TEMPLATE_PATH.name,
            content=source,
        )
        action = "remplacé"
    else:
        status, template = call_multipart(
            "POST",
            f"{API_V1}/templates",
            token=token,
            filename=TEMPLATE_PATH.name,
            content=source,
            fields={"name": TEMPLATE_NAME},
        )
        action = "créé"

    if status not in (200, 201) or not isinstance(template, dict):
        sys.exit(f"Échec de l'import du modèle (statut {status}).")

    template_id = template["id"]
    status, current = call(
        "GET",
        f"{API_V1}/templates/{template_id}/variables",
        token=token,
    )
    if status != 200 or not isinstance(current, list):
        sys.exit(f"Impossible de lister les variables (statut {status}).")
    by_name = {item["name"]: item for item in current}

    created = 0
    updated = 0
    variable_ids: dict[str, str] = {}
    for definition in DEFINITIONS:
        existing_variable = by_name.get(definition["name"])
        if existing_variable:
            status, saved = call(
                "PUT",
                f"{API_V1}/templates/{template_id}/variables/{existing_variable['id']}",
                token=token,
                body=definition,
            )
            expected = 200
            updated += 1
        else:
            status, saved = call(
                "POST",
                f"{API_V1}/templates/{template_id}/variables",
                token=token,
                body=definition,
            )
            expected = 201
            created += 1
        if status != expected or not isinstance(saved, dict):
            sys.exit(f"Échec pour la variable {definition['name']} (statut {status}).")
        variable_ids[definition["name"]] = str(saved["id"])

    logo_status, _logo = call_multipart(
        "PUT",
        f"{API_V1}/templates/{template_id}/variables/{variable_ids['logo']}/image",
        token=token,
        filename=LOGO_PATH.name,
        content=LOGO_PATH.read_bytes(),
    )
    if logo_status != 200:
        sys.exit(f"Échec du téléversement du logo (statut {logo_status}).")

    print(f"Modèle « {TEMPLATE_NAME} » {action} : {template_id}")
    print(f"Variables : {created} créée(s), {updated} mise(s) à jour.")
    print(f"Logo téléversé : {LOGO_PATH.name}")
    print(f"Ouvrir : /templates/{template_id}")


if __name__ == "__main__":
    main()
