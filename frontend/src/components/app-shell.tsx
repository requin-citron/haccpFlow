import Link from "next/link";

import { logoutAction } from "@/actions/auth";
import { LogOutIcon, SnowflakeIcon } from "@/components/icons";
import { NavLinks } from "@/components/nav-links";
import type { CurrentUser, UserRole } from "@/lib/types";

const ROLE_LABELS: Record<UserRole, string> = {
  admin: "Administrateur",
  operator: "Opérateur",
};

export function AppShell({ user, children }: { user: CurrentUser; children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <aside className="sticky top-0 flex h-screen w-[72px] shrink-0 flex-col border-r border-slate-800 bg-slate-900 px-3 py-5 lg:w-64 lg:px-4">
        <Link href="/equipment" className="mb-8 flex items-center gap-3 px-1">
          <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-teal-500/15 text-teal-300 ring-1 ring-teal-400/25">
            <SnowflakeIcon className="size-5" />
          </span>
          <span className="hidden text-base font-semibold tracking-tight text-white lg:block">
            haccpFlow
          </span>
        </Link>

        <NavLinks />

        <div className="mt-auto space-y-3 border-t border-slate-800 pt-4">
          <div className="hidden px-1 lg:block">
            <p className="truncate text-sm font-medium text-slate-200">{user.email}</p>
            <p className="text-xs text-slate-500">{ROLE_LABELS[user.role]}</p>
          </div>
          <form action={logoutAction}>
            <button
              type="submit"
              className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-slate-300 transition hover:bg-slate-800 hover:text-white"
            >
              <LogOutIcon className="size-5 shrink-0" />
              <span className="hidden lg:block">Se déconnecter</span>
            </button>
          </form>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <main className="mx-auto w-full max-w-6xl flex-1 px-5 py-8 lg:px-10 lg:py-10">
          {children}
        </main>
        <footer className="px-5 pb-6 text-xs text-slate-400 lg:px-10">
          Relevés horodatés en UTC · haccpFlow
        </footer>
      </div>
    </div>
  );
}
