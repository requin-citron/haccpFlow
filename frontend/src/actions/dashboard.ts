"use server";

import { revalidatePath } from "next/cache";

import { apiFetch } from "@/lib/api";
import type {
  DashboardMissingReadings,
  DashboardRevenue,
  DashboardWidgetConfig,
} from "@/lib/types";

export async function fetchDashboardRevenueAction(
  from: string,
  to: string,
): Promise<DashboardRevenue> {
  const query = new URLSearchParams({ from, to });
  return apiFetch<DashboardRevenue>(`/api/v1/dashboard/revenue?${query.toString()}`);
}

export async function fetchDashboardMissingReadingsAction(
  from: string,
  to: string,
): Promise<DashboardMissingReadings> {
  const query = new URLSearchParams({ from, to });
  return apiFetch<DashboardMissingReadings>(
    `/api/v1/dashboard/missing-readings?${query.toString()}`,
  );
}

export async function saveDashboardLayoutAction(
  widgets: DashboardWidgetConfig[],
): Promise<void> {
  await apiFetch("/api/v1/dashboard/layout", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ widgets }),
  });
  revalidatePath("/");
}
