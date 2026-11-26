"use client";

import {
  type CSSProperties,
  type PointerEvent as ReactPointerEvent,
  useEffect,
  useRef,
  useState,
} from "react";

import {
  fetchDashboardMissingReadingsAction,
  fetchDashboardRevenueAction,
  saveDashboardLayoutAction,
} from "@/actions/dashboard";
import {
  AlertIcon,
  CheckIcon,
  DragHandleIcon,
  PencilIcon,
  PlusIcon,
  TrashIcon,
} from "@/components/icons";
import { useI18n } from "@/components/locale-provider";
import { MissingReadingsWidget } from "@/components/dashboard/missing-readings-widget";
import { RevenueWidget } from "@/components/dashboard/revenue-widget";
import type { Locale } from "@/lib/i18n";
import type {
  DashboardMissingReadings,
  DashboardLayout,
  DashboardRevenue,
  DashboardWidgetConfig,
} from "@/lib/types";

const MIN_WIDTH = 3;

type GridStyle = CSSProperties & {
  "--widget-start": number;
  "--widget-row-start": number;
  "--widget-width": number;
  "--widget-rows": number;
};

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.min(Math.max(value, minimum), maximum);
}

function widgetStyle(widget: DashboardWidgetConfig): GridStyle {
  return {
    "--widget-start": widget.column_start,
    "--widget-row-start": widget.row_start,
    "--widget-width": widget.width_columns,
    "--widget-rows": widget.row_span,
  };
}

function minimumHeight(widget: DashboardWidgetConfig["key"]): number {
  return widget === "revenue" ? 5 : 3;
}

function widgetsOverlap(
  first: DashboardWidgetConfig,
  second: DashboardWidgetConfig,
): boolean {
  return (
    first.column_start < second.column_start + second.width_columns &&
    first.column_start + first.width_columns > second.column_start &&
    first.row_start < second.row_start + second.row_span &&
    first.row_start + first.row_span > second.row_start
  );
}

function placeWithoutOverlap(
  widget: DashboardWidgetConfig,
  others: readonly DashboardWidgetConfig[],
): DashboardWidgetConfig {
  let candidate = {
    ...widget,
    column_start: clamp(widget.column_start, 1, 13 - widget.width_columns),
    row_start: Math.max(1, widget.row_start),
  };

  while (others.some((other) => widgetsOverlap(candidate, other))) {
    const blocking = others.filter((other) => widgetsOverlap(candidate, other));
    candidate = {
      ...candidate,
      row_start: Math.max(...blocking.map((other) => other.row_start + other.row_span)),
    };
  }
  return candidate;
}

function normalizeLayout(
  widgets: readonly DashboardWidgetConfig[],
): DashboardWidgetConfig[] {
  const normalized: DashboardWidgetConfig[] = [];
  for (const widget of widgets) {
    normalized.push(placeWithoutOverlap(widget, normalized));
  }
  return normalized;
}

export function ConfigurableDashboard({
  initialLayout,
  initialRevenue,
  initialMissingReadings,
  periodFrom,
  periodTo,
  locale,
}: {
  initialLayout: DashboardLayout;
  initialRevenue: DashboardRevenue | null;
  initialMissingReadings: DashboardMissingReadings | null;
  periodFrom: string;
  periodTo: string;
  locale: Locale;
}) {
  const { t: translate } = useI18n();
  const [layout, setLayout] = useState(() => normalizeLayout(initialLayout.widgets));
  const [revenue, setRevenue] = useState(initialRevenue);
  const [missingReadings, setMissingReadings] = useState(initialMissingReadings);
  const [editing, setEditing] = useState(false);
  const [catalogOpen, setCatalogOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const gridRef = useRef<HTMLDivElement>(null);
  const lastSavedRef = useRef(normalizeLayout(initialLayout.widgets));

  useEffect(() => {
    // The page is re-rendered by the URL period change, while this client
    // component instance stays mounted. Keep the widget in sync with it.
    setRevenue(initialRevenue);
    setMissingReadings(initialMissingReadings);
  }, [initialMissingReadings, initialRevenue, periodFrom, periodTo]);

  const revenueWidget = layout.find((widget) => widget.key === "revenue");
  const missingReadingsWidget = layout.find(
    (widget) => widget.key === "missing_readings",
  );

  const persist = async (next: DashboardWidgetConfig[]) => {
    const previous = lastSavedRef.current;
    setLayout(next);
    setSaving(true);
    setError("");
    try {
      await saveDashboardLayoutAction(next);
      lastSavedRef.current = next;
    } catch {
      setLayout(previous);
      setError(translate("La disposition du dashboard n'a pas pu être enregistrée."));
    } finally {
      setSaving(false);
    }
  };

  const addWidget = async (key: DashboardWidgetConfig["key"]) => {
    if (saving || layout.some((widget) => widget.key === key)) {
      return;
    }
    setError("");
    if (key === "revenue" && !revenue) {
      try {
        setSaving(true);
        setRevenue(await fetchDashboardRevenueAction(periodFrom, periodTo));
      } catch {
        setError(translate("Les données du widget n'ont pas pu être chargées."));
        setSaving(false);
        return;
      }
    }
    if (key === "missing_readings" && !missingReadings) {
      try {
        setSaving(true);
        setMissingReadings(
          await fetchDashboardMissingReadingsAction(periodFrom, periodTo),
        );
      } catch {
        setError(translate("Les données du widget n'ont pas pu être chargées."));
        setSaving(false);
        return;
      }
    }
    setCatalogOpen(false);
    await persist([
      ...layout,
      {
        key,
        column_start: 1,
        row_start:
          Math.max(1, ...layout.map((item) => item.row_start + item.row_span)),
        width_columns: 6,
        row_span: 6,
      },
    ]);
  };

  const removeWidget = async (key: DashboardWidgetConfig["key"]) => {
    if (saving) {
      return;
    }
    await persist(layout.filter((widget) => widget.key !== key));
  };

  const beginResize = (
    event: ReactPointerEvent<HTMLButtonElement>,
    widget: DashboardWidgetConfig,
    side: "left" | "right" | "top" | "bottom",
  ) => {
    const grid = gridRef.current;
    const card = event.currentTarget.parentElement;
    if (!grid || !card || saving) {
      return;
    }

    event.preventDefault();
    const gridRect = grid.getBoundingClientRect();
    const columnWidth = gridRect.width / 12;
    const initialStart = widget.column_start;
    const initialWidth = widget.width_columns;
    const initialRows = widget.row_span;
    const initialPointerY = event.clientY;
    const rightEdge = initialStart + initialWidth - 1;
    const gridStyle = window.getComputedStyle(grid);
    const rowHeight = Number.parseFloat(gridStyle.gridAutoRows) || 64;
    const rowGap = Number.parseFloat(gridStyle.rowGap) || 0;
    const rowStep = rowHeight + rowGap;
    let latest = layout;

    const onPointerMove = (moveEvent: PointerEvent) => {
      const pointerColumn = Math.round((moveEvent.clientX - gridRect.left) / columnWidth);
      latest = layout.map((current) => {
        if (current.key !== widget.key) {
          return current;
        }
        if (side === "top" || side === "bottom") {
          const delta =
            side === "bottom"
              ? Math.round((moveEvent.clientY - initialPointerY) / rowStep)
              : Math.round((initialPointerY - moveEvent.clientY) / rowStep);
          return {
            ...current,
            row_span: clamp(
              initialRows + delta,
              minimumHeight(widget.key),
              12,
            ),
          };
        }
        if (side === "right") {
          const endColumn = clamp(pointerColumn, initialStart + MIN_WIDTH - 1, 12);
          return {
            ...current,
            width_columns: endColumn - initialStart + 1,
          };
        }
        const nextStart = clamp(pointerColumn + 1, 1, rightEdge - MIN_WIDTH + 1);
        return {
          ...current,
          column_start: nextStart,
          width_columns: rightEdge - nextStart + 1,
        };
      });
      const resized = latest.find((current) => current.key === widget.key);
      if (resized) {
        const placed = placeWithoutOverlap(
          resized,
          latest.filter((current) => current.key !== widget.key),
        );
        latest = latest.map((current) =>
          current.key === widget.key ? placed : current,
        );
      }
      setLayout(latest);
    };

    const stopResize = () => {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", stopResize);
      window.removeEventListener("pointercancel", stopResize);
      document.body.classList.remove(
        "dashboard-resizing",
        "dashboard-resizing-horizontal",
        "dashboard-resizing-vertical",
      );
      void persist(latest);
    };

    const resizeClass =
      side === "top" || side === "bottom"
        ? "dashboard-resizing-vertical"
        : "dashboard-resizing-horizontal";
    document.body.classList.add("dashboard-resizing", resizeClass);
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", stopResize, { once: true });
    window.addEventListener("pointercancel", stopResize, { once: true });
  };

  const beginMove = (
    event: ReactPointerEvent<HTMLButtonElement>,
    widget: DashboardWidgetConfig,
  ) => {
    const grid = gridRef.current;
    if (!grid || saving) {
      return;
    }

    event.preventDefault();
    const gridRect = grid.getBoundingClientRect();
    const gridStyle = window.getComputedStyle(grid);
    const columnWidth = gridRect.width / 12;
    const rowHeight = Number.parseFloat(gridStyle.gridAutoRows) || 64;
    const rowGap = Number.parseFloat(gridStyle.rowGap) || 0;
    const rowStep = rowHeight + rowGap;
    const initialPointerX = event.clientX;
    const initialPointerY = event.clientY;
    let latest = layout;

    const onPointerMove = (moveEvent: PointerEvent) => {
      const deltaColumns = Math.round(
        (moveEvent.clientX - initialPointerX) / columnWidth,
      );
      const deltaRows = Math.round(
        (moveEvent.clientY - initialPointerY) / rowStep,
      );
      const moved = {
        ...widget,
        column_start: widget.column_start + deltaColumns,
        row_start: Math.max(1, widget.row_start + deltaRows),
      };
      const placed = placeWithoutOverlap(
        moved,
        layout.filter((item) => item.key !== widget.key),
      );
      latest = layout.map((item) =>
        item.key === widget.key ? placed : item,
      );
      setLayout(latest);
    };

    const stopMove = () => {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", stopMove);
      window.removeEventListener("pointercancel", stopMove);
      document.body.classList.remove("dashboard-moving");
      void persist(latest);
    };

    document.body.classList.add("dashboard-moving");
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", stopMove, { once: true });
    window.addEventListener("pointercancel", stopMove, { once: true });
  };

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-slate-900">
            {translate("Widgets du dashboard")}
          </h2>
          <p className="mt-0.5 text-xs text-slate-500">
            {editing
              ? translate(
                  "Déplace, ajoute, retire ou redimensionne les widgets. Les changements sont enregistrés automatiquement.",
                )
              : translate("Ta disposition est synchronisée avec ton compte.")}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {editing ? (
            <button
              type="button"
              onClick={() => setCatalogOpen((current) => !current)}
              className="inline-flex min-h-10 items-center gap-2 rounded-xl border border-slate-300 bg-white px-3.5 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50"
            >
              <PlusIcon className="size-4" />
              {translate("Ajouter un widget")}
            </button>
          ) : null}
          <button
            type="button"
            onClick={() => {
              setEditing((current) => !current);
              setCatalogOpen(false);
            }}
            className={`inline-flex min-h-10 items-center gap-2 rounded-xl px-3.5 text-sm font-medium shadow-sm transition ${
              editing
                ? "bg-teal-600 text-white hover:bg-teal-700"
                : "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
            }`}
          >
            {editing ? <CheckIcon className="size-4" /> : <PencilIcon className="size-4" />}
            {editing ? translate("Terminer") : translate("Modifier le dashboard")}
          </button>
        </div>
      </div>

      {editing && catalogOpen ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-sm font-semibold text-slate-900">
            {translate("Widgets disponibles")}
          </p>
          <div className="mt-3 space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-slate-50 px-4 py-3">
              <div>
                <p className="text-sm font-medium text-slate-800">
                  {translate("Chiffre d'affaires")}
                </p>
                <p className="mt-0.5 text-xs text-slate-500">
                  {translate("Total et ventilation par moyen de paiement.")}
                </p>
              </div>
              <button
                type="button"
                onClick={() => addWidget("revenue")}
                disabled={Boolean(revenueWidget) || saving}
                className="rounded-lg bg-teal-600 px-3 py-2 text-xs font-semibold text-white transition hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {revenueWidget ? translate("Ajouté") : translate("Ajouter")}
              </button>
            </div>
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-slate-50 px-4 py-3">
              <div>
                <p className="text-sm font-medium text-slate-800">
                  {translate("Relevés manquants")}
                </p>
                <p className="mt-0.5 text-xs text-slate-500">
                  {translate("Créneaux de température non renseignés.")}
                </p>
              </div>
              <button
                type="button"
                onClick={() => addWidget("missing_readings")}
                disabled={Boolean(missingReadingsWidget) || saving}
                className="rounded-lg bg-teal-600 px-3 py-2 text-xs font-semibold text-white transition hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {missingReadingsWidget ? translate("Ajouté") : translate("Ajouter")}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {error ? (
        <p
          role="alert"
          className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 px-3.5 py-2.5 text-sm text-rose-700"
        >
          <AlertIcon className="mt-0.5 size-4 shrink-0" />
          <span>{error}</span>
        </p>
      ) : null}

      {saving ? (
        <p className="text-xs text-slate-500" role="status">
          {translate("Enregistrement de la disposition…")}
        </p>
      ) : null}

      {layout.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white/60 px-5 py-12 text-center">
          <p className="text-sm font-semibold text-slate-800">
            {translate("Aucun widget sur le dashboard")}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            {translate("Passe en mode modification pour ajouter un widget.")}
          </p>
        </div>
      ) : (
        <div ref={gridRef} className="dashboard-grid">
          {layout.map((widget) => {
            const widgetName =
              widget.key === "revenue"
                ? translate("Chiffre d'affaires")
                : translate("Relevés manquants");
            const content =
              widget.key === "revenue" && revenue ? (
                <RevenueWidget revenue={revenue} locale={locale} />
              ) : widget.key === "missing_readings" && missingReadings ? (
                <MissingReadingsWidget readings={missingReadings} locale={locale} />
              ) : null;
            if (!content) {
              return null;
            }
            return (
              <div
                key={widget.key}
                style={widgetStyle(widget)}
                className="dashboard-widget min-w-0"
                data-editing={editing ? "true" : "false"}
              >
                {editing ? (
                  <div className="mb-2 flex justify-end gap-1">
                    <button
                      type="button"
                      onPointerDown={(event) => beginMove(event, widget)}
                      disabled={saving}
                      aria-label={translate("Déplacer le widget {name}", {
                        name: widgetName,
                      })}
                      className="dashboard-move-handle grid size-8 place-items-center rounded-lg border border-slate-300 bg-white text-slate-600 shadow-sm transition hover:bg-slate-50 disabled:opacity-40"
                    >
                      <DragHandleIcon className="size-4" />
                    </button>
                    <button
                      type="button"
                      onClick={() => removeWidget(widget.key)}
                      disabled={saving}
                      aria-label={translate("Retirer le widget {name}", {
                        name: widgetName,
                      })}
                      className="grid size-8 place-items-center rounded-lg border border-rose-200 bg-white text-rose-600 shadow-sm transition hover:bg-rose-50 disabled:opacity-40"
                    >
                      <TrashIcon className="size-4" />
                    </button>
                  </div>
                ) : null}

                <article
                  className={`dashboard-widget-card relative ${
                    editing ? "rounded-2xl ring-2 ring-teal-500/35 ring-offset-4" : ""
                  }`}
                >
                  {content}

                  {editing ? (
                    <>
                      <button
                        type="button"
                        aria-label={translate("Redimensionner le widget depuis la gauche")}
                        onPointerDown={(event) => beginResize(event, widget, "left")}
                        className="dashboard-resize-handle dashboard-resize-handle-left"
                      />
                      <button
                        type="button"
                        aria-label={translate("Redimensionner le widget depuis la droite")}
                        onPointerDown={(event) => beginResize(event, widget, "right")}
                        className="dashboard-resize-handle dashboard-resize-handle-right"
                      />
                      <button
                        type="button"
                        aria-label={translate("Redimensionner le widget depuis le haut")}
                        onPointerDown={(event) => beginResize(event, widget, "top")}
                        className="dashboard-resize-handle dashboard-resize-handle-top"
                      />
                      <button
                        type="button"
                        aria-label={translate("Redimensionner le widget depuis le bas")}
                        onPointerDown={(event) => beginResize(event, widget, "bottom")}
                        className="dashboard-resize-handle dashboard-resize-handle-bottom"
                      />
                    </>
                  ) : null}
                </article>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
