"use server";

import { revalidatePath } from "next/cache";

import { ApiError, apiFetch } from "@/lib/api";
import { translateApiError } from "@/lib/api-errors";
import type { PasteurisationFormState } from "@/lib/form-state";
import { t, type Locale } from "@/lib/i18n";
import { getLocale } from "@/lib/locale";

const BATCHES_PATH = "/api/v1/pasteurisations";

function readOptionalText(formData: FormData, field: string): string | null {
  const value = String(formData.get(field) ?? "").trim();
  return value === "" ? null : value;
}

type PayloadResult =
  | { ok: true; payload: Record<string, unknown> }
  | { ok: false; error: string };

function buildBatchPayload(formData: FormData, locale: Locale): PayloadResult {
  const batchDate = String(formData.get("batch_date") ?? "").trim();
  const productName = String(formData.get("product_name") ?? "").trim();
  const lotNumber = String(formData.get("lot_number") ?? "").trim();
  const quantity = Number(String(formData.get("quantity") ?? "").trim());

  if (!batchDate) {
    return { ok: false, error: t(locale, "La date du lot est obligatoire.") };
  }
  if (!productName) {
    return { ok: false, error: t(locale, "Le nom du produit est obligatoire.") };
  }
  if (!lotNumber) {
    return { ok: false, error: t(locale, "Le numéro de lot est obligatoire.") };
  }
  if (!Number.isInteger(quantity) || quantity < 1) {
    return { ok: false, error: t(locale, "Indique un nombre d'entités supérieur à zéro.") };
  }

  return {
    ok: true,
    payload: {
      batch_date: batchDate,
      product_name: productName,
      lot_number: lotNumber,
      quantity,
    },
  };
}

function revalidatePasteurisation(batchId?: string): void {
  revalidatePath("/pasteurisation");
  if (batchId) {
    revalidatePath(`/pasteurisation/${batchId}`);
  }
}

export async function createPasteurisationAction(
  _previous: PasteurisationFormState,
  formData: FormData,
): Promise<PasteurisationFormState> {
  const locale = await getLocale();
  const result = buildBatchPayload(formData, locale);
  if (!result.ok) {
    return { status: "error", message: result.error };
  }

  try {
    await apiFetch(BATCHES_PATH, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(result.payload),
    });
  } catch (error) {
    return {
      status: "error",
      message: translateApiError(error, locale, {
        notFound: "Ce lot de pasteurisation n'existe plus.",
      }),
    };
  }

  revalidatePasteurisation();
  return { status: "success" };
}

export async function updatePasteurisationAction(
  _previous: PasteurisationFormState,
  formData: FormData,
): Promise<PasteurisationFormState> {
  const locale = await getLocale();
  const batchId = String(formData.get("id") ?? "").trim();
  if (!batchId) {
    return { status: "error", message: t(locale, "Lot introuvable.") };
  }

  const result = buildBatchPayload(formData, locale);
  if (!result.ok) {
    return { status: "error", message: result.error };
  }

  try {
    await apiFetch(`${BATCHES_PATH}/${encodeURIComponent(batchId)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(result.payload),
    });
  } catch (error) {
    return {
      status: "error",
      message: translateApiError(error, locale, {
        notFound: "Ce lot de pasteurisation n'existe plus.",
      }),
    };
  }

  revalidatePasteurisation(batchId);
  return { status: "success" };
}

export async function deletePasteurisationAction(batchId: string): Promise<void> {
  try {
    await apiFetch(`${BATCHES_PATH}/${encodeURIComponent(batchId)}`, { method: "DELETE" });
  } catch (error) {
    if (!(error instanceof ApiError && error.status === 404)) {
      throw error;
    }
  }
  revalidatePasteurisation();
}

export async function savePasteurisationPhaseAction(
  _previous: PasteurisationFormState,
  formData: FormData,
): Promise<PasteurisationFormState> {
  const locale = await getLocale();
  const batchId = String(formData.get("batch_id") ?? "").trim();
  const phase = String(formData.get("phase") ?? "").trim();
  if (!batchId || !phase) {
    return { status: "error", message: t(locale, "Phase introuvable.") };
  }

  const target = readOptionalText(formData, "target_temperature_celsius");
  const temperature = target === null ? null : Number(target.replace(",", "."));
  if (temperature !== null && !Number.isFinite(temperature)) {
    return {
      status: "error",
      message: t(locale, "La température cible n'est pas un nombre valide."),
    };
  }

  // The form owns the whole phase: empty fields are sent as null and clear it.
  const payload = {
    started_at: readOptionalText(formData, "started_at"),
    ended_at: readOptionalText(formData, "ended_at"),
    target_temperature_celsius: temperature,
    observation: readOptionalText(formData, "observation"),
  };

  try {
    await apiFetch(
      `${BATCHES_PATH}/${encodeURIComponent(batchId)}/phases/${encodeURIComponent(phase)}`,
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
        notFound: "Ce lot de pasteurisation n'existe plus.",
      }),
    };
  }

  revalidatePasteurisation(batchId);
  return { status: "success" };
}
