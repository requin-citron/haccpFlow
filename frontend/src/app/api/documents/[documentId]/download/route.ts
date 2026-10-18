import { NextResponse, type NextRequest } from "next/server";

import { ApiError, apiFetchRaw } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ documentId: string }> },
) {
  const { documentId } = await params;

  let response: Response;
  try {
    response = await apiFetchRaw(
      `/api/v1/documents/${encodeURIComponent(documentId)}/download`,
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
    return NextResponse.json({ detail: "Document indisponible." }, { status: response.status });
  }

  return new NextResponse(response.body, {
    status: 200,
    headers: {
      "Content-Type": response.headers.get("content-type") ?? "application/pdf",
      "Content-Disposition":
        response.headers.get("content-disposition") ?? 'attachment; filename="document.pdf"',
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
    },
  });
}
