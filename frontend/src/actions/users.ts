"use server";

import { revalidatePath } from "next/cache";

import { ApiError, apiFetch } from "@/lib/api";
import { translateApiError } from "@/lib/api-errors";
import type { DeleteUserState, PasswordResetState, UserFormState } from "@/lib/form-state";
import { t } from "@/lib/i18n";
import { getLocale } from "@/lib/locale";
import type { CreatedUserAccount, UserAccount, UserRole } from "@/lib/types";

const USERS_PATH = "/api/v1/users";

function readRole(formData: FormData): UserRole | null {
  const role = String(formData.get("role") ?? "");
  return role === "admin" || role === "operator" ? role : null;
}

export async function createUserAction(
  _previous: UserFormState,
  formData: FormData,
): Promise<UserFormState> {
  const locale = await getLocale();
  const email = String(formData.get("email") ?? "").trim();
  const role = readRole(formData);
  if (!email) {
    return { status: "error", message: t(locale, "L'email est obligatoire.") };
  }
  if (role === null) {
    return { status: "error", message: t(locale, "Choisis un rôle valide.") };
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
    return {
      status: "error",
      message: translateApiError(error, locale, {
        notFound: "Ce compte n'existe plus.",
        conflict: "Un compte utilise déjà cet email.",
        invalid: "Vérifie l'email, le rôle et l'état du compte.",
      }),
    };
  }
}

export async function updateUserAction(
  _previous: UserFormState,
  formData: FormData,
): Promise<UserFormState> {
  const locale = await getLocale();
  const userId = String(formData.get("id") ?? "").trim();
  const role = readRole(formData);
  const activeValue = String(formData.get("is_active") ?? "");
  if (!userId) {
    return { status: "error", message: t(locale, "Compte introuvable.") };
  }
  if (role === null) {
    return { status: "error", message: t(locale, "Choisis un rôle valide.") };
  }
  if (activeValue !== "true" && activeValue !== "false") {
    return { status: "error", message: t(locale, "Choisis un état de compte valide.") };
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
    return {
      status: "error",
      message: translateApiError(error, locale, {
        notFound: "Ce compte n'existe plus.",
        conflict: "Un compte utilise déjà cet email.",
        invalid: "Vérifie l'email, le rôle et l'état du compte.",
      }),
    };
  }
}

export async function resetUserPasswordAction(userId: string): Promise<PasswordResetState> {
  const locale = await getLocale();
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
    return {
      status: "error",
      message: translateApiError(error, locale, {
        notFound: "Ce compte n'existe plus.",
      }),
    };
  }
}

export async function deleteUserAction(userId: string): Promise<DeleteUserState> {
  const locale = await getLocale();
  if (!userId) {
    return { status: "error", message: t(locale, "Compte introuvable.") };
  }

  try {
    await apiFetch<void>(`${USERS_PATH}/${encodeURIComponent(userId)}`, {
      method: "DELETE",
    });
    revalidatePath("/users");
    return { status: "success" };
  } catch (error) {
    return {
      status: "error",
      message: translateApiError(error, locale, {
        notFound: "Ce compte n'existe plus.",
      }),
    };
  }
}
