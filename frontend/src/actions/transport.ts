"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { ApiError, apiFetch } from "@/lib/api";
import type { TransportFormState } from "@/lib/form-state";
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

function describeError(error: unknown): string {
  if (error instanceof ApiError) {
    switch (error.status) {
      case 404:
        return error.code === "vehicle_not_found"
          ? "Ce véhicule n'existe plus."
          : "Ce transport n'existe plus.";
      case 403:
        return "Cette action est réservée aux administrateurs.";
      case 422:
        return error.code === "transport_date_out_of_range"
          ? "Impossible d'enregistrer un transport à plus d'un jour dans le futur."
          : "Vérifie les valeurs saisies, puis réessaie.";
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

function buildHeaderPayload(formData: FormData): PayloadResult {
  const transportDate = String(formData.get("transport_date") ?? "").trim();
  const place = String(formData.get("place") ?? "").trim();
  const productName = String(formData.get("product_name") ?? "").trim();
  const choice = String(formData.get("vehicle_choice") ?? "").trim();
  const externalLabel = readOptionalText(formData, "vehicle_label");

  if (!transportDate) {
    return { ok: false, error: "La date du transport est obligatoire." };
  }
  if (!place) {
    return { ok: false, error: "Le lieu est obligatoire." };
  }
  if (!productName) {
    return { ok: false, error: "Le nom du produit est obligatoire." };
  }
  if (!choice) {
    return { ok: false, error: "Choisis un véhicule." };
  }
  if (choice === "external") {
    if (!externalLabel) {
      return { ok: false, error: "Précise le véhicule externe." };
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
  const result = buildHeaderPayload(formData);
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
    return { status: "error", message: describeError(error) };
  }

  revalidatePath("/transport");
  // Straight to the detail page: the departure is declared right away.
  redirect(`/transport/${created.id}`);
}

export async function updateTransportAction(
  _previous: TransportFormState,
  formData: FormData,
): Promise<TransportFormState> {
  const transportId = String(formData.get("id") ?? "").trim();
  if (!transportId) {
    return { status: "error", message: "Transport introuvable." };
  }

  const result = buildHeaderPayload(formData);
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
    return { status: "error", message: describeError(error) };
  }

  revalidatePath("/transport");
  revalidatePath(`/transport/${transportId}`);
  return { status: "success" };
}

export async function saveTransportReadingsAction(
  _previous: TransportFormState,
  formData: FormData,
): Promise<TransportFormState> {
  const transportId = String(formData.get("transport_id") ?? "").trim();
  if (!transportId) {
    return { status: "error", message: "Transport introuvable." };
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
    return { status: "error", message: "Rien à enregistrer." };
  }

  try {
    await apiFetch(`${TRANSPORTS_PATH}/${encodeURIComponent(transportId)}/readings`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (error) {
    return { status: "error", message: describeError(error) };
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
