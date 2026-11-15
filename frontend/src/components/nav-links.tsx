"use client";

import Link from "next/link";
import type { ComponentType, SVGProps } from "react";

import {
  BanknoteIcon,
  CheckIcon,
  ClipboardIcon,
  DropletIcon,
  DownloadIcon,
  FileDownIcon,
  FileTextIcon,
  FlameIcon,
  GridIcon,
  HistoryIcon,
  TruckIcon,
  UsersIcon,
} from "@/components/icons";
import { useI18n } from "@/components/locale-provider";
import type { ModuleNavItem } from "@/lib/modules";

type IconComponent = ComponentType<SVGProps<SVGSVGElement>>;

const NAV_ICONS: Record<string, IconComponent> = {
  "/equipment": GridIcon,
  "/readings": ClipboardIcon,
  "/cleaning": CheckIcon,
  "/cleaning/plans": DropletIcon,
  "/pasteurisation": FlameIcon,
  "/transport": TruckIcon,
  "/cash-sessions": BanknoteIcon,
  "/export": DownloadIcon,
  "/templates": FileTextIcon,
  "/documents": FileDownIcon,
  "/history": HistoryIcon,
  "/users": UsersIcon,
};

export type NavVariant = "sidebar" | "drawer";

export function NavLinks({
  items,
  activeHref,
  variant,
  showLabels,
  onNavigate,
}: {
  items: readonly ModuleNavItem[];
  activeHref: string | undefined;
  variant: NavVariant;
  showLabels: boolean;
  onNavigate?: () => void;
}) {
  const { t } = useI18n();

  return (
    <nav
      aria-label={t("Navigation principale")}
      className={variant === "drawer" ? "space-y-1.5" : "space-y-1"}
    >
      {items.map((item) => {
        const Icon = NAV_ICONS[item.href] ?? GridIcon;
        const active = item.href === activeHref;

        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            title={!showLabels ? t(item.labelKey) : undefined}
            aria-current={active ? "page" : undefined}
            aria-label={!showLabels ? t(item.labelKey) : undefined}
            className={`flex min-h-11 items-center rounded-xl text-sm font-medium transition ${
              showLabels ? "gap-3 px-3 py-2.5" : "justify-center px-2 py-2.5"
            } ${
              active
                ? "bg-teal-500/15 text-teal-200 ring-1 ring-inset ring-teal-400/25"
                : "text-slate-300 hover:bg-slate-800 hover:text-white"
            }`}
          >
            <Icon className="size-5 shrink-0" />
            {showLabels ? <span className="truncate">{t(item.labelKey)}</span> : null}
          </Link>
        );
      })}
    </nav>
  );
}
