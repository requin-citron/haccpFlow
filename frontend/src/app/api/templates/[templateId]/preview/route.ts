import { NextResponse, type NextRequest } from "next/server";

import { ApiError, apiFetchRaw } from "@/lib/api";

export const dynamic = "force-dynamic";

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

  let response: Response;
  try {
    response = await apiFetchRaw(
      `/api/v1/templates/${encodeURIComponent(templateId)}/preview`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      },
    );
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json(
        { code: error.code, detail: error.message, context: error.context },
        { status: error.status },
      );
    }
    throw error;
  }

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as Record<string, unknown> | null;
    return NextResponse.json(body ?? { detail: "Aperçu indisponible." }, {
      status: response.status,
    });
  }

  return new NextResponse(response.body, {
    status: 200,
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "no-store",
    },
  });
}
