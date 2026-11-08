"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
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
import { MODULE_NAV_ITEMS, type EnabledModules } from "@/lib/modules";

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

export function NavLinks({
  isAdmin,
  enabledModules,
}: {
  isAdmin: boolean;
  enabledModules: EnabledModules;
}) {
  const pathname = usePathname();
  const items = MODULE_NAV_ITEMS.filter(
    (item) => enabledModules[item.key] && (!item.adminOnly || isAdmin),
  );
  // Longest matching href wins, so /cleaning/plans does not also light up
  // the /cleaning entry.
  const activeHref = items.filter(
    (item) => pathname === item.href || pathname.startsWith(`${item.href}/`),
  ).sort((first, second) => second.href.length - first.href.length)[0]?.href;

  return (
    <nav aria-label="Navigation principale" className="space-y-1">
      {items.map((item) => {
        const Icon = NAV_ICONS[item.href] ?? GridIcon;
        const active = item.href === activeHref;

        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? "page" : undefined}
            className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
              active
                ? "bg-teal-500/15 text-teal-200 ring-1 ring-inset ring-teal-400/25"
                : "text-slate-300 hover:bg-slate-800 hover:text-white"
            }`}
          >
            <Icon className="size-5 shrink-0" />
            <span className="hidden lg:block">{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
