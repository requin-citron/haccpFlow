import { NextResponse, type NextRequest } from "next/server";

import { ApiError, apiFetchRaw } from "@/lib/api";

export const dynamic = "force-dynamic";

const DATASETS = new Set(["readings", "cleanings", "pasteurisations", "transports"]);
const ALLOWED_PARAMS = ["from", "to"];

/**
 * Downloads go through Next: the browser only knows the session cookies, and
 * the API stays server-side.
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ dataset: string }> },
) {
  const { dataset } = await params;
  if (!DATASETS.has(dataset)) {
    return NextResponse.json({ detail: "Unknown dataset" }, { status: 404 });
  }

  const query = new URLSearchParams();
  for (const name of ALLOWED_PARAMS) {
    const value = request.nextUrl.searchParams.get(name);
    if (value) {
      query.set(name, value);
    }
  }
  const suffix = query.size > 0 ? `?${query.toString()}` : "";

  let response: Response;
  try {
    response = await apiFetchRaw(`/api/v1/exports/${dataset}${suffix}`);
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
        response.headers.get("content-disposition") ?? `attachment; filename="${dataset}.csv"`,
      "Cache-Control": "no-store",
    },
  });
}
