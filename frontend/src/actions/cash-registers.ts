"use server";

import { revalidatePath } from "next/cache";

import { ApiError, apiFetch } from "@/lib/api";
import { translateApiError } from "@/lib/api-errors";
import { DENOMINATIONS } from "@/lib/cash-register";
import type { CashRegisterFormState } from "@/lib/form-state";
import { t, type Locale } from "@/lib/i18n";
import { getLocale } from "@/lib/locale";

const CASH_REGISTERS_PATH = "/api/v1/cash-registers";

function readCount(formData: FormData, field: string): number | null {
  const value = String(formData.get(field) ?? "").trim();
  if (value === "") {
    return 0;
  }
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed >= 0 ? parsed : null;
}

type PayloadResult =
  | { ok: true; payload: Record<string, unknown> }
  | { ok: false; error: string };

function buildPayload(formData: FormData, locale: Locale): PayloadResult {
  const name = String(formData.get("name") ?? "").trim();
  if (!name) {
    return { ok: false, error: t(locale, "Le nom de la caisse est obligatoire.") };
  }

  const counts: Record<string, number> = {};
  for (const denomination of DENOMINATIONS) {
    const count = readCount(formData, denomination.field);
    if (count === null) {
      return {
        ok: false,
        error: t(locale, "Le compteur « {name} » doit être un entier positif.", {
          name: denomination.label,
        }),
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
  const locale = await getLocale();
  const result = buildPayload(formData, locale);
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
    return {
      status: "error",
      message: translateApiError(error, locale, {
        notFound: "Cette caisse n'existe plus.",
        conflict: "Une caisse active porte déjà ce nom.",
        invalid: "Vérifie les compteurs : ils doivent être des nombres entiers positifs.",
      }),
    };
  }

  revalidatePath("/equipment");
  return { status: "success" };
}

export async function updateCashRegisterAction(
  _previous: CashRegisterFormState,
  formData: FormData,
): Promise<CashRegisterFormState> {
  const locale = await getLocale();
  const cashRegisterId = String(formData.get("id") ?? "").trim();
  if (!cashRegisterId) {
    return { status: "error", message: t(locale, "Caisse introuvable.") };
  }

  const result = buildPayload(formData, locale);
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
    return {
      status: "error",
      message: translateApiError(error, locale, {
        notFound: "Cette caisse n'existe plus.",
        conflict: "Une caisse active porte déjà ce nom.",
        invalid: "Vérifie les compteurs : ils doivent être des nombres entiers positifs.",
      }),
    };
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
