"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { ClipboardIcon, GridIcon, SensorIcon } from "@/components/icons";

const NAV_ITEMS = [
  { href: "/equipment", label: "Matériel", icon: GridIcon, available: true },
  { href: "/sensors", label: "Capteurs", icon: SensorIcon, available: false },
  { href: "/measurements", label: "Relevés", icon: ClipboardIcon, available: false },
];

export function NavLinks() {
  const pathname = usePathname();

  return (
    <nav aria-label="Navigation principale" className="space-y-1">
      {NAV_ITEMS.map((item) => {
        const Icon = item.icon;
        const active =
          item.available && (pathname === item.href || pathname.startsWith(`${item.href}/`));

        if (!item.available) {
          return (
            <span
              key={item.href}
              aria-disabled="true"
              className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-slate-500"
            >
              <Icon className="size-5 shrink-0" />
              <span className="hidden flex-1 lg:block">{item.label}</span>
              <span className="hidden rounded-full bg-slate-800 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-slate-400 lg:block">
                bientôt
              </span>
            </span>
          );
        }

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
