import type { UserRole } from "@/lib/types";
import { t, type Locale } from "@/lib/i18n";

export function userRoleLabel(locale: Locale, role: UserRole): string {
  return t(locale, role === "admin" ? "Administrateur" : "Opérateur");
}

export const USER_ROLE_BADGES: Record<UserRole, string> = {
  admin: "bg-indigo-50 text-indigo-700 ring-indigo-200",
  operator: "bg-sky-50 text-sky-700 ring-sky-200",
};

export const USER_STATUS_BADGES = {
  active: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  inactive: "bg-slate-100 text-slate-600 ring-slate-200",
} as const;
