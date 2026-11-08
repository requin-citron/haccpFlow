"use server";

import { revalidatePath } from "next/cache";

import { ApiError, apiFetch } from "@/lib/api";
import { translateApiError } from "@/lib/api-errors";
import type { CleaningPlanFormState, CleaningRecordFormState } from "@/lib/form-state";
import { t, type Locale } from "@/lib/i18n";
import { getLocale } from "@/lib/locale";

const PLANS_PATH = "/api/v1/cleaning-plans";
const FREQUENCIES = ["after_each_use", "daily", "weekly"];

function readOptionalText(formData: FormData, field: string): string | null {
  const value = String(formData.get(field) ?? "").trim();
  return value === "" ? null : value;
}

type PlanPayloadResult =
  | { ok: true; payload: Record<string, unknown> }
  | { ok: false; error: string };

function buildPlanPayload(formData: FormData, locale: Locale): PlanPayloadResult {
  const name = String(formData.get("name") ?? "").trim();
  if (!name) {
    return { ok: false, error: t(locale, "Le nom du plan est obligatoire.") };
  }
  const frequency = String(formData.get("frequency") ?? "");
  if (!FREQUENCIES.includes(frequency)) {
    return { ok: false, error: t(locale, "Choisis une fréquence de nettoyage.") };
  }
  return {
    ok: true,
    payload: {
      name,
      frequency,
      products: readOptionalText(formData, "products"),
    },
  };
}

function revalidateCleaning(planId?: string): void {
  revalidatePath("/cleaning");
  if (planId) {
    revalidatePath(`/cleaning/${planId}`);
  }
}

export async function createCleaningPlanAction(
  _previous: CleaningPlanFormState,
  formData: FormData,
): Promise<CleaningPlanFormState> {
  const locale = await getLocale();
  const result = buildPlanPayload(formData, locale);
  if (!result.ok) {
    return { status: "error", message: result.error };
  }

  try {
    await apiFetch(PLANS_PATH, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(result.payload),
    });
  } catch (error) {
    return {
      status: "error",
      message: translateApiError(error, locale, {
        notFound: "Ce plan de nettoyage n'existe plus.",
        conflict: "Un plan actif porte déjà ce nom.",
        invalid: "Vérifie les champs saisis, puis réessaie.",
      }),
    };
  }

  revalidateCleaning();
  return { status: "success" };
}

export async function updateCleaningPlanAction(
  _previous: CleaningPlanFormState,
  formData: FormData,
): Promise<CleaningPlanFormState> {
  const locale = await getLocale();
  const planId = String(formData.get("id") ?? "").trim();
  if (!planId) {
    return { status: "error", message: t(locale, "Plan introuvable.") };
  }

  const result = buildPlanPayload(formData, locale);
  if (!result.ok) {
    return { status: "error", message: result.error };
  }

  try {
    await apiFetch(`${PLANS_PATH}/${encodeURIComponent(planId)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(result.payload),
    });
  } catch (error) {
    return {
      status: "error",
      message: translateApiError(error, locale, {
        notFound: "Ce plan de nettoyage n'existe plus.",
        conflict: "Un plan actif porte déjà ce nom.",
        invalid: "Vérifie les champs saisis, puis réessaie.",
      }),
    };
  }

  revalidateCleaning(planId);
  return { status: "success" };
}

export async function deleteCleaningPlanAction(planId: string): Promise<void> {
  try {
    await apiFetch(`${PLANS_PATH}/${encodeURIComponent(planId)}`, { method: "DELETE" });
  } catch (error) {
    if (!(error instanceof ApiError && error.status === 404)) {
      throw error;
    }
  }
  revalidateCleaning();
}

export async function declareCleaningAction(
  _previous: CleaningRecordFormState,
  formData: FormData,
): Promise<CleaningRecordFormState> {
  const locale = await getLocale();
  const planId = String(formData.get("plan_id") ?? "").trim();
  const cleaningDate = String(formData.get("cleaning_date") ?? "").trim();
  if (!planId || !cleaningDate) {
    return { status: "error", message: t(locale, "La date du nettoyage est obligatoire.") };
  }

  try {
    await apiFetch(`${PLANS_PATH}/${encodeURIComponent(planId)}/records`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        cleaning_date: cleaningDate,
        comment: readOptionalText(formData, "comment"),
      }),
    });
  } catch (error) {
    return {
      status: "error",
      message: translateApiError(error, locale, {
        notFound: "Ce plan de nettoyage n'existe plus.",
        invalid: "Vérifie les champs saisis, puis réessaie.",
      }),
    };
  }

  revalidateCleaning(planId);
  return { status: "success" };
}

export async function updateCleaningRecordAction(
  _previous: CleaningRecordFormState,
  formData: FormData,
): Promise<CleaningRecordFormState> {
  const locale = await getLocale();
  const planId = String(formData.get("plan_id") ?? "").trim();
  const recordId = String(formData.get("record_id") ?? "").trim();
  const cleaningDate = String(formData.get("cleaning_date") ?? "").trim();
  if (!planId || !recordId || !cleaningDate) {
    return { status: "error", message: t(locale, "Déclaration introuvable.") };
  }

  try {
    await apiFetch(
      `${PLANS_PATH}/${encodeURIComponent(planId)}/records/${encodeURIComponent(recordId)}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          cleaning_date: cleaningDate,
          comment: readOptionalText(formData, "comment"),
        }),
      },
    );
  } catch (error) {
    return {
      status: "error",
      message: translateApiError(error, locale, {
        notFound: "Déclaration introuvable.",
        invalid: "Vérifie les champs saisis, puis réessaie.",
      }),
    };
  }

  revalidateCleaning(planId);
  return { status: "success" };
}

export async function deleteCleaningRecordAction(
  planId: string,
  recordId: string,
): Promise<void> {
  try {
    await apiFetch(
      `${PLANS_PATH}/${encodeURIComponent(planId)}/records/${encodeURIComponent(recordId)}`,
      { method: "DELETE" },
    );
  } catch (error) {
    if (!(error instanceof ApiError && error.status === 404)) {
      throw error;
    }
  }
  revalidateCleaning(planId);
}
