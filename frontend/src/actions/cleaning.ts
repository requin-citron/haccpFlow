"use server";

import { revalidatePath } from "next/cache";

import { ApiError, apiFetch } from "@/lib/api";
import type { CleaningPlanFormState, CleaningRecordFormState } from "@/lib/form-state";

const PLANS_PATH = "/api/v1/cleaning-plans";
const FREQUENCIES = ["after_each_use", "daily", "weekly"];

function readOptionalText(formData: FormData, field: string): string | null {
  const value = String(formData.get(field) ?? "").trim();
  return value === "" ? null : value;
}

function describeError(error: unknown): string {
  if (error instanceof ApiError) {
    switch (error.status) {
      case 404:
        return "Ce plan de nettoyage n'existe plus.";
      case 409:
        return "Un plan actif porte déjà ce nom.";
      case 403:
        return "Cette action est réservée aux administrateurs.";
      case 422:
        return error.code === "cleaning_date_out_of_range"
          ? "Impossible de déclarer un nettoyage à plus d'un jour dans le futur."
          : "Vérifie les champs saisis, puis réessaie.";
      case 401:
        return "Ta session a expiré, reconnecte-toi.";
      default:
        return error.message;
    }
  }
  return "Une erreur inattendue est survenue.";
}

type PlanPayloadResult =
  | { ok: true; payload: Record<string, unknown> }
  | { ok: false; error: string };

function buildPlanPayload(formData: FormData): PlanPayloadResult {
  const name = String(formData.get("name") ?? "").trim();
  if (!name) {
    return { ok: false, error: "Le nom du plan est obligatoire." };
  }
  const frequency = String(formData.get("frequency") ?? "");
  if (!FREQUENCIES.includes(frequency)) {
    return { ok: false, error: "Choisis une fréquence de nettoyage." };
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
  const result = buildPlanPayload(formData);
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
    return { status: "error", message: describeError(error) };
  }

  revalidateCleaning();
  return { status: "success" };
}

export async function updateCleaningPlanAction(
  _previous: CleaningPlanFormState,
  formData: FormData,
): Promise<CleaningPlanFormState> {
  const planId = String(formData.get("id") ?? "").trim();
  if (!planId) {
    return { status: "error", message: "Plan introuvable." };
  }

  const result = buildPlanPayload(formData);
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
    return { status: "error", message: describeError(error) };
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
  const planId = String(formData.get("plan_id") ?? "").trim();
  const cleaningDate = String(formData.get("cleaning_date") ?? "").trim();
  if (!planId || !cleaningDate) {
    return { status: "error", message: "La date du nettoyage est obligatoire." };
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
    return { status: "error", message: describeError(error) };
  }

  revalidateCleaning(planId);
  return { status: "success" };
}

export async function updateCleaningRecordAction(
  _previous: CleaningRecordFormState,
  formData: FormData,
): Promise<CleaningRecordFormState> {
  const planId = String(formData.get("plan_id") ?? "").trim();
  const recordId = String(formData.get("record_id") ?? "").trim();
  const cleaningDate = String(formData.get("cleaning_date") ?? "").trim();
  if (!planId || !recordId || !cleaningDate) {
    return { status: "error", message: "Déclaration introuvable." };
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
    return { status: "error", message: describeError(error) };
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
