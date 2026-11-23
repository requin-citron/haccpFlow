"use server";

import { revalidatePath } from "next/cache";

import { ApiError, apiFetch } from "@/lib/api";
import { translateApiError } from "@/lib/api-errors";
import type { ReadingFormState } from "@/lib/form-state";
import { t } from "@/lib/i18n";
import { getLocale } from "@/lib/locale";
import {
  parseTemperatureInput,
  type ParsedTemperature,
  type TemperatureField,
} from "@/lib/readings";

function readTemperature(formData: FormData, field: TemperatureField): ParsedTemperature {
  return parseTemperatureInput(String(formData.get(`${field}_celsius`) ?? ""));
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

  const morning = readTemperature(formData, "morning");
  const evening = readTemperature(formData, "evening");
  const fieldErrors: NonNullable<ReadingFormState["fieldErrors"]> = {};
  if (morning.kind === "invalid") {
    fieldErrors.morning = t(locale, "Saisis une température valide.");
  }
  if (evening.kind === "invalid") {
    fieldErrors.evening = t(locale, "Saisis une température valide.");
  }
  if (Object.keys(fieldErrors).length > 0) {
    return { status: "error", message: t(locale, "Vérifie les températures saisies."), fieldErrors };
  }

  // A slot left empty is not sent: the API keeps its current value.
  if (morning.kind === "empty" && evening.kind === "empty") {
    return { status: "error", message: t(locale, "Saisis au moins une température.") };
  }

  const payload = {
    ...(morning.kind === "valid" ? { morning_celsius: morning.value } : {}),
    ...(evening.kind === "valid" ? { evening_celsius: evening.value } : {}),
  };
  const morningJustification = String(formData.get("morning_justification") ?? "").trim();
  const eveningJustification = String(formData.get("evening_justification") ?? "").trim();
  if (morningJustification) {
    Object.assign(payload, { morning_justification: morningJustification });
  }
  if (eveningJustification) {
    Object.assign(payload, { evening_justification: eveningJustification });
  }

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
    if (error instanceof ApiError && error.code === "reading_justification_required") {
      const slot = error.context?.slot;
      const message = translateApiError(error, locale);
      return {
        status: "error",
        message,
        fieldErrors:
          slot === "morning"
            ? { morning: message }
            : slot === "evening"
              ? { evening: message }
              : undefined,
      };
    }
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
