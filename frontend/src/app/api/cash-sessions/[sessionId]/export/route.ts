import { NextResponse, type NextRequest } from "next/server";

import { ApiError, apiFetchRaw } from "@/lib/api";

export const dynamic = "force-dynamic";

/**
 * One session's extract. Like the dataset exports, the download goes through
 * Next so the browser never holds an API token.
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> },
) {
  const { sessionId } = await params;

  let response: Response;
  try {
    response = await apiFetchRaw(
      `/api/v1/cash-sessions/${encodeURIComponent(sessionId)}/export`,
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
    return NextResponse.json({ detail: "Export indisponible" }, { status: response.status });
  }

  return new NextResponse(response.body, {
    status: 200,
    headers: {
      "Content-Type": response.headers.get("content-type") ?? "text/csv; charset=utf-8",
      "Content-Disposition":
        response.headers.get("content-disposition") ?? 'attachment; filename="caisse.csv"',
      "Cache-Control": "no-store",
    },
  });
}
