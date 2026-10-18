import { NextResponse, type NextRequest } from "next/server";

import { ApiError, apiFetch } from "@/lib/api";
import type { LatexTemplate } from "@/lib/types";

export const dynamic = "force-dynamic";

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ templateId: string }> },
) {
  const { templateId } = await params;
  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return NextResponse.json({ detail: "Requête invalide." }, { status: 400 });
  }

  try {
    const template = await apiFetch<LatexTemplate>(
      `/api/v1/templates/${encodeURIComponent(templateId)}`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      },
    );
    return NextResponse.json(template);
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json(
        { code: error.code, detail: error.message, context: error.context },
        { status: error.status },
      );
    }
    throw error;
  }
}
