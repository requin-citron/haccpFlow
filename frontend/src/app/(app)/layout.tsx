import { redirect } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { ApiError, apiFetch } from "@/lib/api";
import type { CurrentUser } from "@/lib/types";

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  let user: CurrentUser;
  try {
    user = await apiFetch<CurrentUser>("/api/v1/auth/me");
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      redirect("/login");
    }
    throw error;
  }

  return <AppShell user={user}>{children}</AppShell>;
}
