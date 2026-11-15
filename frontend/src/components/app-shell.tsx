"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { logoutAction } from "@/actions/auth";
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  CloseIcon,
  LogOutIcon,
  MenuIcon,
  SnowflakeIcon,
} from "@/components/icons";
import { useI18n } from "@/components/locale-provider";
import { LocaleSwitcher } from "@/components/locale-switcher";
import { NavLinks } from "@/components/nav-links";
import type { Locale } from "@/lib/i18n";
import {
  activeModuleNavItem,
  visibleModuleNavItems,
  type EnabledModules,
} from "@/lib/modules";
import type { CurrentUser } from "@/lib/types";
import { userRoleLabel } from "@/lib/users";

const SIDEBAR_COLLAPSED_KEY = "haccpflow.sidebar.collapsed";

export function AppShell({
  user,
  enabledModules,
  locale,
  children,
}: {
  user: CurrentUser;
  enabledModules: EnabledModules;
  locale: Locale;
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const { t } = useI18n();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [mobileHeaderVisible, setMobileHeaderVisible] = useState(true);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const drawerRef = useRef<HTMLElement>(null);
  const drawerWasOpenRef = useRef(false);
  const lastScrollYRef = useRef(0);
  const scrollTickingRef = useRef(false);

  const items = useMemo(
    () => visibleModuleNavItems(enabledModules, user.role === "admin"),
    [enabledModules, user.role],
  );
  const activeItem = activeModuleNavItem(items, pathname);
  const activeHref = activeItem?.href;

  useEffect(() => {
    try {
      setSidebarCollapsed(window.localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === "1");
    } catch {
      // Keep the expanded default when storage is unavailable.
    }
  }, []);

  useEffect(() => {
    setDrawerOpen(false);
    setMobileHeaderVisible(true);
  }, [pathname]);

  useEffect(() => {
    const desktopQuery = window.matchMedia("(min-width: 1024px)");
    lastScrollYRef.current = Math.max(0, window.scrollY);

    if (!desktopQuery.matches) {
      setMobileHeaderVisible(lastScrollYRef.current < 24);
    }

    const updateVisibility = () => {
      scrollTickingRef.current = false;
      if (desktopQuery.matches) {
        setMobileHeaderVisible(true);
        return;
      }

      const currentY = Math.max(0, window.scrollY);
      const delta = currentY - lastScrollYRef.current;

      if (currentY <= 16) {
        setMobileHeaderVisible(true);
      } else if (delta > 0 && currentY > 24) {
        setMobileHeaderVisible(false);
      } else if (delta < -8) {
        setMobileHeaderVisible(true);
      }

      lastScrollYRef.current = currentY;
    };

    const onScroll = () => {
      if (scrollTickingRef.current) {
        return;
      }
      scrollTickingRef.current = true;
      window.requestAnimationFrame(updateVisibility);
    };

    const onDesktopChange = () => {
      lastScrollYRef.current = Math.max(0, window.scrollY);
      setMobileHeaderVisible(true);
    };

    window.addEventListener("scroll", onScroll, { passive: true });
    desktopQuery.addEventListener("change", onDesktopChange);
    return () => {
      window.removeEventListener("scroll", onScroll);
      desktopQuery.removeEventListener("change", onDesktopChange);
    };
  }, []);

  useEffect(() => {
    if (!drawerOpen) {
      if (drawerWasOpenRef.current) {
        drawerWasOpenRef.current = false;
        menuButtonRef.current?.focus();
      }
      return;
    }

    drawerWasOpenRef.current = true;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const focusFrame = window.requestAnimationFrame(() => {
      drawerRef.current?.querySelector<HTMLElement>("button, a[href]")?.focus();
    });

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setDrawerOpen(false);
        return;
      }
      if (event.key !== "Tab" || !drawerRef.current) {
        return;
      }

      const focusable = Array.from(
        drawerRef.current.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ),
      );
      if (focusable.length === 0) {
        return;
      }

      const first = focusable[0];
      const last = focusable.at(-1);
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    };

    document.addEventListener("keydown", onKeyDown);
    return () => {
      window.cancelAnimationFrame(focusFrame);
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [drawerOpen]);

  const toggleSidebar = () => {
    setSidebarCollapsed((current) => {
      const next = !current;
      try {
        window.localStorage.setItem(SIDEBAR_COLLAPSED_KEY, next ? "1" : "0");
      } catch {
        // The visual state still changes for the current page.
      }
      return next;
    });
  };

  const closeDrawer = () => setDrawerOpen(false);
  const openDrawer = () => {
    setMobileHeaderVisible(true);
    setDrawerOpen(true);
  };

  return (
    <div className="flex min-h-dvh">
      <aside
        className={`sticky top-0 hidden h-dvh shrink-0 flex-col border-r border-slate-800 bg-slate-900 px-3 py-5 transition-[width] duration-200 lg:flex ${
          sidebarCollapsed ? "w-20" : "w-64"
        }`}
      >
        <div
          className={`mb-8 flex items-center ${
            sidebarCollapsed ? "flex-col gap-3" : "justify-between gap-2"
          }`}
        >
          <Link
            href="/"
            className={`flex items-center gap-3 rounded-xl focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-400 ${
              sidebarCollapsed ? "justify-center" : "min-w-0 flex-1"
            }`}
            aria-label="haccpFlow"
          >
            <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-teal-500/15 text-teal-300 ring-1 ring-teal-400/25">
              <SnowflakeIcon className="size-5" />
            </span>
            {!sidebarCollapsed ? (
              <span className="truncate text-base font-semibold tracking-tight text-white">
                haccpFlow
              </span>
            ) : null}
          </Link>
          <button
            type="button"
            onClick={toggleSidebar}
            aria-label={t(
              sidebarCollapsed
                ? "Développer la navigation"
                : "Réduire la navigation",
            )}
            title={t(
              sidebarCollapsed
                ? "Développer la navigation"
                : "Réduire la navigation",
            )}
            className="grid size-9 shrink-0 place-items-center rounded-lg text-slate-400 transition hover:bg-slate-800 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-400"
          >
            {sidebarCollapsed ? (
              <ChevronRightIcon className="size-4" />
            ) : (
              <ChevronLeftIcon className="size-4" />
            )}
          </button>
        </div>

        <NavLinks
          items={items}
          activeHref={activeHref}
          variant="sidebar"
          showLabels={!sidebarCollapsed}
        />

        <div className="mt-auto space-y-3 border-t border-slate-800 pt-4">
          {!sidebarCollapsed ? (
            <div className="px-1">
              <p className="truncate text-sm font-medium text-slate-200">{user.email}</p>
              <p className="text-xs text-slate-500">{userRoleLabel(locale, user.role)}</p>
            </div>
          ) : null}
          <div className={sidebarCollapsed ? "flex justify-center" : ""}>
            <LocaleSwitcher compact />
          </div>
          <form action={logoutAction}>
            <button
              type="submit"
              title={t("Se déconnecter")}
              aria-label={t("Se déconnecter")}
              className={`flex min-h-11 w-full items-center rounded-xl text-sm font-medium text-slate-300 transition hover:bg-slate-800 hover:text-white ${
                sidebarCollapsed ? "justify-center px-2" : "gap-3 px-3"
              }`}
            >
              <LogOutIcon className="size-5 shrink-0" />
              {!sidebarCollapsed ? <span>{t("Se déconnecter")}</span> : null}
            </button>
          </form>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header
          data-mobile-header
          aria-hidden={!mobileHeaderVisible}
          inert={!mobileHeaderVisible ? true : undefined}
          className={`sticky top-0 z-30 border-b border-slate-800 bg-slate-900/95 px-3 pb-2 pt-[calc(env(safe-area-inset-top)+0.5rem)] text-slate-100 backdrop-blur transition-transform duration-200 ease-out motion-reduce:transition-none lg:hidden ${
            mobileHeaderVisible ? "translate-y-0" : "-translate-y-full"
          }`}
        >
          <div className="flex min-h-12 items-center gap-2">
            <button
              ref={menuButtonRef}
              type="button"
              onClick={openDrawer}
              aria-label={t("Ouvrir le menu")}
              aria-expanded={drawerOpen}
              aria-controls="mobile-navigation-drawer"
              className="grid size-11 shrink-0 place-items-center rounded-xl text-slate-300 transition hover:bg-slate-800 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-400"
            >
              <MenuIcon className="size-5" />
            </button>
            <div className="min-w-0 flex-1">
              <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                haccpFlow
              </p>
              <p className="truncate text-sm font-semibold">
                {activeItem ? t(activeItem.labelKey) : "haccpFlow"}
              </p>
            </div>
            <LocaleSwitcher compact />
          </div>
        </header>

        <main className="mx-auto w-full max-w-7xl flex-1 px-4 pb-[calc(1.5rem+env(safe-area-inset-bottom))] pt-6 sm:px-5 lg:px-10 lg:pb-10 lg:pt-10">
          {children}
        </main>
        <footer className="px-4 pb-[calc(1.5rem+env(safe-area-inset-bottom))] text-xs text-slate-400 sm:px-5 lg:px-10 lg:pb-6">
          {t("Données horodatées en UTC · haccpFlow")}
        </footer>
      </div>

      {drawerOpen ? (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            type="button"
            aria-label={t("Fermer le menu")}
            onClick={closeDrawer}
            className="absolute inset-0 bg-slate-950/55 backdrop-blur-[2px]"
          />
          <aside
            id="mobile-navigation-drawer"
            ref={drawerRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="mobile-navigation-title"
            className="animate-drawer-in relative flex h-dvh w-[min(86vw,340px)] flex-col overflow-y-auto border-r border-slate-800 bg-slate-900 px-4 pb-[calc(env(safe-area-inset-bottom)+1rem)] pt-[calc(env(safe-area-inset-top)+1rem)] text-slate-100 shadow-2xl"
          >
            <header className="mb-5 flex items-center justify-between gap-3 border-b border-slate-800 pb-4">
              <div className="flex items-center gap-3">
                <span className="grid size-10 place-items-center rounded-xl bg-teal-500/15 text-teal-300 ring-1 ring-teal-400/25">
                  <SnowflakeIcon className="size-5" />
                </span>
                <div>
                  <p id="mobile-navigation-title" className="font-semibold">
                    haccpFlow
                  </p>
                  <p className="text-xs text-slate-500">{t("Compte et navigation")}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={closeDrawer}
                aria-label={t("Fermer le menu")}
                className="grid size-11 place-items-center rounded-xl text-slate-400 transition hover:bg-slate-800 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-400"
              >
                <CloseIcon className="size-5" />
              </button>
            </header>

            <NavLinks
              items={items}
              activeHref={activeHref}
              variant="drawer"
              showLabels
              onNavigate={closeDrawer}
            />

            <div className="mt-auto space-y-4 border-t border-slate-800 pt-4">
              <div>
                <p className="truncate text-sm font-medium text-slate-200">{user.email}</p>
                <p className="text-xs text-slate-500">
                  {userRoleLabel(locale, user.role)}
                </p>
              </div>
              <LocaleSwitcher compact />
              <form action={logoutAction}>
                <button
                  type="submit"
                  className="flex min-h-11 w-full items-center gap-3 rounded-xl px-3 text-sm font-medium text-slate-300 transition hover:bg-slate-800 hover:text-white"
                >
                  <LogOutIcon className="size-5" />
                  {t("Se déconnecter")}
                </button>
              </form>
            </div>
          </aside>
        </div>
      ) : null}

    </div>
  );
}
