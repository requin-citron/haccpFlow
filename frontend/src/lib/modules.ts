import type { MessageKey } from "@/lib/i18n";

export const MODULE_KEYS = [
  "dashboard",
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

export type ModuleNavItem = {
  key: ModuleKey;
  href: string;
  labelKey: MessageKey;
  adminOnly?: boolean;
};

export const MODULE_NAV_ITEMS: readonly ModuleNavItem[] = [
  { key: "dashboard", href: "/", labelKey: "Tableau de bord" },
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

export function visibleModuleNavItems(
  enabledModules: EnabledModules,
  isAdmin: boolean,
): readonly ModuleNavItem[] {
  return MODULE_NAV_ITEMS.filter(
    (item) => enabledModules[item.key] && (!item.adminOnly || isAdmin),
  );
}

export function activeModuleNavItem(
  items: readonly ModuleNavItem[],
  pathname: string,
): ModuleNavItem | undefined {
  return items
    .filter((item) => pathname === item.href || pathname.startsWith(`${item.href}/`))
    .sort((first, second) => second.href.length - first.href.length)[0];
}

export function firstEnabledModuleHref(
  enabledModules: EnabledModules,
  isAdmin: boolean,
): string | null {
  return visibleModuleNavItems(enabledModules, isAdmin)[0]?.href ?? null;
}

