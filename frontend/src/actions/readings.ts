"use server";

import { revalidatePath } from "next/cache";

import { ApiError, apiFetch } from "@/lib/api";
import type { ReadingFormState } from "@/lib/form-state";

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

function describeError(error: unknown): string {
  if (error instanceof ApiError) {
    switch (error.status) {
      case 404:
        return "Ce matériel n'existe plus.";
      case 422:
        return error.code === "reading_date_out_of_range"
          ? "Impossible de saisir un relevé à plus d'un jour dans le futur."
          : "Vérifie les valeurs saisies, puis réessaie.";
      case 401:
        return "Ta session a expiré, reconnecte-toi.";
      default:
        return error.message;
    }
  }
  return "Une erreur inattendue est survenue.";
}

export async function saveReadingAction(
  _previous: ReadingFormState,
  formData: FormData,
): Promise<ReadingFormState> {
  const equipmentId = String(formData.get("equipment_id") ?? "").trim();
  const readingDate = String(formData.get("reading_date") ?? "").trim();
  if (!equipmentId || !readingDate) {
    return { status: "error", message: "Relevé introuvable." };
  }

  // A slot left empty is not sent: the API keeps its current value.
  const morning = readOptionalNumber(formData, "morning_celsius");
  const evening = readOptionalNumber(formData, "evening_celsius");
  if (morning === null && evening === null) {
    return { status: "error", message: "Saisis au moins une température." };
  }

  const payload = {
    ...(morning !== null ? { morning_celsius: morning } : {}),
    ...(evening !== null ? { evening_celsius: evening } : {}),
  };

  try {
    await apiFetch(
      `/api/v1/equipment/${encodeURIComponent(equipmentId)}/readings/${encodeURIComponent(readingDate)}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      },
    );
  } catch (error) {
    return { status: "error", message: describeError(error) };
  }

  revalidatePath("/readings");
  revalidatePath(`/equipment/${equipmentId}`);
  return { status: "success" };
}
