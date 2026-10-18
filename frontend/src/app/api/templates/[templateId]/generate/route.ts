import { NextResponse, type NextRequest } from "next/server";

import { ApiError, apiFetch } from "@/lib/api";
import type { GeneratedDocument } from "@/lib/types";

export const dynamic = "force-dynamic";

// The backend allows two 30-second pdflatex passes. Keep the client-side
// timeout above that budget so a slow but valid document is not reported as
// failed while the server is still generating it.
const PDF_GENERATION_TIMEOUT_MS = 120_000;

export async function POST(
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
    const document = await apiFetch<GeneratedDocument>(
      `/api/v1/templates/${encodeURIComponent(templateId)}/generate`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      },
      PDF_GENERATION_TIMEOUT_MS,
    );
    return NextResponse.json(document, { status: 201 });
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
