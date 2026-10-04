"use server";

import { revalidatePath } from "next/cache";

import { ApiError, apiFetch } from "@/lib/api";
import type { VehicleFormState } from "@/lib/form-state";

const VEHICLES_PATH = "/api/v1/vehicles";

function readOptionalText(formData: FormData, field: string): string | null {
  const value = String(formData.get(field) ?? "").trim();
  return value === "" ? null : value;
}

function describeError(error: unknown): string {
  if (error instanceof ApiError) {
    switch (error.status) {
      case 404:
        return "Ce véhicule n'existe plus.";
      case 409:
        return "Un véhicule actif utilise déjà ce nom ou cette plaque.";
      case 403:
        return "Cette action est réservée aux administrateurs.";
      case 422:
        return "Renseigne au moins un nom ou une plaque.";
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
  const name = readOptionalText(formData, "name");
  const plate = readOptionalText(formData, "plate");
  if (name === null && plate === null) {
    return { ok: false, error: "Renseigne au moins un nom ou une plaque." };
  }
  return { ok: true, payload: { name, plate } };
}

export async function createVehicleAction(
  _previous: VehicleFormState,
  formData: FormData,
): Promise<VehicleFormState> {
  const result = buildPayload(formData);
  if (!result.ok) {
    return { status: "error", message: result.error };
  }

  try {
    await apiFetch(VEHICLES_PATH, {
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

export async function updateVehicleAction(
  _previous: VehicleFormState,
  formData: FormData,
): Promise<VehicleFormState> {
  const vehicleId = String(formData.get("id") ?? "").trim();
  if (!vehicleId) {
    return { status: "error", message: "Véhicule introuvable." };
  }

  const result = buildPayload(formData);
  if (!result.ok) {
    return { status: "error", message: result.error };
  }

  try {
    await apiFetch(`${VEHICLES_PATH}/${encodeURIComponent(vehicleId)}`, {
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

export async function deleteVehicleAction(vehicleId: string): Promise<void> {
  try {
    await apiFetch(`${VEHICLES_PATH}/${encodeURIComponent(vehicleId)}`, { method: "DELETE" });
  } catch (error) {
    if (!(error instanceof ApiError && error.status === 404)) {
      throw error;
    }
  }
  revalidatePath("/equipment");
}
