"use server";

import { revalidatePath } from "next/cache";

import { ApiError, apiFetch } from "@/lib/api";
import type { CreateEquipmentState } from "@/lib/form-state";
import type { EquipmentType } from "@/lib/types";

const EQUIPMENT_PATH = "/api/v1/equipment";

function readOptionalText(formData: FormData, field: string): string | null {
  const value = String(formData.get(field) ?? "").trim();
  return value === "" ? null : value;
}

function readOptionalNumber(formData: FormData, field: string): number | null {
  const value = String(formData.get(field) ?? "")
    .trim()
    .replace(",", ".");
  if (value === "") {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function readEquipmentType(formData: FormData): EquipmentType {
  return formData.get("type") === "freezer" ? "freezer" : "fridge";
}

function describeError(error: unknown): string {
  if (error instanceof ApiError) {
    switch (error.status) {
      case 409:
        return "Un matériel actif porte déjà ce nom.";
      case 422:
        return "Vérifie les seuils : les deux doivent être renseignés ensemble, et le minimum doit rester inférieur au maximum.";
      case 403:
        return "Cette action est réservée aux administrateurs.";
      case 401:
        return "Ta session a expiré, reconnecte-toi.";
      default:
        return error.message;
    }
  }
  return "Une erreur inattendue est survenue.";
}

export async function createEquipmentAction(
  _previous: CreateEquipmentState,
  formData: FormData,
): Promise<CreateEquipmentState> {
  const name = String(formData.get("name") ?? "").trim();
  if (!name) {
    return { status: "error", message: "Le nom du matériel est obligatoire." };
  }

  const minimum = readOptionalNumber(formData, "min_temperature_celsius");
  const maximum = readOptionalNumber(formData, "max_temperature_celsius");
  if ((minimum === null) !== (maximum === null)) {
    return {
      status: "error",
      message: "Renseigne les deux seuils, ou laisse les deux vides pour utiliser les valeurs par défaut.",
    };
  }

  const payload = {
    name,
    type: readEquipmentType(formData),
    location: readOptionalText(formData, "location"),
    notes: readOptionalText(formData, "notes"),
    ...(minimum !== null && maximum !== null
      ? { min_temperature_celsius: minimum, max_temperature_celsius: maximum }
      : {}),
  };

  try {
    await apiFetch(EQUIPMENT_PATH, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (error) {
    return { status: "error", message: describeError(error) };
  }

  revalidatePath("/equipment");
  return { status: "success" };
}

export async function deleteEquipmentAction(equipmentId: string): Promise<void> {
  try {
    await apiFetch(`${EQUIPMENT_PATH}/${encodeURIComponent(equipmentId)}`, { method: "DELETE" });
  } catch (error) {
    // Already gone: the user's intent is satisfied.
    if (!(error instanceof ApiError && error.status === 404)) {
      throw error;
    }
  }
  revalidatePath("/equipment");
}
