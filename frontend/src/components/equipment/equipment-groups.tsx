"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { CashRegisterCard } from "@/components/cash-registers/cash-register-card";
import { CashRegisterFormDialog } from "@/components/cash-registers/cash-register-form-dialog";
import { EquipmentCard } from "@/components/equipment/equipment-card";
import { EquipmentFormDialog } from "@/components/equipment/equipment-form-dialog";
import {
  BanknoteIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  FridgeIcon,
  SnowflakeIcon,
  TruckIcon,
} from "@/components/icons";
import { useI18n } from "@/components/locale-provider";
import type { MessageKey } from "@/lib/i18n";
import type { CashRegister, Equipment, Vehicle } from "@/lib/types";
import { VehicleCard } from "@/components/vehicles/vehicle-card";
import { VehicleFormDialog } from "@/components/vehicles/vehicle-form-dialog";

type GroupKey = "fridge" | "freezer" | "vehicles" | "cash-registers";

type EquipmentGroup = {
  key: GroupKey;
  labelKey: MessageKey;
  iconClass: string;
  items: Equipment[] | Vehicle[] | CashRegister[];
};

export function EquipmentGroups({
  equipment,
  vehicles,
  cashRegisters,
  isAdmin,
  includeVehicles,
  includeCashRegisters,
}: {
  equipment: Equipment[];
  vehicles: Vehicle[];
  cashRegisters: CashRegister[];
  isAdmin: boolean;
  includeVehicles: boolean;
  includeCashRegisters: boolean;
}) {
  const { locale, t } = useI18n();
  const [activeIndex, setActiveIndex] = useState(0);
  const touchStartRef = useRef<{ x: number; y: number } | null>(null);

  const groups = useMemo<EquipmentGroup[]>(() => {
    const next: EquipmentGroup[] = [
      {
        key: "fridge",
        labelKey: "Réfrigérateurs",
        iconClass: "bg-sky-50 text-sky-600 ring-sky-100",
        items: equipment.filter((item) => item.type === "fridge"),
      },
      {
        key: "freezer",
        labelKey: "Congélateurs",
        iconClass: "bg-indigo-50 text-indigo-600 ring-indigo-100",
        items: equipment.filter((item) => item.type === "freezer"),
      },
    ];
    if (includeVehicles) {
      next.push({
        key: "vehicles",
        labelKey: "Véhicules",
        iconClass: "bg-indigo-50 text-indigo-600 ring-indigo-100",
        items: vehicles,
      });
    }
    if (includeCashRegisters) {
      next.push({
        key: "cash-registers",
        labelKey: "Caisses",
        iconClass: "bg-emerald-50 text-emerald-600 ring-emerald-100",
        items: cashRegisters,
      });
    }
    return next;
  }, [cashRegisters, equipment, includeCashRegisters, includeVehicles, vehicles]);

  useEffect(() => {
    if (activeIndex < groups.length) {
      return;
    }
    setActiveIndex(0);
  }, [activeIndex, groups.length]);

  const move = (direction: -1 | 1) => {
    setActiveIndex((current) => (current + direction + groups.length) % groups.length);
  };

  const activeGroup = groups[activeIndex] ?? groups[0];

  return (
    <section data-equipment-carousel aria-label={t("Catégories de matériel")}>
      <div className="mb-3 flex items-center justify-between gap-3 lg:hidden">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t("Catégories de matériel")}
        </p>
        <div className="flex items-center gap-2">
          <button
            type="button"
            data-equipment-previous
            onClick={() => move(-1)}
            aria-label={t("Catégorie précédente")}
            className="grid size-11 place-items-center rounded-xl border border-slate-300 bg-white text-slate-600 shadow-sm transition hover:bg-slate-50 hover:text-slate-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-500"
          >
            <ChevronLeftIcon className="size-5" />
          </button>
          <button
            type="button"
            data-equipment-next
            onClick={() => move(1)}
            aria-label={t("Catégorie suivante")}
            className="grid size-11 place-items-center rounded-xl border border-slate-300 bg-white text-slate-600 shadow-sm transition hover:bg-slate-50 hover:text-slate-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-500"
          >
            <ChevronRightIcon className="size-5" />
          </button>
        </div>
      </div>

      <p className="sr-only" aria-live="polite">
        {activeGroup ? t(activeGroup.labelKey) : ""}
      </p>

      <div
        data-equipment-swipe
        className="touch-pan-y"
        onTouchStart={(event) => {
          const touch = event.touches[0];
          touchStartRef.current = touch ? { x: touch.clientX, y: touch.clientY } : null;
        }}
        onTouchEnd={(event) => {
          const start = touchStartRef.current;
          const touch = event.changedTouches[0];
          touchStartRef.current = null;
          if (!start || !touch) {
            return;
          }
          const deltaX = touch.clientX - start.x;
          const deltaY = touch.clientY - start.y;
          if (Math.abs(deltaX) < 60 || Math.abs(deltaX) <= Math.abs(deltaY) * 1.25) {
            return;
          }
          move(deltaX < 0 ? 1 : -1);
        }}
        onTouchCancel={() => {
          touchStartRef.current = null;
        }}
      >
        {groups.map((group, index) => (
          <section
            key={group.key}
            data-equipment-group={group.key}
            aria-labelledby={`equipment-group-${group.key}`}
            className={`${
              index === activeIndex ? "block animate-fade-in" : "hidden"
            } lg:mb-8 lg:block lg:animate-none`}
          >
            <GroupHeader group={group} />
            <div
              className={`mt-4 grid gap-4 sm:grid-cols-2 ${
                group.key === "cash-registers" ? "" : "xl:grid-cols-3"
              }`}
            >
              <GroupContent group={group} isAdmin={isAdmin} locale={locale} />
            </div>
          </section>
        ))}
      </div>

      {groups.length > 1 ? (
        <div className="mt-4 flex justify-center gap-1 lg:hidden">
          {groups.map((group, index) => {
            const active = index === activeIndex;
            return (
              <button
                key={group.key}
                type="button"
                data-equipment-dot={group.key}
                onClick={() => setActiveIndex(index)}
                aria-label={t("Afficher {category}", { category: t(group.labelKey) })}
                aria-pressed={active}
                className="grid size-10 place-items-center rounded-full focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-500"
              >
                <span
                  className={`size-2.5 rounded-full transition ${
                    active ? "scale-110 bg-teal-600" : "bg-slate-300 hover:bg-slate-400"
                  }`}
                />
              </button>
            );
          })}
        </div>
      ) : null}
    </section>
  );
}

function GroupHeader({ group }: { group: EquipmentGroup }) {
  const { t } = useI18n();
  const Icon =
    group.key === "fridge"
      ? FridgeIcon
      : group.key === "freezer"
        ? SnowflakeIcon
        : group.key === "vehicles"
          ? TruckIcon
          : BanknoteIcon;

  return (
    <header className="flex flex-wrap items-start justify-between gap-3">
      <div className="flex min-w-0 items-center gap-3">
        <span
          className={`grid size-10 shrink-0 place-items-center rounded-xl ring-1 ${group.iconClass}`}
        >
          <Icon className="size-5" />
        </span>
        <div className="min-w-0">
          <h2 id={`equipment-group-${group.key}`} className="text-base font-semibold text-slate-900">
            {t(group.labelKey)}
          </h2>
          <p className="text-xs text-slate-500">{groupCountLabel(group, t)}</p>
        </div>
      </div>
      <GroupCreateAction group={group} />
    </header>
  );
}

function GroupCreateAction({ group }: { group: EquipmentGroup }) {
  if (group.key === "fridge" || group.key === "freezer") {
    return <EquipmentFormDialog defaultType={group.key} />;
  }
  if (group.key === "vehicles") {
    return <VehicleFormDialog />;
  }
  return <CashRegisterFormDialog />;
}

function GroupContent({
  group,
  isAdmin,
  locale,
}: {
  group: EquipmentGroup;
  isAdmin: boolean;
  locale: "fr" | "en";
}) {
  const { t } = useI18n();
  if (group.items.length === 0) {
    return (
      <EmptyGroup
        message={emptyGroupMessage(group.key, t)}
        className={group.key === "cash-registers" ? "" : "sm:col-span-2 xl:col-span-3"}
      />
    );
  }
  if (group.key === "fridge" || group.key === "freezer") {
    return (group.items as Equipment[]).map((item) => (
      <EquipmentCard key={item.id} equipment={item} locale={locale} />
    ));
  }
  if (group.key === "vehicles") {
    return (group.items as Vehicle[]).map((vehicle) => (
      <VehicleCard key={vehicle.id} vehicle={vehicle} isAdmin={isAdmin} locale={locale} />
    ));
  }
  return (group.items as CashRegister[]).map((cashRegister) => (
    <CashRegisterCard
      key={cashRegister.id}
      cashRegister={cashRegister}
      isAdmin={isAdmin}
      locale={locale}
    />
  ));
}

function EmptyGroup({ message, className = "" }: { message: string; className?: string }) {
  return (
    <div
      className={`rounded-2xl border border-dashed border-slate-300 bg-white/60 px-5 py-8 text-center text-sm text-slate-500 ${className}`}
    >
      {message}
    </div>
  );
}

function groupCountLabel(group: EquipmentGroup, t: ReturnType<typeof useI18n>["t"]): string {
  const count = group.items.length;
  if (group.key === "vehicles") {
    return count === 1 ? t("1 véhicule") : t("{count} véhicules", { count });
  }
  if (group.key === "cash-registers") {
    return count === 1 ? t("1 caisse") : t("{count} caisses", { count });
  }
  return count === 1 ? t("1 équipement") : t("{count} équipements", { count });
}

function emptyGroupMessage(
  key: GroupKey,
  t: ReturnType<typeof useI18n>["t"],
): string {
  switch (key) {
    case "fridge":
      return t("Aucun réfrigérateur enregistré. Ajoute un réfrigérateur pour commencer.");
    case "freezer":
      return t("Aucun congélateur enregistré. Ajoute un congélateur pour commencer.");
    case "vehicles":
      return t(
        "Aucun véhicule enregistré. Ajoute un nom ou une plaque pour pouvoir déclarer des transports.",
      );
    case "cash-registers":
      return t(
        "Aucune caisse enregistrée. Déclare une caisse et son comptage initial pour préparer le suivi.",
      );
  }
}
