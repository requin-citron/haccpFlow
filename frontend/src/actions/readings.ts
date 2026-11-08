"use server";

import { revalidatePath } from "next/cache";

import { ApiError, apiFetch } from "@/lib/api";
import { translateApiError } from "@/lib/api-errors";
import type { ReadingFormState } from "@/lib/form-state";
import { t } from "@/lib/i18n";
import { getLocale } from "@/lib/locale";

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

export async function saveReadingAction(
  _previous: ReadingFormState,
  formData: FormData,
): Promise<ReadingFormState> {
  const locale = await getLocale();
  const equipmentId = String(formData.get("equipment_id") ?? "").trim();
  const readingDate = String(formData.get("reading_date") ?? "").trim();
  if (!equipmentId || !readingDate) {
    return { status: "error", message: t(locale, "Relevé introuvable.") };
  }

  // A slot left empty is not sent: the API keeps its current value.
  const morning = readOptionalNumber(formData, "morning_celsius");
  const evening = readOptionalNumber(formData, "evening_celsius");
  if (morning === null && evening === null) {
    return { status: "error", message: t(locale, "Saisis au moins une température.") };
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
    return {
      status: "error",
      message: translateApiError(error, locale, {
        notFound: "Ce matériel n'existe plus.",
      }),
    };
  }

  revalidatePath("/readings");
  revalidatePath(`/equipment/${equipmentId}`);
  return { status: "success" };
}
