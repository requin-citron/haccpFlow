"use server";

import { redirect } from "next/navigation";

import { signIn, signOut } from "@/lib/api";
import type { LoginState } from "@/lib/form-state";
import { t } from "@/lib/i18n";
import { getLocale } from "@/lib/locale";
import { clearSession, getSession, persistSession } from "@/lib/session";

export async function loginAction(_previous: LoginState, formData: FormData): Promise<LoginState> {
  const locale = await getLocale();
  const email = String(formData.get("email") ?? "").trim();
  const password = String(formData.get("password") ?? "");

  if (!email || !password) {
    return { error: t(locale, "Renseigne ton email et ton mot de passe.") };
  }

  const session = await signIn(email, password);
  if (!session) {
    return { error: t(locale, "Email ou mot de passe incorrect.") };
  }

  await persistSession(session);
  redirect("/");
}

export async function logoutAction(): Promise<void> {
  const session = await getSession();
  if (session) {
    await signOut(session);
  }
  await clearSession();
  redirect("/login");
}
