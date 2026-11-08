import { cache } from "react";
import { redirect } from "next/navigation";

import { ApiError, apiFetch } from "@/lib/api";
import type { CurrentUser } from "@/lib/types";

const loadCurrentUser = cache(() => apiFetch<CurrentUser>("/api/v1/auth/me"));

export async function requireCurrentUser(): Promise<CurrentUser> {
  try {
    return await loadCurrentUser();
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      redirect("/login");
    }
    throw error;
  }
}
