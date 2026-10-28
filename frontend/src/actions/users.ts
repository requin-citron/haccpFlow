"use server";

import { revalidatePath } from "next/cache";

import { ApiError, apiFetch } from "@/lib/api";
import type { PasswordResetState, UserFormState } from "@/lib/form-state";
import type { CreatedUserAccount, UserAccount, UserRole } from "@/lib/types";

const USERS_PATH = "/api/v1/users";

function describeError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === "user_email_taken") {
      return "Un compte utilise déjà cet email.";
    }
    if (error.code === "user_last_admin") {
      return "Le dernier administrateur actif ne peut pas être retiré.";
    }
    if (error.code === "user_self_lockout") {
      return "Tu ne peux pas modifier tes propres droits ou désactiver ton compte.";
    }
    switch (error.status) {
      case 404:
        return "Ce compte n'existe plus.";
      case 403:
        return "Cette action est réservée aux administrateurs.";
      case 422:
        return "Vérifie l'email, le rôle et l'état du compte.";
      case 401:
        return "Ta session a expiré, reconnecte-toi.";
      default:
        return error.message;
    }
  }
  return "Une erreur inattendue est survenue.";
}

function readRole(formData: FormData): UserRole | null {
  const role = String(formData.get("role") ?? "");
  return role === "admin" || role === "operator" ? role : null;
}

export async function createUserAction(
  _previous: UserFormState,
  formData: FormData,
): Promise<UserFormState> {
  const email = String(formData.get("email") ?? "").trim();
  const role = readRole(formData);
  if (!email) {
    return { status: "error", message: "L'email est obligatoire." };
  }
  if (role === null) {
    return { status: "error", message: "Choisis un rôle valide." };
  }

  try {
    const created = await apiFetch<CreatedUserAccount>(USERS_PATH, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, role }),
    });
    const { temporary_password, ...user } = created;
    revalidatePath("/users");
    return {
      status: "success",
      user,
      temporaryPassword: temporary_password,
    };
  } catch (error) {
    return { status: "error", message: describeError(error) };
  }
}

export async function updateUserAction(
  _previous: UserFormState,
  formData: FormData,
): Promise<UserFormState> {
  const userId = String(formData.get("id") ?? "").trim();
  const role = readRole(formData);
  const activeValue = String(formData.get("is_active") ?? "");
  if (!userId) {
    return { status: "error", message: "Compte introuvable." };
  }
  if (role === null) {
    return { status: "error", message: "Choisis un rôle valide." };
  }
  if (activeValue !== "true" && activeValue !== "false") {
    return { status: "error", message: "Choisis un état de compte valide." };
  }

  try {
    const user = await apiFetch<UserAccount>(`${USERS_PATH}/${encodeURIComponent(userId)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        role,
        is_active: activeValue === "true",
      }),
    });
    revalidatePath("/users");
    return { status: "success", user };
  } catch (error) {
    return { status: "error", message: describeError(error) };
  }
}

export async function resetUserPasswordAction(userId: string): Promise<PasswordResetState> {
  try {
    const result = await apiFetch<{ temporary_password: string }>(
      `${USERS_PATH}/${encodeURIComponent(userId)}/reset-password`,
      { method: "POST" },
    );
    return {
      status: "success",
      temporaryPassword: result.temporary_password,
    };
  } catch (error) {
    return { status: "error", message: describeError(error) };
  }
}
