import { NextResponse, type NextRequest } from "next/server";

import { ApiError, apiFetch } from "@/lib/api";
import type { LatexTemplate } from "@/lib/types";

export const dynamic = "force-dynamic";

/**
 * Upload proxy. A route handler is used instead of a Server Action so the
 * configurable file size limit is not capped by the 1 MiB action body limit.
 */
export async function POST(request: NextRequest) {
  let formData: FormData;
  try {
    formData = await request.formData();
  } catch {
    return NextResponse.json(
      { code: "invalid_form", detail: "Formulaire d'import invalide." },
      { status: 400 },
    );
  }

  try {
    const template = await apiFetch<LatexTemplate>("/api/v1/templates", {
      method: "POST",
      body: formData,
    });
    return NextResponse.json(template, { status: 201 });
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json(
        { code: error.code, detail: error.message },
        { status: error.status },
      );
    }
    throw error;
  }
}
