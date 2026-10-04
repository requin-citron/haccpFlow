"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import {
  BanknoteIcon,
  CheckIcon,
  ClipboardIcon,
  DropletIcon,
  DownloadIcon,
  FlameIcon,
  GridIcon,
  HistoryIcon,
  TruckIcon,
} from "@/components/icons";

const NAV_ITEMS = [
  { href: "/equipment", label: "Matériel", icon: GridIcon },
  { href: "/readings", label: "Relevés", icon: ClipboardIcon },
  { href: "/cleaning", label: "Nettoyage", icon: CheckIcon },
  { href: "/cleaning/plans", label: "Plan de nettoyage", icon: DropletIcon },
  { href: "/pasteurisation", label: "Pasteurisation", icon: FlameIcon },
  { href: "/transport", label: "Transport", icon: TruckIcon },
  { href: "/cash-sessions", label: "Suivi de caisse", icon: BanknoteIcon },
  { href: "/export", label: "Export", icon: DownloadIcon },
  { href: "/history", label: "Historique", icon: HistoryIcon, adminOnly: true },
];

export function NavLinks({ isAdmin }: { isAdmin: boolean }) {
  const pathname = usePathname();
  const items = NAV_ITEMS.filter((item) => !item.adminOnly || isAdmin);
  // Longest matching href wins, so /cleaning/plans does not also light up
  // the /cleaning entry.
  const activeHref = items.filter(
    (item) => pathname === item.href || pathname.startsWith(`${item.href}/`),
  ).sort((first, second) => second.href.length - first.href.length)[0]?.href;

  return (
    <nav aria-label="Navigation principale" className="space-y-1">
      {items.map((item) => {
        const Icon = item.icon;
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
