import { NextResponse, type NextRequest } from "next/server";

import { ApiError, apiFetch, apiFetchRaw } from "@/lib/api";
import type { TemplateVariableImage } from "@/lib/types";

export const dynamic = "force-dynamic";

type Context = { params: Promise<{ templateId: string; variableId: string }> };

function backendPath(templateId: string, variableId: string): string {
  return `/api/v1/templates/${encodeURIComponent(templateId)}/variables/${encodeURIComponent(
    variableId,
  )}/image`;
}

export async function GET(request: NextRequest, { params }: Context) {
  const { templateId, variableId } = await params;
  let response: Response;
  try {
    response = await apiFetchRaw(backendPath(templateId, variableId));
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      return NextResponse.redirect(new URL("/login", request.url));
    }
    throw error;
  }

  if (response.status === 401) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
  if (!response.ok) {
    return NextResponse.json({ detail: "Image indisponible." }, { status: response.status });
  }

  return new NextResponse(response.body, {
    status: 200,
    headers: {
      "Content-Type": response.headers.get("content-type") ?? "application/octet-stream",
      "Content-Disposition":
        response.headers.get("content-disposition") ?? 'inline; filename="image"',
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
    },
  });
}

export async function PUT(request: NextRequest, { params }: Context) {
  const { templateId, variableId } = await params;
  let formData: FormData;
  try {
    formData = await request.formData();
  } catch {
    return NextResponse.json({ detail: "Formulaire invalide." }, { status: 400 });
  }

  try {
    const image = await apiFetch<TemplateVariableImage>(
      backendPath(templateId, variableId),
      { method: "PUT", body: formData },
    );
    return NextResponse.json(image);
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
    await apiFetch<void>(backendPath(templateId, variableId), { method: "DELETE" });
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
