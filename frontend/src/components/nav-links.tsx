"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { ClipboardIcon, GridIcon } from "@/components/icons";

const NAV_ITEMS = [
  { href: "/equipment", label: "Matériel", icon: GridIcon },
  { href: "/readings", label: "Relevés", icon: ClipboardIcon },
];

export function NavLinks() {
  const pathname = usePathname();

  return (
    <nav aria-label="Navigation principale" className="space-y-1">
      {NAV_ITEMS.map((item) => {
        const Icon = item.icon;
        const active = pathname === item.href || pathname.startsWith(`${item.href}/`);

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
