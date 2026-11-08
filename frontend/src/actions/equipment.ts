"use server";

import { revalidatePath } from "next/cache";

import { ApiError, apiFetch } from "@/lib/api";
import { translateApiError } from "@/lib/api-errors";
import type { EquipmentFormState } from "@/lib/form-state";
import { t, type Locale } from "@/lib/i18n";
import { getLocale } from "@/lib/locale";
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

type PayloadResult =
  | { ok: true; payload: Record<string, unknown> }
  | { ok: false; error: string };

function buildPayload(formData: FormData, locale: Locale): PayloadResult {
  const name = String(formData.get("name") ?? "").trim();
  if (!name) {
    return { ok: false, error: t(locale, "Le nom du matériel est obligatoire.") };
  }

  const minimum = readOptionalNumber(formData, "min_temperature_celsius");
  const maximum = readOptionalNumber(formData, "max_temperature_celsius");
  if ((minimum === null) !== (maximum === null)) {
    return {
      ok: false,
      error: t(
        locale,
        "Renseigne les deux seuils, ou laisse les deux vides pour utiliser les valeurs par défaut.",
      ),
    };
  }

  return {
    ok: true,
    payload: {
      name,
      type: readEquipmentType(formData),
      location: readOptionalText(formData, "location"),
      notes: readOptionalText(formData, "notes"),
      ...(minimum !== null && maximum !== null
        ? { min_temperature_celsius: minimum, max_temperature_celsius: maximum }
        : {}),
    },
  };
}

export async function createEquipmentAction(
  _previous: EquipmentFormState,
  formData: FormData,
): Promise<EquipmentFormState> {
  const locale = await getLocale();
  const result = buildPayload(formData, locale);
  if (!result.ok) {
    return { status: "error", message: result.error };
  }

  try {
    await apiFetch(EQUIPMENT_PATH, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(result.payload),
    });
  } catch (error) {
    return {
      status: "error",
      message: translateApiError(error, locale, {
        conflict: "Un matériel actif porte déjà ce nom.",
        invalid:
          "Vérifie les seuils : les deux doivent être renseignés ensemble, et le minimum doit rester inférieur au maximum.",
      }),
    };
  }

  revalidatePath("/equipment");
  return { status: "success" };
}

export async function updateEquipmentAction(
  _previous: EquipmentFormState,
  formData: FormData,
): Promise<EquipmentFormState> {
  const locale = await getLocale();
  const equipmentId = String(formData.get("id") ?? "").trim();
  if (!equipmentId) {
    return { status: "error", message: t(locale, "Matériel introuvable.") };
  }

  const result = buildPayload(formData, locale);
  if (!result.ok) {
    return { status: "error", message: result.error };
  }

  try {
    await apiFetch(`${EQUIPMENT_PATH}/${encodeURIComponent(equipmentId)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(result.payload),
    });
  } catch (error) {
    return {
      status: "error",
      message: translateApiError(error, locale, {
        conflict: "Un matériel actif porte déjà ce nom.",
        invalid:
          "Vérifie les seuils : les deux doivent être renseignés ensemble, et le minimum doit rester inférieur au maximum.",
      }),
    };
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
