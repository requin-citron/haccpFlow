import { NextResponse, type NextRequest } from "next/server";

import {
  ACCESS_COOKIE,
  REFRESH_COOKIE,
  accessTokenNeedsRefresh,
  baseCookieOptions,
  sessionFromTokenPair,
  type Session,
  type TokenPairPayload,
} from "@/lib/auth-cookies";

const API_BASE_URL = (process.env.API_INTERNAL_URL ?? "http://localhost:8000").replace(
  /\/+$/,
  "",
);
const REFRESH_TIMEOUT_MS = 5_000;

type RefreshOutcome =
  | { status: "ok"; session: Session }
  | { status: "invalid" }
  | { status: "unavailable" };

let refreshInFlight: {
  token: string;
  promise: Promise<RefreshOutcome>;
} | null = null;

async function requestRefresh(refreshToken: string): Promise<RefreshOutcome> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
      cache: "no-store",
      signal: AbortSignal.timeout(REFRESH_TIMEOUT_MS),
    });
    if (response.status === 401) {
      return { status: "invalid" };
    }
    if (!response.ok) {
      return { status: "unavailable" };
    }
    return {
      status: "ok",
      session: sessionFromTokenPair((await response.json()) as TokenPairPayload),
    };
  } catch {
    return { status: "unavailable" };
  }
}

function refreshOnce(refreshToken: string): Promise<RefreshOutcome> {
  if (refreshInFlight?.token === refreshToken) {
    return refreshInFlight.promise;
  }
  let promise: Promise<RefreshOutcome>;
  promise = requestRefresh(refreshToken).finally(() => {
    if (refreshInFlight?.promise === promise) {
      refreshInFlight = null;
    }
  });
  refreshInFlight = { token: refreshToken, promise };
  return promise;
}

function requestHeadersWithSession(request: NextRequest, session: Session): Headers {
  const headers = new Headers(request.headers);
  const cookies = request.cookies
    .getAll()
    .filter((cookie) => cookie.name !== ACCESS_COOKIE && cookie.name !== REFRESH_COOKIE);
  cookies.push(
    { name: ACCESS_COOKIE, value: session.accessToken },
    { name: REFRESH_COOKIE, value: session.refreshToken },
  );
  headers.set("cookie", cookies.map((cookie) => `${cookie.name}=${cookie.value}`).join("; "));
  return headers;
}

function applySessionCookies(response: NextResponse, session: Session): void {
  response.cookies.set(ACCESS_COOKIE, session.accessToken, {
    ...baseCookieOptions(),
    maxAge: Math.max(60, session.accessMaxAge),
  });
  response.cookies.set(REFRESH_COOKIE, session.refreshToken, {
    ...baseCookieOptions(),
    maxAge: Math.max(60, session.refreshMaxAge),
  });
}

function clearSessionCookies(response: NextResponse): void {
  response.cookies.set(ACCESS_COOKIE, "", { ...baseCookieOptions(), maxAge: 0 });
  response.cookies.set(REFRESH_COOKIE, "", { ...baseCookieOptions(), maxAge: 0 });
}

function unauthenticatedResponse(request: NextRequest): NextResponse {
  const isApi = request.nextUrl.pathname.startsWith("/api/");
  const response = isApi
    ? NextResponse.json({ detail: "Session expirée." }, { status: 401 })
    : NextResponse.redirect(new URL("/login", request.url));
  clearSessionCookies(response);
  return response;
}

export async function proxy(request: NextRequest): Promise<NextResponse> {
  const pathname = request.nextUrl.pathname;
  if (pathname === "/login" || pathname.startsWith("/api/auth/")) {
    return NextResponse.next();
  }

  const refreshToken = request.cookies.get(REFRESH_COOKIE)?.value;
  if (!refreshToken) {
    return NextResponse.next();
  }

  const accessToken = request.cookies.get(ACCESS_COOKIE)?.value;
  if (!accessTokenNeedsRefresh(accessToken)) {
    return NextResponse.next();
  }

  const outcome = await refreshOnce(refreshToken);
  if (outcome.status === "invalid") {
    return unauthenticatedResponse(request);
  }
  if (outcome.status === "unavailable") {
    // Do not destroy a valid-looking session because the API is temporarily
    // unreachable; the layout will still turn a real 401 into a login redirect.
    return NextResponse.next();
  }

  const response = NextResponse.next({
    request: { headers: requestHeadersWithSession(request, outcome.session) },
  });
  applySessionCookies(response, outcome.session);
  return response;
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)",
  ],
};
