"use server";

import { revalidatePath } from "next/cache";

import { ApiError, apiFetch } from "@/lib/api";
import { DENOMINATIONS } from "@/lib/cash-register";
import {
  draftTotals,
  eurosToCents,
  normalizeVatRate,
  type CountsDraft,
} from "@/lib/cash-session";
import { isIsoDate } from "@/lib/format";
import type { CashSessionFormState } from "@/lib/form-state";

const SESSIONS_PATH = "/api/v1/cash-sessions";

function describeError(error: unknown): string {
  if (error instanceof ApiError) {
    switch (error.code) {
      case "cash_session_already_open":
        return "Cette caisse a déjà un suivi ouvert : clôture-le avant d'en ouvrir un nouveau.";
      case "cash_session_closed":
        return "Ce suivi est clôturé : il ne peut plus être modifié.";
      case "cash_session_date_in_future":
        return "Impossible d'enregistrer un suivi à plus d'un jour dans le futur.";
      case "cash_register_has_open_session":
        return "Cette caisse a un suivi ouvert : clôture-le d'abord.";
      default:
        break;
    }
    switch (error.status) {
      case 404:
        return "Ce suivi de caisse n'existe plus.";
      case 403:
        return "Cette action est réservée aux administrateurs.";
      case 409:
        return error.message;
      case 422:
        return "Vérifie les valeurs saisies, puis réessaie.";
      case 401:
        return "Ta session a expiré, reconnecte-toi.";
      default:
        return error.message;
    }
  }
  return "Une erreur inattendue est survenue.";
}

type PayloadResult =
  | { ok: true; payload: Record<string, unknown> }
  | { ok: false; error: string };

function readCounts(formData: FormData): CountsDraft {
  return Object.fromEntries(
    DENOMINATIONS.map((denomination) => [
      denomination.field,
      String(formData.get(denomination.field) ?? ""),
    ]),
  );
}

function revalidateSessions(sessionId?: string): void {
  revalidatePath("/cash-sessions");
  if (sessionId) {
    revalidatePath(`/cash-sessions/${sessionId}`);
  }
}

function buildOpenPayload(formData: FormData): PayloadResult {
  const cashRegisterId = String(formData.get("cash_register_id") ?? "").trim();
  const sessionDate = String(formData.get("session_date") ?? "").trim();
  if (!cashRegisterId) {
    return { ok: false, error: "Choisis la caisse à suivre." };
  }
  if (!isIsoDate(sessionDate)) {
    return { ok: false, error: "La date du suivi est obligatoire." };
  }

  // The float is copied from the register unless the override is ticked.
  if (String(formData.get("override_opening") ?? "") !== "1") {
    return { ok: true, payload: { cash_register_id: cashRegisterId, session_date: sessionDate } };
  }
  return {
    ok: true,
    payload: {
      cash_register_id: cashRegisterId,
      session_date: sessionDate,
      opening_counts: draftTotals(readCounts(formData)),
    },
  };
}

export async function openCashSessionAction(
  _previous: CashSessionFormState,
  formData: FormData,
): Promise<CashSessionFormState> {
  const result = buildOpenPayload(formData);
  if (!result.ok) {
    return { status: "error", message: result.error };
  }

  try {
    await apiFetch(SESSIONS_PATH, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(result.payload),
    });
  } catch (error) {
    return { status: "error", message: describeError(error) };
  }

  revalidateSessions();
  return { status: "success" };
}

export async function updateCashSessionAction(
  _previous: CashSessionFormState,
  formData: FormData,
): Promise<CashSessionFormState> {
  const sessionId = String(formData.get("session_id") ?? "").trim();
  const sessionDate = String(formData.get("session_date") ?? "").trim();
  if (!sessionId) {
    return { status: "error", message: "Suivi introuvable." };
  }
  if (!isIsoDate(sessionDate)) {
    return { status: "error", message: "La date du suivi est obligatoire." };
  }

  try {
    await apiFetch(`${SESSIONS_PATH}/${encodeURIComponent(sessionId)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_date: sessionDate,
        opening_counts: draftTotals(readCounts(formData)),
      }),
    });
  } catch (error) {
    return { status: "error", message: describeError(error) };
  }

  revalidateSessions(sessionId);
  return { status: "success" };
}

export async function closeCashSessionAction(
  _previous: CashSessionFormState,
  formData: FormData,
): Promise<CashSessionFormState> {
  const sessionId = String(formData.get("session_id") ?? "").trim();
  if (!sessionId) {
    return { status: "error", message: "Suivi introuvable." };
  }

  try {
    await apiFetch(`${SESSIONS_PATH}/${encodeURIComponent(sessionId)}/close`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ closing_counts: draftTotals(readCounts(formData)) }),
    });
  } catch (error) {
    return { status: "error", message: describeError(error) };
  }

  revalidateSessions(sessionId);
  // Closing commits the count: the register cards on the Matériel page change.
  revalidatePath("/equipment");
  return { status: "success" };
}

function buildExpensePayload(formData: FormData): PayloadResult {
  const kind = String(formData.get("kind") ?? "").trim();
  const name = String(formData.get("name") ?? "").trim();
  const quantity = Number(String(formData.get("quantity") ?? "").trim());
  const unitPriceCents = eurosToCents(String(formData.get("unit_price") ?? ""));
  const vatRate = normalizeVatRate(String(formData.get("vat_rate") ?? ""));

  if (kind !== "professional" && kind !== "personal") {
    return { ok: false, error: "Choisis un type de frais." };
  }
  if (!name) {
    return { ok: false, error: "Le nom du frais est obligatoire." };
  }
  if (!Number.isInteger(quantity) || quantity < 1) {
    return { ok: false, error: "Indique une quantité supérieure ou égale à 1." };
  }
  if (unitPriceCents === null) {
    return { ok: false, error: "Le montant unitaire doit être un prix en euros." };
  }
  if (vatRate === null) {
    return { ok: false, error: "La TVA doit être un pourcentage entre 0 et 100." };
  }

  return {
    ok: true,
    payload: {
      kind,
      name,
      quantity,
      unit_price_cents: unitPriceCents,
      vat_rate: vatRate,
    },
  };
}

export async function createCashExpenseAction(
  _previous: CashSessionFormState,
  formData: FormData,
): Promise<CashSessionFormState> {
  const sessionId = String(formData.get("session_id") ?? "").trim();
  if (!sessionId) {
    return { status: "error", message: "Suivi introuvable." };
  }

  const result = buildExpensePayload(formData);
  if (!result.ok) {
    return { status: "error", message: result.error };
  }

  try {
    await apiFetch(`${SESSIONS_PATH}/${encodeURIComponent(sessionId)}/expenses`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(result.payload),
    });
  } catch (error) {
    return { status: "error", message: describeError(error) };
  }

  revalidateSessions(sessionId);
  return { status: "success" };
}

export async function updateCashExpenseAction(
  _previous: CashSessionFormState,
  formData: FormData,
): Promise<CashSessionFormState> {
  const sessionId = String(formData.get("session_id") ?? "").trim();
  const expenseId = String(formData.get("expense_id") ?? "").trim();
  if (!sessionId || !expenseId) {
    return { status: "error", message: "Frais introuvable." };
  }

  const result = buildExpensePayload(formData);
  if (!result.ok) {
    return { status: "error", message: result.error };
  }

  try {
    await apiFetch(
      `${SESSIONS_PATH}/${encodeURIComponent(sessionId)}/expenses/${encodeURIComponent(expenseId)}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(result.payload),
      },
    );
  } catch (error) {
    return { status: "error", message: describeError(error) };
  }

  revalidateSessions(sessionId);
  return { status: "success" };
}

export async function deleteCashExpenseAction(
  sessionId: string,
  expenseId: string,
): Promise<void> {
  try {
    await apiFetch(
      `${SESSIONS_PATH}/${encodeURIComponent(sessionId)}/expenses/${encodeURIComponent(expenseId)}`,
      { method: "DELETE" },
    );
  } catch (error) {
    if (!(error instanceof ApiError && error.status === 404)) {
      throw error;
    }
  }
  revalidateSessions(sessionId);
}

export async function deleteCashSessionAction(sessionId: string): Promise<void> {
  try {
    await apiFetch(`${SESSIONS_PATH}/${encodeURIComponent(sessionId)}`, { method: "DELETE" });
  } catch (error) {
    if (!(error instanceof ApiError && error.status === 404)) {
      throw error;
    }
  }
  revalidateSessions(sessionId);
}
