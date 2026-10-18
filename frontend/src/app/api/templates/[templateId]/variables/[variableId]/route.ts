import { NextResponse, type NextRequest } from "next/server";

import { ApiError, apiFetch } from "@/lib/api";
import type { TemplateVariable } from "@/lib/types";

export const dynamic = "force-dynamic";

type Context = { params: Promise<{ templateId: string; variableId: string }> };

export async function PUT(request: NextRequest, { params }: Context) {
  const { templateId, variableId } = await params;
  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return NextResponse.json({ detail: "Requête invalide." }, { status: 400 });
  }

  try {
    const variable = await apiFetch<TemplateVariable>(
      `/api/v1/templates/${encodeURIComponent(templateId)}/variables/${encodeURIComponent(variableId)}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      },
    );
    return NextResponse.json(variable);
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

export async function DELETE(_: NextRequest, { params }: Context) {
  const { templateId, variableId } = await params;
  try {
    await apiFetch<void>(
      `/api/v1/templates/${encodeURIComponent(templateId)}/variables/${encodeURIComponent(variableId)}`,
      { method: "DELETE" },
    );
    return new NextResponse(null, { status: 204 });
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
