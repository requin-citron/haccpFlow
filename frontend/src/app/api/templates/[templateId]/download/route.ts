import { NextResponse, type NextRequest } from "next/server";

import { ApiError, apiFetchRaw } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ templateId: string }> },
) {
  const { templateId } = await params;

  let response: Response;
  try {
    response = await apiFetchRaw(
      `/api/v1/templates/${encodeURIComponent(templateId)}/download`,
    );
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
    return NextResponse.json({ detail: "Modèle indisponible." }, { status: response.status });
  }

  return new NextResponse(response.body, {
    status: 200,
    headers: {
      "Content-Type": response.headers.get("content-type") ?? "text/plain; charset=utf-8",
      "Content-Disposition":
        response.headers.get("content-disposition") ?? 'attachment; filename="template.tex"',
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
    },
  });
}
