import type { MessageKey } from "@/lib/i18n";

export const MODULE_KEYS = [
  "equipment",
  "readings",
  "cleaning",
  "pasteurisation",
  "transport",
  "cashSessions",
  "export",
  "documents",
  "history",
  "users",
] as const;

export type ModuleKey = (typeof MODULE_KEYS)[number];

export type EnabledModules = Record<ModuleKey, boolean>;

type ModuleNavItem = {
  key: ModuleKey;
  href: string;
  labelKey: MessageKey;
  adminOnly?: boolean;
};

export const MODULE_NAV_ITEMS: readonly ModuleNavItem[] = [
  { key: "equipment", href: "/equipment", labelKey: "Matériel" },
  { key: "readings", href: "/readings", labelKey: "Relevés" },
  { key: "cleaning", href: "/cleaning", labelKey: "Nettoyage" },
  { key: "cleaning", href: "/cleaning/plans", labelKey: "Plan de nettoyage" },
  { key: "pasteurisation", href: "/pasteurisation", labelKey: "Pasteurisation" },
  { key: "transport", href: "/transport", labelKey: "Transport" },
  { key: "cashSessions", href: "/cash-sessions", labelKey: "Suivi de caisse" },
  { key: "export", href: "/export", labelKey: "Export" },
  { key: "documents", href: "/templates", labelKey: "Modèles LaTeX" },
  { key: "documents", href: "/documents", labelKey: "Documents générés" },
  { key: "history", href: "/history", labelKey: "Historique", adminOnly: true },
  { key: "users", href: "/users", labelKey: "Utilisateurs", adminOnly: true },
];

export function firstEnabledModuleHref(
  enabledModules: EnabledModules,
  isAdmin: boolean,
): string | null {
  return (
    MODULE_NAV_ITEMS.find(
      (item) => enabledModules[item.key] && (!item.adminOnly || isAdmin),
    )?.href ?? null
  );
}

