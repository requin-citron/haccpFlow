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
  label: string;
  adminOnly?: boolean;
};

export const MODULE_NAV_ITEMS: readonly ModuleNavItem[] = [
  { key: "equipment", href: "/equipment", label: "Matériel" },
  { key: "readings", href: "/readings", label: "Relevés" },
  { key: "cleaning", href: "/cleaning", label: "Nettoyage" },
  { key: "cleaning", href: "/cleaning/plans", label: "Plan de nettoyage" },
  { key: "pasteurisation", href: "/pasteurisation", label: "Pasteurisation" },
  { key: "transport", href: "/transport", label: "Transport" },
  { key: "cashSessions", href: "/cash-sessions", label: "Suivi de caisse" },
  { key: "export", href: "/export", label: "Export" },
  { key: "documents", href: "/templates", label: "Modèles LaTeX" },
  { key: "documents", href: "/documents", label: "Documents générés" },
  { key: "history", href: "/history", label: "Historique", adminOnly: true },
  { key: "users", href: "/users", label: "Utilisateurs", adminOnly: true },
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
