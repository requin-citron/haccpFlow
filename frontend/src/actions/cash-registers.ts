"use server";

import { revalidatePath } from "next/cache";

import { ApiError, apiFetch } from "@/lib/api";
import { DENOMINATIONS } from "@/lib/cash-register";
import type { CashRegisterFormState } from "@/lib/form-state";

const CASH_REGISTERS_PATH = "/api/v1/cash-registers";

function readCount(formData: FormData, field: string): number | null {
  const value = String(formData.get(field) ?? "").trim();
  if (value === "") {
    return 0;
  }
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed >= 0 ? parsed : null;
}

function describeError(error: unknown): string {
  if (error instanceof ApiError) {
    switch (error.status) {
      case 404:
        return "Cette caisse n'existe plus.";
      case 409:
        return "Une caisse active porte déjà ce nom.";
      case 403:
        return "Cette action est réservée aux administrateurs.";
      case 422:
        return "Vérifie les compteurs : ils doivent être des nombres entiers positifs.";
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

function buildPayload(formData: FormData): PayloadResult {
  const name = String(formData.get("name") ?? "").trim();
  if (!name) {
    return { ok: false, error: "Le nom de la caisse est obligatoire." };
  }

  const counts: Record<string, number> = {};
  for (const denomination of DENOMINATIONS) {
    const count = readCount(formData, denomination.field);
    if (count === null) {
      return {
        ok: false,
        error: `Le compteur « ${denomination.label} » doit être un entier positif.`,
      };
    }
    counts[denomination.field] = count;
  }

  return { ok: true, payload: { name, ...counts } };
}

export async function createCashRegisterAction(
  _previous: CashRegisterFormState,
  formData: FormData,
): Promise<CashRegisterFormState> {
  const result = buildPayload(formData);
  if (!result.ok) {
    return { status: "error", message: result.error };
  }

  try {
    await apiFetch(CASH_REGISTERS_PATH, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(result.payload),
    });
  } catch (error) {
    return { status: "error", message: describeError(error) };
  }

  revalidatePath("/equipment");
  return { status: "success" };
}

export async function updateCashRegisterAction(
  _previous: CashRegisterFormState,
  formData: FormData,
): Promise<CashRegisterFormState> {
  const cashRegisterId = String(formData.get("id") ?? "").trim();
  if (!cashRegisterId) {
    return { status: "error", message: "Caisse introuvable." };
  }

  const result = buildPayload(formData);
  if (!result.ok) {
    return { status: "error", message: result.error };
  }

  try {
    await apiFetch(`${CASH_REGISTERS_PATH}/${encodeURIComponent(cashRegisterId)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(result.payload),
    });
  } catch (error) {
    return { status: "error", message: describeError(error) };
  }

  revalidatePath("/equipment");
  return { status: "success" };
}

export async function deleteCashRegisterAction(cashRegisterId: string): Promise<void> {
  try {
    await apiFetch(`${CASH_REGISTERS_PATH}/${encodeURIComponent(cashRegisterId)}`, {
      method: "DELETE",
    });
  } catch (error) {
    if (!(error instanceof ApiError && error.status === 404)) {
      throw error;
    }
  }
  revalidatePath("/equipment");
}
