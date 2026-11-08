"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { ApiError, apiFetch } from "@/lib/api";
import { translateApiError } from "@/lib/api-errors";
import type { TransportFormState } from "@/lib/form-state";
import { t, type Locale } from "@/lib/i18n";
import { getLocale } from "@/lib/locale";
import type { Transport } from "@/lib/types";

const TRANSPORTS_PATH = "/api/v1/transports";

const READING_FIELDS = [
  "departure_time",
  "departure_temperature_celsius",
  "arrival_time",
  "arrival_temperature_celsius",
  "observation",
] as const;

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

type PayloadResult =
  | { ok: true; payload: Record<string, unknown> }
  | { ok: false; error: string };

function buildHeaderPayload(formData: FormData, locale: Locale): PayloadResult {
  const transportDate = String(formData.get("transport_date") ?? "").trim();
  const place = String(formData.get("place") ?? "").trim();
  const productName = String(formData.get("product_name") ?? "").trim();
  const choice = String(formData.get("vehicle_choice") ?? "").trim();
  const externalLabel = readOptionalText(formData, "vehicle_label");

  if (!transportDate) {
    return { ok: false, error: t(locale, "La date du transport est obligatoire.") };
  }
  if (!place) {
    return { ok: false, error: t(locale, "Le lieu est obligatoire.") };
  }
  if (!productName) {
    return { ok: false, error: t(locale, "Le nom du produit est obligatoire.") };
  }
  if (!choice) {
    return { ok: false, error: t(locale, "Choisis un véhicule.") };
  }
  if (choice === "external") {
    if (!externalLabel) {
      return { ok: false, error: t(locale, "Précise le véhicule externe.") };
    }
    return {
      ok: true,
      payload: {
        transport_date: transportDate,
        place,
        product_name: productName,
        lot_number: readOptionalText(formData, "lot_number"),
        vehicle_id: null,
        vehicle_label: externalLabel,
      },
    };
  }

  return {
    ok: true,
    payload: {
      transport_date: transportDate,
      place,
      product_name: productName,
      lot_number: readOptionalText(formData, "lot_number"),
      vehicle_id: choice,
      vehicle_label: null,
    },
  };
}

export async function createTransportAction(
  _previous: TransportFormState,
  formData: FormData,
): Promise<TransportFormState> {
  const locale = await getLocale();
  const result = buildHeaderPayload(formData, locale);
  if (!result.ok) {
    return { status: "error", message: result.error };
  }

  let created: Transport;
  try {
    created = await apiFetch<Transport>(TRANSPORTS_PATH, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(result.payload),
    });
  } catch (error) {
    return {
      status: "error",
      message: translateApiError(error, locale, {
        notFound: "Ce transport n'existe plus.",
      }),
    };
  }

  revalidatePath("/transport");
  // Straight to the detail page: the departure is declared right away.
  redirect(`/transport/${created.id}`);
}

export async function updateTransportAction(
  _previous: TransportFormState,
  formData: FormData,
): Promise<TransportFormState> {
  const locale = await getLocale();
  const transportId = String(formData.get("id") ?? "").trim();
  if (!transportId) {
    return { status: "error", message: t(locale, "Transport introuvable.") };
  }

  const result = buildHeaderPayload(formData, locale);
  if (!result.ok) {
    return { status: "error", message: result.error };
  }

  try {
    await apiFetch(`${TRANSPORTS_PATH}/${encodeURIComponent(transportId)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(result.payload),
    });
  } catch (error) {
    return {
      status: "error",
      message: translateApiError(error, locale, {
        notFound: "Ce transport n'existe plus.",
      }),
    };
  }

  revalidatePath("/transport");
  revalidatePath(`/transport/${transportId}`);
  return { status: "success" };
}

export async function saveTransportReadingsAction(
  _previous: TransportFormState,
  formData: FormData,
): Promise<TransportFormState> {
  const locale = await getLocale();
  const transportId = String(formData.get("transport_id") ?? "").trim();
  if (!transportId) {
    return { status: "error", message: t(locale, "Transport introuvable.") };
  }

  // Only the fields rendered by the form are sent: the API keeps the others.
  const payload: Record<string, unknown> = {};
  for (const field of READING_FIELDS) {
    if (!formData.has(field)) {
      continue;
    }
    payload[field] = field.endsWith("_temperature_celsius")
      ? readOptionalNumber(formData, field)
      : readOptionalText(formData, field);
  }
  if (Object.keys(payload).length === 0) {
    return { status: "error", message: t(locale, "Rien à enregistrer.") };
  }

  try {
    await apiFetch(`${TRANSPORTS_PATH}/${encodeURIComponent(transportId)}/readings`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (error) {
    return {
      status: "error",
      message: translateApiError(error, locale, {
        notFound: "Ce transport n'existe plus.",
      }),
    };
  }

  revalidatePath("/transport");
  revalidatePath(`/transport/${transportId}`);
  return { status: "success" };
}

export async function deleteTransportAction(transportId: string): Promise<void> {
  try {
    await apiFetch(`${TRANSPORTS_PATH}/${encodeURIComponent(transportId)}`, {
      method: "DELETE",
    });
  } catch (error) {
    if (!(error instanceof ApiError && error.status === 404)) {
      throw error;
    }
  }
  revalidatePath("/transport");
  redirect("/transport");
}
