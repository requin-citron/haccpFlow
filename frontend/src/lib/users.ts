import type { UserRole } from "@/lib/types";

export const USER_ROLE_LABELS: Record<UserRole, string> = {
  admin: "Administrateur",
  operator: "Opérateur",
};

export const USER_ROLE_BADGES: Record<UserRole, string> = {
  admin: "bg-indigo-50 text-indigo-700 ring-indigo-200",
  operator: "bg-sky-50 text-sky-700 ring-sky-200",
};

export const USER_STATUS_BADGES = {
  active: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  inactive: "bg-slate-100 text-slate-600 ring-slate-200",
} as const;
